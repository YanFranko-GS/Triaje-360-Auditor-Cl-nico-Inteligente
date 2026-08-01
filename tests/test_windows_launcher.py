from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import windows_launcher as launcher


class Sink:
    def __init__(self):
        self.lines: list[str] = []

    def __call__(self, message: str = "") -> None:
        self.lines.append(message)


def test_all_bats_resolve_project_with_percent_tilde_dp0():
    names = [
        "00_INSTALAR_O_REPARAR.bat", "01_PROBAR_TODO.bat", "02_INICIAR_TRIAJE360.bat",
        "03_DETENER_TRIAJE360.bat", "INICIAR_TRIAJE360.bat",
    ]
    for name in names:
        source = (launcher.ROOT / name).read_text(encoding="utf-8")
        assert 'pushd "%~dp0"' in source
        assert "Set-ExecutionPolicy" not in source


def test_menu_calls_each_launcher_and_creates_logs():
    source = (launcher.ROOT / "INICIAR_TRIAJE360.bat").read_text(encoding="utf-8")
    for name in ("00_INSTALAR_O_REPARAR.bat", "01_PROBAR_TODO.bat", "02_INICIAR_TRIAJE360.bat", "03_DETENER_TRIAJE360.bat"):
        assert f'call "{name}"' in source
    assert 'if not exist "logs" mkdir "logs"' in source


def test_reporter_creates_logs_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "LOGS", tmp_path / "logs")
    report = launcher.Reporter(tmp_path / "logs" / "test.log")
    report("OK")
    assert (tmp_path / "logs" / "test.log").read_text(encoding="utf-8") == "OK\n"


def test_venv_is_detected():
    launcher.verify_venv()


def test_ollama_model_detection(monkeypatch):
    monkeypatch.setattr(launcher, "request_json", lambda *args, **kwargs: {"models": [{"name": "gemma4:e2b"}]})
    assert launcher.ollama_models() == ("gemma4:e2b",)
    report = Sink()
    launcher.ensure_model(report, offer_pull=False)
    assert any("detectado" in line for line in report.lines)


def test_direct_inference_requires_real_nonempty_response_and_cpu(monkeypatch):
    captured = {}

    def fake_request(url, payload, timeout):
        captured.update(payload)
        return {"model": "gemma4:e2b", "response": "GEMMA 4 OPERATIVO"}

    monkeypatch.setattr(launcher, "request_json", fake_request)
    assert launcher.direct_inference(Sink()) == "GEMMA 4 OPERATIVO"
    assert captured["options"]["num_gpu"] == 0
    assert captured["options"]["num_ctx"] == 4096


def test_direct_inference_rejects_empty_response(monkeypatch):
    monkeypatch.setattr(launcher, "request_json", lambda *args, **kwargs: {"model": "gemma4:e2b", "response": ""})
    with pytest.raises(launcher.LauncherError, match="vacía"):
        launcher.direct_inference(Sink())


def test_start_reuses_valid_existing_application(monkeypatch):
    monkeypatch.setattr(launcher, "read_pid", lambda: 123)
    monkeypatch.setattr(launcher, "is_project_streamlit", lambda pid: pid == 123)
    monkeypatch.setattr(launcher, "health_ok", lambda: True)
    monkeypatch.setattr(launcher.webbrowser, "open", lambda url: True)
    pid, started = launcher.start_streamlit(Sink(), open_browser=True)
    assert (pid, started) == (123, False)


def test_start_refuses_port_owned_by_other_process(monkeypatch):
    monkeypatch.setattr(launcher, "read_pid", lambda: None)
    monkeypatch.setattr(launcher, "port_owner", lambda: 456)
    monkeypatch.setattr(launcher, "find_project_root_for_pid", lambda pid: None)
    monkeypatch.setattr(launcher, "process_info", lambda pid: {"ExecutablePath": "C:\\otro\\python.exe"})
    with pytest.raises(launcher.LauncherError, match="PID 456"):
        launcher.start_streamlit(Sink(), open_browser=False)


def test_pid_file_roundtrip(tmp_path, monkeypatch):
    pid_file = tmp_path / "streamlit.pid"
    monkeypatch.setattr(launcher, "PID_FILE", pid_file)
    pid_file.write_text("987", encoding="ascii")
    assert launcher.read_pid() == 987


def test_project_process_requires_absolute_app_path(monkeypatch):
    command = f'python -m streamlit run "{launcher.APP_SCRIPT}" --server.port 8501'
    monkeypatch.setattr(launcher, "process_info", lambda pid: {"CommandLine": command})
    assert launcher.is_project_streamlit(123)

    monkeypatch.setattr(
        launcher,
        "process_info",
        lambda pid: {"CommandLine": "python -m streamlit run app.py --server.port 8501"},
    )
    assert not launcher.is_project_streamlit(123)


def test_safe_stop_rejects_unrelated_pid(monkeypatch):
    monkeypatch.setattr(launcher, "read_pid", lambda: 222)
    monkeypatch.setattr(launcher, "process_info", lambda pid: {"ProcessId": pid})
    monkeypatch.setattr(launcher, "is_project_streamlit", lambda pid: False)
    with pytest.raises(launcher.LauncherError, match="no corresponde"):
        launcher.stop_streamlit(Sink())


def test_safe_stop_targets_only_registered_process_tree(tmp_path, monkeypatch):
    pid_file = tmp_path / "streamlit.pid"
    pid_file.write_text("333", encoding="ascii")
    monkeypatch.setattr(launcher, "PID_FILE", pid_file)
    states = iter(({"ProcessId": 333}, None))
    monkeypatch.setattr(launcher, "process_info", lambda pid: next(states, None))
    monkeypatch.setattr(launcher, "is_project_streamlit", lambda pid: True)
    calls = []

    class Result:
        returncode = 0
        stderr = ""
        stdout = ""

    monkeypatch.setattr(launcher.subprocess, "run", lambda command, **kwargs: calls.append(command) or Result())
    monkeypatch.setattr(launcher, "wait_for", lambda predicate, seconds: True)
    launcher.stop_streamlit(Sink())
    assert calls == [["taskkill", "/PID", "333", "/T", "/F"]]
    assert not pid_file.exists()


def test_expected_env_configuration_is_exact(tmp_path):
    content = (launcher.ROOT / ".env.example").read_text(encoding="utf-8")
    parsed = {line.split("=", 1)[0]: line.split("=", 1)[1] for line in content.splitlines() if "=" in line}
    for key, value in launcher.EXPECTED_ENV.items():
        assert parsed[key] == value
