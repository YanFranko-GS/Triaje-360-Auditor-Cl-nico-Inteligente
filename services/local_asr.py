from __future__ import annotations

import importlib.util
import io
import json
import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ASRResult:
    provider: str
    text: str
    confidence: float | None
    available: bool
    detail: str


def asr_status(model_path: Path | None) -> ASRResult:
    if importlib.util.find_spec("vosk") is None:
        return ASRResult("local_asr", "", None, False, "Vosk no está instalado; use texto manual o instale el extra de voz.")
    if model_path is None or not model_path.is_dir():
        return ASRResult("local_asr", "", None, False, "Falta ASR_MODEL_PATH con un modelo español local.")
    return ASRResult("local_asr", "", None, True, "Vosk español local disponible bajo demanda.")


def transcribe_wav(wav_bytes: bytes, model_path: Path | None) -> ASRResult:
    status = asr_status(model_path)
    if not status.available:
        return status
    from vosk import KaldiRecognizer, Model, SetLogLevel  # type: ignore[import-not-found]

    SetLogLevel(-1)
    with wave.open(io.BytesIO(wav_bytes), "rb") as source:
        if source.getnchannels() != 1 or source.getsampwidth() != 2 or source.getframerate() != 16000:
            return ASRResult("local_asr", "", None, False, "El audio preprocesado no cumple PCM mono 16 kHz.")
        model = Model(str(model_path))
        recognizer = KaldiRecognizer(model, 16000)
        recognizer.SetWords(True)
        while data := source.readframes(4000):
            recognizer.AcceptWaveform(data)
        payload = json.loads(recognizer.FinalResult())
    text = str(payload.get("text", "")).strip()
    words = payload.get("result", [])
    confidence = round(sum(float(item.get("conf", 0)) for item in words) / len(words), 4) if words else None
    if not text:
        return ASRResult("local_asr", "", confidence, False, "El ASR no obtuvo habla suficiente; repita o escriba.")
    return ASRResult("local_asr", text, confidence, True, "Transcripción local generada por Vosk.")
