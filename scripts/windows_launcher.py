from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
APP_SCRIPT = (ROOT / "app.py").resolve()
LOGS = ROOT / "logs"
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
PID_FILE = LOGS / "streamlit.pid"
STDOUT_LOG = LOGS / "streamlit_stdout.log"
STDERR_LOG = LOGS / "streamlit_stderr.log"
OLLAMA_URL = "http://127.0.0.1:11434"
HEALTH_URL = "http://127.0.0.1:8501/_stcore/health"
APP_URL = "http://127.0.0.1:8501"
MODEL = "gemma4:e2b"

EXPECTED_ENV = {
    "AI_PROVIDER": "ollama",
    "ALLOW_LAN_ACCESS": "false",
    "OLLAMA_BASE_URL": "http://localhost:11434",
    "OLLAMA_MODEL": MODEL,
    "OLLAMA_TIMEOUT_SECONDS": "120",
    "OLLAMA_NUM_CTX": "4096",
    "OLLAMA_NUM_PREDICT": "320",
    "OLLAMA_NUM_GPU": "0",
    "OLLAMA_KEEP_ALIVE": "2m",
}


class LauncherError(RuntimeError):
    pass


class Reporter:
    def __init__(self, path: Path) -> None:
        LOGS.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("", encoding="utf-8")

    def __call__(self, message: str = "") -> None:
        print(message, flush=True)
        with self.path.open("a", encoding="utf-8") as target:
            target.write(message + "\n")


def request_json(url: str, payload: dict[str, Any] | None = None, timeout: float = 5) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise LauncherError(f"{url} respondió HTTP {response.status}.")
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise LauncherError(f"No se pudo consultar {url}: {exc}") from exc


def health_ok(url: str = HEALTH_URL, timeout: float = 2) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status == 200 and response.read().decode("utf-8").strip().casefold() == "ok"
    except (urllib.error.URLError, TimeoutError):
        return False


def wait_for(predicate: Any, seconds: float, interval: float = 0.5) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return bool(predicate())


