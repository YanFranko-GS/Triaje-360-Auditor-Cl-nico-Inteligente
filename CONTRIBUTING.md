# Contributing to TRIaje 360

Thank you for helping improve this research and validation platform. Contributions must preserve synthetic-only data, professional supervision, traceable evidence, and safe failure behavior.

## Before starting

1. Read `README.md`, `AGENTS.md`, `docs/architecture-overview.md`, and `docs/safety_and_limitations.md`.
2. Discuss broad clinical, privacy, schema, or architecture changes in an issue before implementation.
3. Never use real patient, staff, or institution data.

## Fork and branch workflow

```powershell
git clone https://github.com/<YOUR-USER>/Triaje-360-Auditor-Cl-nico-Inteligente.git
cd Triaje-360-Auditor-Cl-nico-Inteligente
git remote add upstream https://github.com/YanFranko-GS/Triaje-360-Auditor-Cl-nico-Inteligente.git
git fetch upstream
git switch develop
git pull --ff-only upstream develop
git switch -c feature/short-description
```

Do not commit directly to `main` or `develop`. Use a focused feature, fix, docs, test, CI, or chore branch.

## Local setup

Use Python 3.12 and an isolated environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe scripts\create_demo_accounts.py
.\.venv\Scripts\python.exe scripts\seed_demo_data.py
```

For optional local voice testing, install `requirements-voice.txt` and supply your own licensed Vosk model under `.demo/`.

## Development rules

- Preserve non-diagnostic wording and explicit patient/professional confirmation.
- Treat AI output as untrusted and keep Pydantic validation and deterministic fallback.
- Do not add clinical thresholds, protocols, or applicability claims without versioned sources and professional review.
- Keep migrations and synthetic seeds idempotent.
- Add or update tests for behavior, persistence, permissions, safety, and failure paths.
- Keep UI text in Spanish unless a product-language change has been agreed.
- Do not add external telemetry, hosted AI calls, or network exposure without explicit review.

## Files that must not be committed

- `.env`, tokens, API keys, certificates, or private credentials;
- SQLite databases, journals, logs, PID files, or coverage output;
- real or identifiable clinical data;
- WAV or other captured audio;
- Ollama, Vosk, GGUF, or other model files;
- editor metadata, machine-specific paths, or generated caches.

Public demo credentials documented in `docs/DEMO_ACCESS.md` are the only deliberate exception; never reuse them elsewhere.

## Tests

```powershell
# CI-safe suite
.\.venv\Scripts\python.exe -m pytest -q -m "not integration"

# Full local suite with Ollama and gemma4:e2b
.\.venv\Scripts\python.exe -m pytest -q

# End-to-end Windows validation
.\01_PROBAR_TODO.bat

git diff --check
```

If a dependency prevents an integration test, say so in the Pull Request and never label it as passing.

## Commits and Pull Requests

Use clear imperative commits, for example:

```text
feat: add confirmed duration follow-up
fix: preserve fallback audit reason
docs: clarify local voice setup
test: cover supervisor page restrictions
```

Before opening a Pull Request:

1. Rebase or update your branch from `develop` without rewriting other contributors' work.
2. Review `git diff` for secrets, generated data, and unrelated changes.
3. Complete the PR template with safety impact and exact test evidence.
4. Link the issue and request relevant technical and clinical review.

Open the Pull Request with base `develop`. Maintainers will decide when and how it is merged.
