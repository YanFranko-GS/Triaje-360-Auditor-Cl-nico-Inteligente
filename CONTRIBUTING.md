# Contribuir

1. Cree una rama y un entorno con `setup_windows.ps1`.
2. No use datos reales ni agregue protocolos clínicos sin revisión autorizada.
3. Mantenga la lista cerrada sincronizada entre `schemas.py` y `data/protocols.json`.
4. Añada pruebas para todo cambio de validación, persistencia o cierre.
5. Ejecute `.venv\Scripts\python.exe -m pytest -q` y `smoke_test.ps1`.
6. No confirme `.env`, bases SQLite, logs, modelos ni secretos.

Los cambios deben conservar lenguaje no diagnóstico, trazabilidad y degradación segura.
