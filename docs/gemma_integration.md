# Integración con Gemma 4

## Precondiciones validadas

La configuración apunta a `http://localhost:11434` y `gemma4:e2b`. El cliente consulta `/api/tags`; si el nombre exacto no aparece, no realiza inferencia y activa respaldo. La validación real se completó con Ollama 0.32.4 y `gemma4:e2b` (familia `gemma4`, 5.1B, Q4_K_M, 7.2 GB).

## Solicitud

Se usa `/api/chat`, `stream=false`, JSON Schema derivado de Pydantic, `think=false`, temperatura `0.1`, `num_predict=320`, contexto 4096 y timeout de 120 segundos. El prompt prohíbe diagnóstico, prescripción, datos inventados, campos adicionales, markdown y razonamiento interno.

En la NVIDIA MX330 de 2 GB, la selección CUDA automática de Ollama falló al repartir el modelo (`GGML_SCHED_MAX_SPLIT_INPUTS`). Para este proyecto se envía `num_gpu=0` en cada solicitud. Es una decisión local y reversible: no expone Ollama a la red ni modifica su configuración global. La inferencia directa validada tardó 32.03 segundos, incluidos 27.45 segundos de carga en CPU.

## Validación

Se exige respuesta HTTP correcta, nombre exacto del modelo, contenido no vacío y un objeto JSON completo. `GemmaAnalysis` limita textos y banderas, prohíbe extras, requiere descargo y restringe el protocolo. `risk_flags` es obligatorio y un protocolo respiratorio exige al menos una bandera.

Solo después de esos controles se registra `model_used=true`. El caso real persistido confirmó `model_name=gemma4:e2b`, `respiratory_alert`, prioridad naranja, cuatro acciones, bloqueo inicial y cierre posterior habilitado por Python. Gemma no decide el cierre.

Todos los errores activan una ejecución determinista y un evento auditable. La evidencia visible está en “Trazabilidad técnica”, `model_responses` y [gemma4_real_validation.md](gemma4_real_validation.md).

## Gemma con RAG trazable

El cliente acepta fragmentos recuperados y agrega una instrucción de sistema que los trata como datos no confiables. Cada fragmento lleva `source_id`, `chunk_id`, título, entidad, URL, fecha, población y hash. Gemma puede usar únicamente esos identificadores; `rag.citations.validate_analysis_citations` rechaza citas ajenas a la ejecución.

La interfaz comunica `OFFLINE`, `STARTING`, `READY`, `WARMING_UP`, `ANALYZING`, `VALIDATING`, `COMPLETED`, `FALLBACK` y `ERROR`. Durante inferencia muestra etapas indeterminadas y tiempo transcurrido. Al finalizar informa duración, modelo, CPU, documentos recuperados, Pydantic, `model_used` y fallback. Estos indicadores describen actividad técnica, no confianza clínica.

`AI_PROVIDER=ollama` es el único proveedor operativo. La alternativa `hosted` no contiene implementación ni secretos y devuelve un estado seguro de “no configurado”.

## Instalación y diagnóstico

La vía recomendada en Windows es hacer doble clic en `INICIAR_TRIAJE360.bat`: **Instalar o reparar** verifica Ollama y ofrece descargar exclusivamente `gemma4:e2b`; **Probar toda la instalación** ejecuta inferencia real con `num_gpu=0`; **Iniciar aplicación** precalienta una vez y abre el navegador. Los logs quedan en `logs`.

Si la ejecución de scripts PowerShell está deshabilitada, no cambie `ExecutionPolicy`. Los BAT funcionan sin esa modificación. Solo como alternativa de emergencia:

```bat
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\smoke_test.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\run_windows.ps1"
```
