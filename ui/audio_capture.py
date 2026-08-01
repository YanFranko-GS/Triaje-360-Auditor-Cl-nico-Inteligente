from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from audio_pipeline import NoiseProfile, process_wav, sanitize_transcription
from config import Settings
from services.local_asr import transcribe_wav
from workflow_store import add_audio_segment, create_audio_session, save_transcription


@dataclass(frozen=True)
class IntakeText:
    text: str
    provider: str
    confirmed: bool


def render_audio_capture(settings: Settings, user_id: str) -> IntakeText:
    st.markdown("### Describa sus síntomas")
    st.caption("Puede grabar hasta 30 segundos por segmento o continuar únicamente con texto.")
    consent = st.checkbox(
        "Autorizo la captura temporal de audio para esta validación",
        key="voice_capture_consent",
    )
    profile = st.selectbox(
        "Entorno de grabación", tuple(NoiseProfile), index=1,
        format_func=lambda item: {NoiseProfile.QUIET: "Silencioso", NoiseProfile.CLINIC: "Clínica", NoiseProfile.HIGH_NOISE: "Ruido alto"}[item],
        key="voice_noise_profile",
    )
    st.caption("Reducción de ruido asistida; revise siempre la transcripción.")
    audio = st.audio_input("Grabar segmento", key="patient_audio_input", disabled=not consent)
    if audio is not None:
        st.audio(audio)
        if st.button("Procesar audio", key="process_patient_audio", type="primary"):
            try:
                processed = process_wav(audio.getvalue(), audio.type or "audio/wav", profile, settings.max_audio_seconds)
                audio_session = create_audio_session(user_id, profile.value, consent, store_audio=settings.store_demo_audio)
                segment = add_audio_segment(audio_session, processed, audio.type or "audio/wav")
                result = transcribe_wav(processed.wav_bytes, settings.asr_model_path)
                st.session_state.audio_metrics = processed
                if result.available and result.text:
                    st.session_state.voice_transcript = sanitize_transcription(result.text)
                    st.session_state.transcription_provider = result.provider
                    st.session_state.transcription_confidence = result.confidence
                    save_transcription(result.provider, result.text, segment_id=segment, confidence=result.confidence)
                else:
                    st.session_state.transcription_provider = "manual_text"
                    st.warning(result.detail)
            except ValueError as exc:
                st.error(str(exc))
    metrics = st.session_state.get("audio_metrics")
    if metrics:
        level = min(100, round(metrics.rms_level * 400))
        st.progress(level, text=f"Nivel aproximado de entrada: {level}/100 · duración {metrics.duration_seconds:.1f} s")
        st.caption(f"PCM mono {metrics.sample_rate} Hz · audio eliminado tras el procesamiento · hash de trazabilidad conservado")
    transcript = st.text_area(
        "Transcripción editable",
        value=st.session_state.get("voice_transcript", ""),
        height=130,
        placeholder="Escriba aquí si no desea o no puede usar el micrófono.",
        key="editable_transcription",
    )
    manual = st.text_area(
        "Información adicional escrita", key="manual_symptom_text", height=90,
        placeholder="Añada o corrija información antes de confirmar.",
    )
    combined = sanitize_transcription(" ".join(item for item in (transcript, manual) if item.strip())) if (transcript.strip() or manual.strip()) else ""
    provider = st.session_state.get("transcription_provider", "manual_text") if transcript.strip() else "manual_text"
    confirmed = st.checkbox("He revisado y confirmo el texto anterior", key="confirm_transcription", disabled=not combined)
    if st.session_state.get("transcription_confidence") is not None:
        st.caption(f"Confianza informada por ASR: {st.session_state.transcription_confidence:.2f}")
    return IntakeText(combined, provider, confirmed)