def run_streamed(command: Iterable[str], report: Reporter, *, timeout: int | None = None) -> None:
    report(f"> {' '.join(map(str, command))}")
    try:
        process = subprocess.Popen(
            list(command), cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
        assert process.stdout is not None
        for line in process.stdout:
            report(line.rstrip())
        code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        raise LauncherError(f"El comando excedió {timeout} segundos.") from exc
    if code != 0:
        raise LauncherError(f"El comando terminó con código {code}.")


def verify_venv() -> None:
    if not VENV_PYTHON.is_file():
        raise LauncherError("Falta .venv\\Scripts\\python.exe. Ejecute 00_INSTALAR_O_REPARAR.bat.")
    result = subprocess.run([VENV_PYTHON, "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        raise LauncherError(f"El Python del entorno virtual no funciona: {result.stderr.strip()}")


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def verify_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        raise LauncherError("Falta .env. Ejecute 00_INSTALAR_O_REPARAR.bat.")
    values = parse_env(env_path)
    differences = [f"{key}={value}" for key, value in EXPECTED_ENV.items() if values.get(key) != value]
    if differences:
        raise LauncherError(".env no contiene la configuración segura requerida: " + ", ".join(differences))


def ollama_executable() -> str:
    executable = shutil.which("ollama")
    if not executable:
        raise LauncherError("Ollama no está instalado o no está disponible en PATH.")
    return executable


def ollama_models() -> tuple[str, ...]:
    body = request_json(f"{OLLAMA_URL}/api/tags", timeout=5)
    return tuple(item.get("name", "") for item in body.get("models", []))


def ensure_ollama(report: Reporter, *, start_if_needed: bool = True) -> tuple[str, ...]:
    executable = ollama_executable()
    version = subprocess.run([executable, "--version"], capture_output=True, text=True, errors="replace")
    if version.returncode != 0:
        raise LauncherError(f"ollama --version falló: {version.stderr.strip()}")
    report(f"OLLAMA: {version.stdout.strip() or version.stderr.strip()}")
    try:
        models = ollama_models()
    except LauncherError:
        if not start_if_needed:
            raise
        report("La API de Ollama no responde; iniciando 'ollama serve' de forma local...")
        ollama_out = (LOGS / "ollama_stdout.log").open("a", encoding="utf-8")
        ollama_err = (LOGS / "ollama_stderr.log").open("a", encoding="utf-8")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        subprocess.Popen([executable, "serve"], cwd=ROOT, stdout=ollama_out, stderr=ollama_err, creationflags=flags)
        if not wait_for(lambda: _ollama_reachable(), 30):
            raise LauncherError("Ollama no respondió en 30 segundos. Revise logs\\ollama_stderr.log.")
        models = ollama_models()
    report("API OLLAMA: OK (HTTP 200)")
    report("MODELOS OLLAMA: " + (", ".join(models) if models else "ninguno"))
    return models


def _ollama_reachable() -> bool:
    try:
        ollama_models()
        return True
    except LauncherError:
        return False


def ensure_model(report: Reporter, *, offer_pull: bool) -> None:
    models = ollama_models()
    if MODEL in models:
        report(f"MODELO: {MODEL} detectado.")
        return
    if not offer_pull:
        raise LauncherError(f"Falta {MODEL}. Ejecute: ollama pull {MODEL}")
    answer = input(f"Falta {MODEL} (aprox. 7.2 GB). ¿Desea descargar exclusivamente este modelo? [S/N]: ").strip().casefold()
    if answer not in {"s", "si", "sí", "y", "yes"}:
        raise LauncherError(f"No se descargó {MODEL}; no es posible continuar con Gemma real.")
    run_streamed([ollama_executable(), "pull", MODEL], report)
    if MODEL not in ollama_models():
        raise LauncherError(f"La descarga terminó, pero {MODEL} no aparece en Ollama.")


def direct_inference(report: Reporter, *, label: str = "GEMMA REAL") -> str:
    payload = {
        "model": MODEL,
        "prompt": "Responde únicamente con el texto: GEMMA 4 OPERATIVO",
        "stream": False,
        "think": False,
        "keep_alive": "2m",
        "options": {"temperature": 0, "num_predict": 32, "num_ctx": 4096, "num_gpu": 0},
    }
    started = time.monotonic()
    body = request_json(f"{OLLAMA_URL}/api/generate", payload, timeout=180)
    response = str(body.get("response", "")).strip()
    if body.get("model") != MODEL:
        raise LauncherError(f"Ollama informó un modelo diferente: {body.get('model')!r}.")
    if not response:
        raise LauncherError("Gemma devolvió una respuesta vacía.")
    if "GEMMA 4 OPERATIVO" not in response.upper():
        raise LauncherError(f"Gemma respondió, pero no confirmó el texto esperado: {response!r}")
    report(f"{label}: OK (model={MODEL}, response={response}, num_gpu=0, {time.monotonic() - started:.2f}s)")
    return response


def process_info(pid: int) -> dict[str, Any] | None:
    script = (
        f'$p=Get-CimInstance Win32_Process -Filter "ProcessId = {pid}" -ErrorAction SilentlyContinue; '
        "if($p){[pscustomobject]@{ProcessId=$p.ProcessId;ParentProcessId=$p.ParentProcessId;"
        "ExecutablePath=$p.ExecutablePath;CommandLine=$p.CommandLine}|ConvertTo-Json -Compress}"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script], capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def is_project_streamlit(pid: int) -> bool:
    info = process_info(pid)
    if not info:
        return False
    command = str(info.get("CommandLine") or "").casefold()
    app_path = str(APP_SCRIPT).casefold()
    return "streamlit" in command and app_path in command and "8501" in command


def read_pid() -> int | None:
    if not PID_FILE.is_file():
        return None
    try:
        return int(PID_FILE.read_text(encoding="ascii").strip())
    except (ValueError, OSError):
        return None


def port_owner(port: int = 8501) -> int | None:
    result = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, errors="replace")
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 5 and fields[1].endswith(f":{port}") and fields[3].upper() == "LISTENING":
            try:
                return int(fields[4])
            except ValueError:
                pass
    return None


def find_project_root_for_pid(pid: int) -> int | None:
    current = pid
    for _ in range(4):
        if is_project_streamlit(current):
            return current
        info = process_info(current)
        if not info:
            return None
        parent = int(info.get("ParentProcessId") or 0)
        if parent <= 0 or parent == current:
            return None
        current = parent
    return None


def start_streamlit(report: Reporter, *, open_browser: bool, temporary: bool = False) -> tuple[int, bool]:
    LOGS.mkdir(parents=True, exist_ok=True)
    saved_pid = read_pid()
    if saved_pid and is_project_streamlit(saved_pid) and health_ok():
        report(f"TRIaje 360 ya está operativo; se reutiliza PID {saved_pid}.")
        if open_browser:
            webbrowser.open(APP_URL)
        return saved_pid, False

    owner = port_owner()
    if owner is not None:
        root_pid = find_project_root_for_pid(owner)
        if root_pid and health_ok():
            PID_FILE.write_text(str(root_pid), encoding="ascii")
            report(f"El puerto 8501 pertenece a TRIaje 360; se reutiliza PID {root_pid}.")
            if open_browser:
                webbrowser.open(APP_URL)
            return root_pid, False
        info = process_info(owner) or {}
        name = info.get("ExecutablePath") or "proceso no identificado"
        raise LauncherError(f"El puerto 8501 está ocupado por PID {owner} ({name}). No se terminó ese proceso.")

    STDOUT_LOG.write_text("", encoding="utf-8")
    STDERR_LOG.write_text("", encoding="utf-8")
    stdout = STDOUT_LOG.open("a", encoding="utf-8")
    stderr = STDERR_LOG.open("a", encoding="utf-8")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    process = subprocess.Popen(
        [str(VENV_PYTHON), "-m", "streamlit", "run", str(APP_SCRIPT), "--server.address", "127.0.0.1",
         "--server.port", "8501", "--server.headless", "true"],
        cwd=ROOT, stdout=stdout, stderr=stderr, creationflags=flags,
    )
    if not wait_for(health_ok, 30):
        detail = STDERR_LOG.read_text(encoding="utf-8", errors="replace")[-2000:]
        if is_project_streamlit(process.pid):
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
        PID_FILE.unlink(missing_ok=True)
        raise LauncherError("Streamlit no respondió HTTP 200 en 30 segundos. " + (detail or "Revise el log de stderr."))
    owner = port_owner()
    server_pid = find_project_root_for_pid(owner) if owner is not None else None
    if server_pid is None:
        if process_info(process.pid) is not None:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
        raise LauncherError("Streamlit respondió, pero no se pudo validar el PID del servidor para una detención segura.")
    PID_FILE.write_text(str(server_pid), encoding="ascii")
    report(f"STREAMLIT HTTP: OK (200) - {HEALTH_URL}")
    report(f"PID REGISTRADO: {server_pid}")
    if open_browser and not temporary:
        if not webbrowser.open(APP_URL):
            report(f"AVISO: no se pudo abrir el navegador automáticamente. Abra {APP_URL}")
        else:
            report("NAVEGADOR: apertura solicitada correctamente.")
    return server_pid, True


def stop_streamlit(report: Reporter, *, expected_pid: int | None = None) -> None:
    pid = expected_pid if expected_pid is not None else read_pid()
    if pid is None:
        PID_FILE.unlink(missing_ok=True)
        report("No hay una instancia de TRIaje 360 registrada.")
        return
    if process_info(pid) is None:
        PID_FILE.unlink(missing_ok=True)
        report(f"El PID registrado {pid} ya terminó; se limpió logs\\streamlit.pid.")
        return
    if not is_project_streamlit(pid):
        raise LauncherError(f"El PID {pid} no corresponde al Streamlit de este proyecto; no se terminó ningún proceso.")
    result = subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True, errors="replace")
    if result.returncode != 0 and process_info(pid) is not None:
        raise LauncherError(f"No se pudo detener el árbol del PID {pid}: {result.stderr.strip() or result.stdout.strip()}")
    wait_for(lambda: process_info(pid) is None, 10)
    PID_FILE.unlink(missing_ok=True)
    report(f"TRIaje 360 detenido correctamente. PID raíz: {pid}. Ollama no fue detenido.")


def install(report: Reporter) -> None:
    verify_venv()
    report(f"PROYECTO: {ROOT}")
    report(f"PYTHON VENV: {subprocess.check_output([VENV_PYTHON, '--version'], text=True).strip()}")
    run_streamed([str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip"], report)
    run_streamed([str(VENV_PYTHON), "-m", "pip", "install", "-r", "requirements.txt"], report)
    env_path = ROOT / ".env"
    if not env_path.exists():
        shutil.copy2(ROOT / ".env.example", env_path)
        report(".env creado desde .env.example.")
    else:
        report(".env existente conservado sin sobrescribir.")
    verify_env()
    ensure_ollama(report)
    ensure_model(report, offer_pull=True)
    run_streamed([str(VENV_PYTHON), "-c", "from database import initialize; initialize(); print('SQLITE: OK')"], report)
    run_streamed([str(VENV_PYTHON), "-m", "pytest", "-q"], report)
    report("INSTALACIÓN COMPLETADA")


def smoke(report: Reporter) -> None:
    report(f"UBICACIÓN DEL PROYECTO: OK ({ROOT})")
    verify_venv()
    report(f"PYTHON DEL ENTORNO: OK ({VENV_PYTHON})")
    verify_env()
    report("ARCHIVO .env Y CONFIGURACIÓN CPU: OK (num_gpu=0, num_ctx=4096)")
    run_streamed([str(VENV_PYTHON), "-c", "import streamlit,requests,pydantic,dotenv; from database import initialize; initialize(); print('DEPENDENCIAS Y SQLITE: OK')"], report)
    ensure_ollama(report)
    ensure_model(report, offer_pull=False)
    direct_inference(report)
    run_streamed([str(VENV_PYTHON), "-m", "pytest", "-q", "tests/test_gemma_integration.py"], report)
    run_streamed([str(VENV_PYTHON), "-c", "from services.ollama_client import fallback_analysis; assert fallback_analysis('me falta el aire').protocol_id == 'respiratory_alert'; print('RESPALDO DETERMINISTA: OK')"], report)
    run_streamed([str(VENV_PYTHON), "-m", "pytest", "-q"], report)
    report("PRUEBAS PYTEST: OK")
    pid: int | None = None
    started = False
    try:
        pid, started = start_streamlit(report, open_browser=False, temporary=True)
    finally:
        if started and pid is not None:
            stop_streamlit(report, expected_pid=pid)
            report("STREAMLIT TEMPORAL: detenido correctamente.")
    report("SMOKE TEST COMPLETADO")


def start(report: Reporter) -> None:
    verify_venv()
    verify_env()
    report(f"PYTHON DEL ENTORNO: OK ({VENV_PYTHON})")
    ensure_ollama(report)
    ensure_model(report, offer_pull=True)
    saved_pid = read_pid()
    if saved_pid and is_project_streamlit(saved_pid) and health_ok():
        pid, _ = start_streamlit(report, open_browser=True)
        report(f"TRIaje 360 ya estaba operativo con {MODEL}. PID: {pid}")
        return
    owner = port_owner()
    if owner is not None:
        root_pid = find_project_root_for_pid(owner)
        if root_pid and health_ok():
            PID_FILE.write_text(str(root_pid), encoding="ascii")
            pid, _ = start_streamlit(report, open_browser=True)
            report(f"TRIaje 360 ya estaba operativo con {MODEL}. PID: {pid}")
            return
        info = process_info(owner) or {}
        name = info.get("ExecutablePath") or "proceso no identificado"
        raise LauncherError(f"El puerto 8501 está ocupado por PID {owner} ({name}). No se terminó ese proceso.")
    direct_inference(report, label="PRECALENTAMIENTO GEMMA")
    pid, _ = start_streamlit(report, open_browser=True)
    report("")
    report("TRIaje 360 está operativo.")
    report(f"Modelo: {MODEL}")
    report(f"URL: {APP_URL}")
    report(f"PID: {pid}")
    report("Para detener solo la demo, use 03_DETENER_TRIAJE360.bat.")


def status(report: Reporter) -> None:
    pid = read_pid()
    report(f"PID registrado: {pid if pid is not None else 'ninguno'}")
    report(f"Proceso válido del proyecto: {'sí' if pid and is_project_streamlit(pid) else 'no'}")
    report(f"HTTP Streamlit: {'200 OK' if health_ok() else 'no disponible'}")
    report(f"API Ollama: {'operativa' if _ollama_reachable() else 'no disponible'}")


def stop(report: Reporter) -> None:
    stop_streamlit(report)


def main() -> int:
    parser = argparse.ArgumentParser(description="Lanzador seguro de KutanLab TRIaje 360 para Windows")
    parser.add_argument("command", choices=("install", "smoke", "start", "stop", "status"))
    parser.add_argument("--log", type=Path)
    args = parser.parse_args()
    default_logs = {
        "install": "install.log", "smoke": "smoke_test.log", "start": "start.log",
        "stop": "stop.log", "status": "status.log",
    }
    report = Reporter(args.log or LOGS / default_logs[args.command])
    try:
        commands = {"install": install, "smoke": smoke, "start": start, "stop": stop, "status": status}
        commands[args.command](report)
        return 0
    except (LauncherError, OSError, subprocess.SubprocessError) as exc:
        report(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
