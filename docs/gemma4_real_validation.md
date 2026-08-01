# Validación real de Gemma 4 E2B

## Ejecución con doble clic

El flujo Windows recomendado es `INICIAR_TRIAJE360.bat`: descomprima el proyecto, elija **Instalar o reparar**, **Probar toda la instalación**, **Iniciar aplicación**, abra `http://localhost:8501` y use **Detener aplicación** al finalizar. Cada etapa genera logs y la detención valida el PID del entorno virtual antes de cerrar únicamente su árbol de procesos. Los BAT no requieren administrador ni modifican permanentemente `ExecutionPolicy`.

Ante «la ejecución de scripts está deshabilitada en este sistema», use los BAT. El comando alternativo `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\smoke_test.ps1"` aplica el bypass solo al proceso invocado.

## Entorno y fecha

- Fecha local: `2026-07-31 23:45:02 -05:00`.
- Sistema: Windows 11, 11.62 GB de RAM, NVIDIA MX330 de 2 GB.
- Ollama: `0.32.4`.
- URL local: `http://localhost:11434` (sin exposición de red).
- Modelo exacto: `gemma4:e2b`.
- Familia reportada por API: `gemma4`, 5.1B, Q4_K_M.
- Tamaño local: 7.2 GB.

No se usaron datos personales reales.

## Instalación e inventario

Comando ejecutado:

```powershell
ollama pull gemma4:e2b
```

Resultado final: capa de 7.2 GB al 100 %, SHA-256 verificado, manifiesto escrito y `success`.

`ollama list` después de instalar:

```text
NAME                ID              SIZE
gemma4:e2b          7fbdbf8f5e45    7.2 GB
qwen2.5:3b          357c53fb659c    1.9 GB
qwen2.5-coder:3b    f72c60cabf62    1.9 GB
llama3.2:3b         a80c4f17acd5    2.0 GB
```

No se borró ni reemplazó ningún modelo existente.

## Inferencia directa

Solicitud equivalente ejecutada contra `/api/generate`:

```json
{
  "model": "gemma4:e2b",
  "prompt": "Responde unicamente con el texto: GEMMA 4 OPERATIVO",
  "stream": false,
  "think": false,
  "keep_alive": "2m",
  "options": {
    "temperature": 0,
    "num_predict": 32,
    "num_ctx": 4096,
    "num_gpu": 0
  }
}
```

Resultado:

```json
{
  "model": "gemma4:e2b",
  "response": "GEMMA 4 OPERATIVO",
  "done": true,
  "done_reason": "stop",
  "elapsed_seconds": 32.03,
  "load_seconds": 27.45,
  "eval_seconds": 1.04,
  "eval_count": 8
}
```

No se utilizó Qwen, Llama ni el respaldo en esta inferencia.

## Incidencia de GPU y mitigación

El primer intento con selección CUDA automática falló tras 55.72 segundos. El log de Ollama registró:

```text
GGML_ASSERT(n_inputs < GGML_SCHED_MAX_SPLIT_INPUTS) failed
llama-server process has terminated: exit status 0xc0000409
```

La MX330 de 2 GB no pudo repartir este modelo. El reintento seguro con `num_gpu=0` cargó el modelo en CPU. La aplicación envía esta opción por solicitud; no se modificó la configuración global de Ollama. También usa contexto 4096, una sola solicitud, temperatura baja, `think=false` y salida limitada.

## JSON estructurado y caso demostrativo

La prueba de integración real y la interfaz enviaron el DNI ficticio `76543210`, sus cuatro antecedentes simulados y el relato solicitado. JSON validado:

```json
{
  "summary": "El usuario reporta dolor en la espalda al respirar y falta de aire desde ayer.",
  "risk_flags": [
    "dolor en la espalda al respirar",
    "falta de aire"
  ],
  "protocol_id": "respiratory_alert",
  "reason": "El relato indica dolor al respirar y falta de aire, activando el protocolo respiratory_alert.",
  "disclaimer": "No constituye diagnóstico ni indicación médica."
}
```

