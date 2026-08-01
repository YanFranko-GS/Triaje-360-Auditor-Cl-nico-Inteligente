from __future__ import annotations

import argparse
import base64
import io
import json
import math
import struct
import wave
from typing import Any

import requests


RESULT_SUPPORTED = "DIRECT_GEMMA_AUDIO_SUPPORTED"
RESULT_UNSUPPORTED = "DIRECT_GEMMA_AUDIO_UNSUPPORTED"
RESULT_UNCONFIRMED = "DIRECT_GEMMA_AUDIO_UNCONFIRMED"


def synthetic_wav(seconds: float = 0.8, sample_rate: int = 16000) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(sample_rate)
        frames = (
            struct.pack("<h", int(0.25 * 32767 * math.sin(2 * math.pi * 440 * index / sample_rate)))
            for index in range(int(seconds * sample_rate))
        )
        target.writeframes(b"".join(frames))
    return output.getvalue()


def check_audio_support(base_url: str, model: str, timeout: int = 120) -> dict[str, Any]:
    report: dict[str, Any] = {"model": model}
    try:
        version_response = requests.get(f"{base_url}/api/version", timeout=5)
        report["version_http"] = version_response.status_code
        report["ollama_version"] = version_response.json().get("version") if version_response.ok else None
        show_response = requests.post(f"{base_url}/api/show", json={"model": model}, timeout=10)
        report["show_http"] = show_response.status_code
        show_payload = show_response.json() if show_response.ok else {}
        capabilities = [str(item).casefold() for item in show_payload.get("capabilities", [])]
        report["declared_capabilities"] = capabilities
        audio = base64.b64encode(synthetic_wav()).decode("ascii")
        chat_response = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "stream": False,
                "think": False,
                "messages": [{"role": "user", "content": "Responde únicamente TONO o SILENCIO según el audio adjunto.", "audios": [audio]}],
                "options": {"num_predict": 24, "num_ctx": 1024, "num_gpu": 0, "temperature": 0},
            },
            timeout=timeout,
        )
        report["audio_probe_http"] = chat_response.status_code
        report["audio_probe_error"] = None if chat_response.ok else chat_response.text[:300]
        response_text = str(chat_response.json().get("message", {}).get("content", "")) if chat_response.ok else ""
        report["audio_probe_response"] = response_text[:160]
        tone_recognized = "tono" in response_text.casefold() and "silencio" not in response_text.casefold().strip(" .")
        if "audio" in capabilities and chat_response.ok and tone_recognized:
            report["result"] = RESULT_SUPPORTED
            report["reason"] = "El modelo declara audio, la API aceptó el WAV y la respuesta identificó el tono sintético."
        elif "audio" in capabilities and chat_response.ok:
            report["result"] = RESULT_UNCONFIRMED
            report["reason"] = "La API aceptó la solicitud, pero la respuesta no demostró que interpretó el tono."
        elif show_response.ok and "audio" not in capabilities:
            report["result"] = RESULT_UNSUPPORTED
            report["reason"] = "El modelo local no declara la capacidad audio; una respuesta textual no prueba consumo del campo desconocido."
        else:
            report["result"] = RESULT_UNCONFIRMED
            report["reason"] = "No fue posible confirmar la modalidad con la evidencia del runtime."
    except (requests.RequestException, ValueError) as exc:
        report.update(result=RESULT_UNCONFIRMED, reason=str(exc), audio_probe_http=None)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="gemma4:e2b")
    args = parser.parse_args()
    print(json.dumps(check_audio_support(args.base_url.rstrip("/"), args.model), indent=2, ensure_ascii=False))
