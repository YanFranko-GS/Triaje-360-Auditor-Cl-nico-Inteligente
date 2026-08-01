# Opciones de despliegue

## Perfil validado: demostración local

Streamlit, SQLite y Ollama se ejecutan en la misma computadora. Ollama permanece en `127.0.0.1`, `ALLOW_LAN_ACCESS=false`, `AI_PROVIDER=ollama` y `num_gpu=0` para estabilidad en el equipo de prueba. Es la única modalidad validada en este repositorio.

## Proveedor hospedado (no configurado)

`services/ai_provider.py` define la frontera para un proveedor hospedado, pero falla de forma segura con “no configurado”. El repositorio no contiene claves ni activa llamadas externas. Habilitarlo exige gestión de secretos, contratos de tratamiento, residencia de datos, registros de acceso y evaluación de privacidad.

## Red local o producción

No está autorizada por defecto. Antes de exponer Streamlit u Ollama se requieren autenticación real, TLS, control de acceso, cifrado, base multiusuario, gestión de sesiones, hardening, respaldo, monitoreo, retención, evaluación regulatoria y validación clínica. Nunca se debe publicar el puerto de Ollama sin una capa de seguridad aprobada.
