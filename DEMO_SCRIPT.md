# Guion de demostración (máximo 3 minutos)

## Ejecución con doble clic

Descomprima el proyecto y haga doble clic en `INICIAR_TRIAJE360.bat`. La primera vez elija **Instalar o reparar**, después **Probar toda la instalación** y finalmente **Iniciar aplicación**. El navegador debe abrir `http://localhost:8501`; al terminar, vuelva al menú y elija **Detener aplicación**. Los BAT no requieren administrador ni una modificación permanente de `ExecutionPolicy`.

Si aparece «la ejecución de scripts está deshabilitada en este sistema», no ejecute el PS1 directamente: use `INICIAR_TRIAJE360.bat`. La alternativa de emergencia es `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\run_windows.ps1"`, cuyo bypass afecta solo a ese proceso.

**0:00–0:20 — Evidencia local.** Ejecutar `ollama list` y señalar `gemma4:e2b` de 7.2 GB. Aclarar que se ejecuta localmente, con contexto 4096 y CPU para estabilidad en 12 GB de RAM.

**0:20–0:45 — Aplicación.** Abrir `http://localhost:8501`. Presentar TRIaje 360 como prototipo educativo de auditoría concurrente de completitud documental: no diagnostica, prescribe ni reemplaza al profesional.

**0:45–1:15 — Caso real.** Mostrar DNI ficticio `76543210`, antecedentes simulados y el relato “Tengo dolor en la espalda al respirar y me falta el aire desde ayer.” Mantener activo **Intentar análisis con Gemma 4** y pulsar **Analizar con Gemma 4**.

**1:15–1:45 — Resultado Gemma.** Mostrar resumen estructurado, prioridad naranja, `respiratory_alert` y banderas. Abrir **Trazabilidad técnica** y destacar `model_used: true`, `model_name: gemma4:e2b` y JSON validado. Gemma estructura; no cierra la consulta.

**1:45–2:25 — Control determinista.** Mostrar 0/4 y botón de cierre deshabilitado. Registrar las cuatro acciones ficticias; enseñar 4/4 y cierre habilitado. Finalizar y explicar que Python, no Gemma, verificó el checklist y guardó la auditoría SQLite.

**2:25–2:50 — Resiliencia.** Desactivar el toggle de Gemma y repetir el análisis. Mostrar “Respaldo determinista”, `model_used: false` y la causa explícita. Esto demuestra continuidad sin simular uso del modelo.

**2:50–3:00 — Cierre.** Recordar que usa datos y protocolos ficticios, no determina negligencia y toda decisión corresponde a un profesional autorizado.

## Recorrido de acceso y voz (4–6 minutos)

1. Abra la aplicación y muestre que no hay selector abierto de perfiles. Ingrese como paciente `76543210` / `1999-01-01`.
2. Acepte la captura sintética. Grabe un segmento WAV o escriba el relato; reproduzca, revise y confirme la transcripción editable.
3. Pulse **Organizar información**. Muestre campos con estado, interrupción si aparece una señal configurada y una sola pregunta de seguimiento cuando falten datos.
4. Envíe a triaje y abra **Seguimiento**. Cierre sesión.
5. Ingrese como `nurse.demo` / `Clinica360-N1!`, revise cola y evidencia; registre la decisión profesional.
6. Ingrese como médico o administrador para revisar cronología/checklist. Muestre **Comprobar asistente**, modelo real y fallback explícito.

## Recorrido multivista (3–5 minutos)

1. En **Inicio**, muestre ambos logotipos, el caso `76543210`, el estado real de Gemma y los cuatro fragmentos RAG aprobados.
2. En **Portal del paciente**, acepte el consentimiento demo, ingrese un relato respiratorio ficticio, marque dolor y registre 0–10. Envíe y confirme `AWAITING_TRIAGE`.
3. En **Estación de triaje**, abra la cola y pulse **Analizar caso con Gemma 4 y RAG**. Señale actividad por etapas, duración, CPU, `model_used`, Pydantic y las citas; explique que recuperación no equivale a exactitud clínica.
4. Registre signos ficticios y una decisión profesional con justificación. Muestre el avance a `AWAITING_PHYSICIAN`.
5. En **Panel médico**, recorra datos, faltantes, banderas, evidencia/citas y trazabilidad. Guarde una nota ficticia y cierre sólo cuando el control documental lo permita.
6. En **Auditoría**, muestre autor, rol, acción, fuente, modelo y decisiones. En **Datos ficticios**, enseñe estadísticas, gobierno de fuentes y reset acotado.
