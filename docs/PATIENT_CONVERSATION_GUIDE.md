# Guía de conversación del paciente

## Principios

- Una pregunta por turno.
- Lenguaje breve, neutral y comprensible.
- No mostrar prompts, JSON, diagnósticos ni tratamientos.
- Reutilizar memoria estructurada confirmada y pedir confirmación si puede haber cambiado.
- Permitir voz, texto, **No sé**, **No aplica** o **Omitir**.
- No convertir un dato no preguntado en ausencia confirmada.
- Terminar al completar mínimos, detectar revisión inmediata, alcanzar el máximo o recibir una solicitud de envío.

## Ejemplo completo

**Asistente:** “Cuéntenos qué siente.”

**Paciente:** “Me duele el pecho desde esta mañana.”

**Asistente:** “¿El dolor comenzó de forma súbita o gradual?”

**Paciente:** “Súbita.”

**Asistente:** “En una escala de 0 a 10, ¿cuánto dolor siente ahora?”

**Paciente:** “8.”

**Asistente:** “¿Tiene dificultad para respirar, sudoración, náuseas o mareo?”

**Paciente:** “Tengo dificultad para respirar y sudoración.”

**Sistema:** “Se requiere valoración prioritaria. La información debe ser confirmada por personal sanitario.”

**Asistente:** “Revise la información antes de enviarla.”

La pantalla final presenta campos completados, pendientes, origen, confirmación y el botón **Enviar a triaje**. Ante una señal inmediata se detienen las preguntas adicionales.
