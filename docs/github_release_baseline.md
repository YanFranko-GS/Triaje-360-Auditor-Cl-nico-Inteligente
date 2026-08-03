# GitHub public release baseline

Baseline captured on 2026-08-02 (America/Lima) from `release/final-triaje360` at `6b5913e` before public-documentation changes.

## Git and environment

- Base branch was clean and matched `origin/release/final-triaje360`.
- The base contained all commits from `fix/product-ui-auth-voice-workflow`, `feature/rag-multivista-clinica`, and `feature/integracion-gemma4-ui-clinica` and was respectively 5, 9, and 12 commits ahead.
- Python: 3.12.13 in `.venv`.
- pip: 25.0.1.
- Ollama: 0.32.4, API reachable on localhost.
- Required model: `gemma4:e2b`, digest beginning `7fbdbf8f5e45`, 5.1B Q4_K_M, present locally.

## Baseline test evidence

```text
.\.venv\Scripts\python.exe -m pytest -q
109 passed, 1 warning in 102.27s
```

The warning is Python's deprecation notice for `audioop`, scheduled for removal in Python 3.13.

## Baseline smoke evidence

Command:

```powershell
.\01_PROBAR_TODO.bat
```

Observed result:

```text
Ollama API: HTTP 200
Model detected: gemma4:e2b
Real Gemma inference: GEMMA 4 OPERATIVO (3.70s, CPU)
Gemma integration test: 1 passed in 24.28s
Deterministic fallback: OK
Complete pytest: 109 passed, 1 warning in 40.71s
Streamlit health: HTTP 200, body ok
Smoke test: completed
```

The temporary Streamlit process was stopped by the smoke launcher. A separate validated start through `02_INICIAR_TRIAJE360.bat` subsequently returned HTTP 200 and was used for role-based visual checks.

## Role and UI validation

The running application was exercised with synthetic accounts only:

- existing patient login and consented text intake;
- visible Gemma/Ollama and RAG status;
- triage nurse queue, narrative, pain, proposal, and professional-decision controls;
- attending physician history, triage, pending data, and evidence view;
- administrator audit table and filtered database catalog.

Real 1440×900 captures are stored under `docs/assets/screenshots/`. No password is visible in the captured login forms.

## Baseline conclusion

The selected release base was reproducible on the validated Windows machine with local Ollama and Gemma. This evidence is environment-specific and is not a claim of production readiness, clinical certification, or compatibility with all hardware.
