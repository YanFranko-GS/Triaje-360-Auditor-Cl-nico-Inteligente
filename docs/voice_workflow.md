# Flujo de admisión por voz

```text
Micrófono del navegador / texto manual
        ↓ consentimiento y límites
validación WAV + mono/16 kHz + normalización moderada
        ↓ recorte de silencio / pasa-altos prudente / señal útil
Vosk español local bajo demanda
        ↓ transcripción editable y confirmada
Gemma 4: extracción estructurada y campos faltantes
        ↓ una pregunta breve por turno (máximo 5)
confirmación del paciente o profesional
        ↓
RAG + triaje supervisado + auditoría
```

## Captura y privacidad

`st.audio_input` ofrece grabación/reproducción en navegador. Esta versión de Streamlit no expone parámetros para forzar `echoCancellation`, `noiseSuppression` o `autoGainControl`; no se afirma que estén activos. El servidor valida MIME WAV, máximo 30 s/8 MB, duración, canales, sample rate, silencio y saturación. Por defecto guarda sólo hash, duración, sample rate y estado de señal; no persiste bytes ni rutas de audio.

## Perfiles de ruido

- `QUIET`: umbral de actividad más sensible.
- `CLINIC`: recorte moderado para ambiente asistencial común.
- `HIGH_NOISE`: umbral prudente y recomendación de segmentos de 12 s.

La reducción es asistida, no elimina perfectamente el ruido. Los filtros evitan transformaciones agresivas y toda transcripción debe revisarse. Si falta señal, se pide repetir o escribir. Las palabras inciertas sólo podrían destacarse cuando el ASR entregue esa información.

## Trazabilidad

`transcription_provider` diferencia `gemma4_audio`, `local_asr` y `manual_text`. En el runtime validado se usan `local_asr` o `manual_text`; `gemma4_audio` permanece deshabilitado mientras el soporte directo sea `UNCONFIRMED`.