Evidencia persistida en la consulta `2`:

```json
{
  "model_used": true,
  "model_name": "gemma4:e2b",
  "fallback_reason": null,
  "protocol_id": "respiratory_alert",
  "priority": "Naranja",
  "checklist_actions": 4,
  "initial_close_permitted": false,
  "initial_block_reason": "Cierre bloqueado: faltan 4 acciones obligatorias.",
  "completed": 4,
  "final_close_permitted": true,
  "database_status": "closed"
}
```

La verificación posterior desde el navegador generó la consulta `3` y mostró en “Trazabilidad técnica” `model_used=true`, `model_name=gemma4:e2b`, `validated=1`, `protocol_id=respiratory_alert` y `fallback_reason=null`.

## Pruebas

Validación final de los lanzadores BAT (1 de agosto de 2026):

```text
00_INSTALAR_O_REPARAR.bat
32 passed in 65.61s
INSTALACIÓN COMPLETADA

01_PROBAR_TODO.bat
GEMMA REAL: OK (model=gemma4:e2b, response=GEMMA 4 OPERATIVO, num_gpu=0, 2.61s)
1 passed in 18.08s
RESPALDO DETERMINISTA: OK
32 passed in 17.52s
STREAMLIT HTTP: OK (200)
PID REGISTRADO: 13680
STREAMLIT TEMPORAL: detenido correctamente
SMOKE TEST COMPLETADO

Suite final después de la validación visual:
33 passed in 18.51s
```

El menú `INICIAR_TRIAJE360.bat` inició finalmente la aplicación con PID raíz `17220`, health HTTP 200 y apertura automática del navegador. Una detención previa comprobó que el PID raíz `25132` y sus hijos `22016` y `23520` terminaron, mientras Ollama continuó respondiendo HTTP 200.

Prueba de integración aislada:

```text
1 passed in 16.33s
```

Suite completa previa al smoke test:

```text
................... [100%]
19 passed in 16.65s
```

Resultado exacto dentro del smoke test:

```text
DEPENDENCIAS Y SQLITE: OK
MODELOS OLLAMA: gemma4:e2b, qwen2.5:3b, qwen2.5-coder:3b, llama3.2:3b
GEMMA REAL: OK (model=gemma4:e2b, response=GEMMA 4 OPERATIVO)
RESPALDO DETERMINISTA: OK
................... [100%]
19 passed in 32.20s
TRIaje 360 ya se esta ejecutando en http://localhost:8501 (PID 27776)
STREAMLIT HTTP: OK (200) - http://localhost:8501
SMOKE TEST COMPLETADO
```

La prueba de integración solo marca `SKIPPED` cuando Ollama o el modelo no están disponibles. En esta validación se ejecutó y aprobó, sin skips.

## Respaldo determinista

Se probó por separado con un relato respiratorio y produjo `respiratory_alert`. El smoke test informa `RESPALDO DETERMINISTA: OK`. Una ejecución anterior persistida conserva `model_used=0`, `model_name=deterministic-fallback`, bloqueo, cuatro acciones y cierre, demostrando que el respaldo no depende de Gemma.

## HTTP y aplicación

- URL: `http://localhost:8501`.
- Health endpoint: `HTTP 200`, contenido `ok`.
- Interfaz verificada en navegador: paciente, antecedentes, estado de modelo, resumen, banderas, protocolo, checklist, bloqueo y trazabilidad visibles.
- stderr de Streamlit: vacío durante la validación.

## Limitaciones de hardware y seguridad

La inferencia se ejecuta en CPU para evitar el fallo CUDA de la MX330. La primera carga tarda aproximadamente 27–40 segundos y consume una porción importante de los 12 GB de RAM; no conviene ejecutar inferencias concurrentes. El modelo no diagnostica, prescribe, recomienda tratamientos, determina negligencia ni controla el cierre. Los protocolos y datos son demostrativos; toda decisión corresponde a un profesional autorizado.
