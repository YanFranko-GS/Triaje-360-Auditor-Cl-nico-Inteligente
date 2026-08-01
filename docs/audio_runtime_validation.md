# Validación del runtime de audio

Fecha: 2026-08-01. Equipo: Windows 11, Python 3.12, Ollama 0.32.4, `gemma4:e2b`, CPU (`num_gpu=0`).

## Resultado de audio directo

`DIRECT_GEMMA_AUDIO_UNCONFIRMED`

`scripts/check_gemma_audio_support.py` consultó `/api/version` y `/api/show`, generó un WAV mono con tono de 440 Hz y lo envió a `/api/chat`. El runtime respondió HTTP 200 y el modelo declaró las capacidades `completion`, `vision`, `audio`, `tools` y `thinking`; sin embargo, usando tanto `audio` como `audios`, la respuesta pidió adjuntar el audio. Por tanto, la prueba no demostró que Ollama entregara el contenido WAV al modelo y la aplicación **no** atribuye transcripción directa a Gemma.

La [API oficial de chat de Ollama](https://docs.ollama.com/api/chat) documenta texto e imágenes, pero no un contrato estable de audio. La ficha local del modelo y la página [Gemma 4 en Ollama](https://ollama.com/library/gemma4) describen capacidad del modelo, que no basta para afirmar soporte del runtime.

## ASR local validado

Proveedor: `local_asr` mediante Vosk 0.3.45 y `vosk-model-small-es-0.42` (39 MB, Apache 2.0). El modelo fue descargado explícitamente a `.demo/asr_models/`, ruta ignorada por Git; nunca se descarga durante el arranque. La página oficial de [modelos Vosk](https://alphacephei.com/vosk/models) lo recomienda como modelo liviano de escritorio.

Prueba empírica:

- entrada: voz sintética Windows en español, “Tengo dolor en el pecho desde ayer”;
- preprocesamiento: WAV PCM, mono, 16 kHz, 1.74 s;
- salida: `tengo dolor en el pecho desde ayer`;
- confianza reportada por Vosk: `1.0`.

La confianza sólo se presenta cuando Vosk la entrega. Este resultado limpio no garantiza precisión con voces reales, terminología clínica, varios hablantes o ruido.

## Reproducción

```powershell
.\.venv\Scripts\python.exe scripts\check_gemma_audio_support.py
.\.venv\Scripts\python.exe -m pip install -r requirements-voice.txt
```

Configure `ASR_MODEL_PATH` después de descargar manualmente el modelo. La entrada escrita permanece disponible siempre.
