from __future__ import annotations

import audioop
import hashlib
import io
import wave
from array import array
from dataclasses import dataclass
from enum import StrEnum


ALLOWED_AUDIO_MIME = {"audio/wav", "audio/x-wav", "audio/wave"}
MAX_AUDIO_BYTES = 8 * 1024 * 1024


class NoiseProfile(StrEnum):
    QUIET = "QUIET"
    CLINIC = "CLINIC"
    HIGH_NOISE = "HIGH_NOISE"


@dataclass(frozen=True)
class ProcessedAudio:
    wav_bytes: bytes
    duration_seconds: float
    sample_rate: int
    peak_level: float
    rms_level: float
    audio_sha256: str
    signal_status: str
    suggested_segment_seconds: int


def _high_pass(samples: bytes, sample_rate: int, cutoff_hz: float = 70.0) -> bytes:
    values = array("h")
    values.frombytes(samples)
    if not values:
        return samples
    rc = 1.0 / (6.283185307179586 * cutoff_hz)
    dt = 1.0 / sample_rate
    alpha = rc / (rc + dt)
    previous_input = float(values[0])
    previous_output = 0.0
    for index, sample in enumerate(values):
        output = alpha * (previous_output + sample - previous_input)
        values[index] = max(-32768, min(32767, int(output)))
        previous_input, previous_output = float(sample), output
    return values.tobytes()


def _trim_silence(samples: bytes, sample_width: int, sample_rate: int, threshold: int) -> bytes:
    frame_bytes = max(sample_width, int(sample_rate * 0.02) * sample_width)
    chunks = [samples[index:index + frame_bytes] for index in range(0, len(samples), frame_bytes)]
    active = [index for index, chunk in enumerate(chunks) if chunk and audioop.rms(chunk, sample_width) >= threshold]
    if not active:
        return b""
    start = max(0, active[0] - 2)
    end = min(len(chunks), active[-1] + 3)
    return b"".join(chunks[start:end])


def process_wav(
    content: bytes, mime_type: str, profile: NoiseProfile = NoiseProfile.CLINIC, max_seconds: int = 30
) -> ProcessedAudio:
    if mime_type.casefold() not in ALLOWED_AUDIO_MIME:
        raise ValueError("MIME de audio no permitido; use WAV.")
    if not content:
        raise ValueError("El archivo de audio está vacío.")
    if len(content) > MAX_AUDIO_BYTES:
        raise ValueError("El audio excede el tamaño permitido.")
    try:
        with wave.open(io.BytesIO(content), "rb") as source:
            channels, width, rate, frames = (
                source.getnchannels(), source.getsampwidth(), source.getframerate(), source.getnframes()
            )
            if channels not in {1, 2} or width not in {1, 2, 3, 4} or rate < 8000 or rate > 96000:
                raise ValueError("Formato WAV no compatible.")
            duration = frames / rate
            if duration <= 0.05:
                raise ValueError("El audio es demasiado corto.")
            if duration > max_seconds + 0.05:
                raise ValueError(f"El audio supera el máximo de {max_seconds} segundos.")
            samples = source.readframes(frames)
    except wave.Error as exc:
        raise ValueError("El contenido no es un WAV válido.") from exc

    if channels == 2:
        samples = audioop.tomono(samples, width, 0.5, 0.5)
    if width != 2:
        samples = audioop.lin2lin(samples, width, 2)
    if rate != 16000:
        samples, _state = audioop.ratecv(samples, 2, 1, rate, 16000, None)
    rate, width = 16000, 2
    samples = _high_pass(samples, rate)
    raw_peak = audioop.max(samples, width) / 32767 if samples else 0.0
    raw_rms = audioop.rms(samples, width) / 32767 if samples else 0.0
    if raw_peak >= 0.999 and raw_rms > 0.75:
        raise ValueError("El audio está saturado; reduzca la ganancia y repita.")
    threshold = {NoiseProfile.QUIET: 180, NoiseProfile.CLINIC: 300, NoiseProfile.HIGH_NOISE: 500}[profile]
    samples = _trim_silence(samples, width, rate, threshold)
    if not samples or audioop.rms(samples, width) / 32767 < 0.004:
        raise ValueError("No se detectó señal de voz suficiente.")
    peak = audioop.max(samples, width)
    if peak:
        target = 0.82 * 32767
        samples = audioop.mul(samples, width, min(2.5, target / peak))
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(rate)
        target.writeframes(samples)
    wav_bytes = output.getvalue()
    processed_duration = len(samples) / (rate * width)
    return ProcessedAudio(
        wav_bytes=wav_bytes,
        duration_seconds=round(processed_duration, 3),
        sample_rate=rate,
        peak_level=round(audioop.max(samples, width) / 32767, 4),
        rms_level=round(audioop.rms(samples, width) / 32767, 4),
        audio_sha256=hashlib.sha256(content).hexdigest(),
        signal_status="usable",
        suggested_segment_seconds=12 if profile == NoiseProfile.HIGH_NOISE else 30,
    )


def sanitize_transcription(text: str) -> str:
    lowered = text.casefold()
    if any(token in lowered for token in ("<script", "javascript:", "ignore previous instructions", "system prompt")):
        raise ValueError("La transcripción contiene contenido no permitido.")
    cleaned = " ".join(text.replace("<", " ").replace(">", " ").split())
    if not cleaned:
        raise ValueError("La transcripción está vacía.")
    return cleaned[:4000]
