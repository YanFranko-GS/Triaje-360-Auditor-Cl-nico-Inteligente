# TRIaje 360 agent operating guide

## Project identity

TRIaje 360 is a local, Spanish-language research and validation platform for AI-assisted patient intake, supervised triage, longitudinal context, and auditable documentation. It uses synthetic data only. It is not a certified medical device, does not diagnose or prescribe, and does not replace professional judgment or emergency services.

These instructions apply to the entire repository. A more specific `AGENTS.md` may narrow them for a subdirectory but must not weaken the clinical, privacy, or evidence rules below.

## Required orientation

Before editing:

1. Read `README.md`, `docs/architecture-overview.md`, `docs/safety_and_limitations.md`, and relevant tests.
2. Inspect Git status, current branch, remotes, and recent commits.
3. Do not work directly on `main` or `develop`; create a focused branch from the requested base.
4. Preserve unrelated changes and never commit local databases, `.env`, logs, audio, models, credentials, or real data.
5. Establish a baseline with the commands in this guide and report actual evidence.

## Architecture

- `app.py`: Streamlit entry point, authentication gate, role navigation, and page dispatch.
- `ui/`: Spanish interface, AI status, patient intake, voice capture, triage, physician, longitudinal, audit, and admin views.
- `auth_service.py`: synthetic patient/professional authentication, scrypt hashes, local sessions, and login events.
- `clinical_db.py`: demo workflow schema, idempotent migrations, synthetic seeds, queues, model/RAG records, and audit events.
- `longitudinal_db.py`: relational longitudinal schema, registration, history, statistics, and schema catalog.
- `intake_service.py`: Gemma-backed structured extraction, deterministic fallback, confirmation, and one-at-a-time follow-up.
- `clinical_verifier.py`: second-stage completeness and contradiction verification.
- `triage_service.py`: configurable five-level proposal requiring professional disposition.
- `services/ollama_client.py`: Ollama health, structured generation, validation, and fallback.
- `audio_pipeline.py` and `services/local_asr.py`: WAV validation/normalization and optional Vosk transcription.
- `rag/`: approved-source ingestion, lexical retrieval, citation validation, and safety filters.
- `schemas.py`: Pydantic contracts.
- `scripts/`: idempotent seed, database inspection, schema export, Gemma checks, and Windows launcher.
- `tests/`: unit, integration, safety, authentication, voice, workflow, UI, and launcher contracts.

## Core functions

The system must continue to support:

- existing and newly registered synthetic patients;
- explicit consent and editable text or optional voice intake;
- structured extraction without treating inference as patient confirmation;
- missing-field follow-up, deterministic fallback, and contradiction checks;
- supervised five-level triage with professional accept/change/escalate/reevaluate actions;
- physician review of history, evidence, pending data, and professional records;
- approved-source RAG with traceable retrieval reasons and limitations;
- `model_used`, model identity, validation, duration, and fallback traceability;
- role-scoped navigation and safe administrative inspection;
- idempotent local database creation from an empty environment.

## Roles and facilities

- `PATIENT`: own portal, history, and tracking.
- `TRIAGE_NURSE`: triage station at the assigned facility.
- `TRIAGE_DOCTOR`: triage station with professional review responsibility.
- `ATTENDING_PHYSICIAN`: physician workspace.
- `SUPERVISOR`: operational and audit review.
- `ADMIN`: all demo views and safe database catalog.

`DEMO_FAC_A` is Centro Andino and `DEMO_FAC_B` is Policlínico Costa. Never broaden a role simply to make a test or screenshot easier.

## Configuration

Copy `.env.example` to `.env`; do not commit `.env`. Paths in code and docs must be relative to `<PROJECT_ROOT>`, never a developer's home directory.

Important settings:

```dotenv
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:e2b
PRIMARY_MODEL=gemma4:e2b
REVIEW_MODEL=gemma4:e2b
DATABASE_PATH=data/triaje360.db
ALLOW_LAN_ACCESS=false
STORE_DEMO_AUDIO=false
ASR_PROVIDER=vosk
```

Maintain localhost-only defaults and audio-storage opt-out.

## Installation

Windows reference setup:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe scripts\create_demo_accounts.py
.\.venv\Scripts\python.exe scripts\seed_demo_data.py
```

The seed and migration commands must remain safe to run repeatedly and must not require a committed SQLite file.

## Ollama and Gemma 4

```powershell
ollama --version
ollama pull gemma4:e2b
ollama list
```

Verify `http://localhost:11434/api/tags` and exact model identity before claiming real AI validation. Do not substitute another model silently. Tests that require real inference use the `integration` marker. An unavailable model must produce a visible, auditable fallback rather than fabricated success.

## Vosk and voice

Voice support is optional:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-voice.txt
```

Place a separately licensed Spanish model under `.demo/asr_models/` and configure `ASR_MODEL_PATH`. Enforce separate audio consent, maximum duration, MIME and signal checks, mono 16 kHz normalization, editable transcription, and confirmation. Do not store audio unless a narrowly scoped test explicitly opts in; never commit `.wav` files.

## RAG

Only ingest entries approved in `docs/source_register.csv`. Preserve source ID, chunk ID, score, retrieval reason, population, applicability, and limitations. Never ingest patient data into the evidence corpus, present retrieval as a diagnosis, or claim an institution endorses the project. Changes to source governance require tests and documentation.

## Pydantic and deterministic validation

Treat model output as untrusted input. Validate it against Pydantic schemas, normalize safe values, record invalid output, and activate deterministic fallback. Inferred fields must require confirmation. Keep the independent completeness/contradiction stage and professional review signals.

## SQLite

Keep foreign keys enabled and migrations idempotent. Database inspection must exclude `password_hash`, salts, session identifiers, and secrets. Tests must use temporary databases where possible. Local `*.db`, `*.sqlite*`, and journals remain ignored.

## Operational flow

```text
Patient authentication/registration
  -> consented text or voice narrative
  -> structured extraction and confirmation
  -> completeness/contradiction verification
  -> supervised triage and professional disposition
  -> physician documentary review
  -> auditable closure
```

Do not skip gates by manipulating session state or direct database writes in product code.

## Clinical restrictions

- No automatic diagnosis, prescription, treatment, discharge, or clinical closure.
- No claim of medical-device certification, government approval, institutional integration, or official national standard.
- No universal vital-sign or triage thresholds presented as locally authorized without versioned configuration and professional governance.
- No real patient, staff, or institution data in code, tests, screenshots, issues, logs, or commits.
- Escalation signals must tell users to seek present staff or emergency help; the application is not an emergency channel.
- Every generated clinical consideration must remain reviewable, attributable, and rejectable by a professional.

## Tests and validation

Run the smallest relevant tests during development and all of these before completion:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\01_PROBAR_TODO.bat
git diff --check
git status --short
```

For environments without Ollama, run `.\.venv\Scripts\python.exe -m pytest -q -m "not integration"` and state that integration was not validated. A complete local release claim additionally requires:

```text
GET http://127.0.0.1:8501/_stcore/health -> 200 ok
```

When changing UI behavior, verify the real application through the affected patient and professional roles and capture only synthetic data.

## Security and privacy

- Keep `ALLOW_LAN_ACCESS=false` and Ollama on localhost by default.
- Never print or persist submitted passwords; demo credentials may appear only in public demo documentation.
- Do not expose hashes, salts, `.env`, tokens, API keys, session IDs, local paths, or user-specific data.
- Treat logs and database files as local evidence, not release artifacts.
- Do not add telemetry, external AI calls, downloads, or network exposure without explicit scope, disclosure, and review.

## Git rules

- Branch from the requested base; normally contributors branch from `develop`.
- Use focused commits such as `feat:`, `fix:`, `docs:`, `test:`, `ci:`, or `chore:`.
- Do not force-push, rewrite shared history, merge without authorization, or modify `main`/`develop` directly.
- Review `git diff --cached` before committing and scan for secrets and generated local artifacts.
- A change is not complete merely because it was committed or pushed.

## Completion criteria

An agent may report completion only when:

- requested behavior and documentation exist;
- relevant roles and safety copy remain correct;
- migrations/seeds work from an empty local database and remain idempotent;
- tests pass at the level claimed;
- the application starts and health is HTTP 200 when runtime validation is in scope;
- Gemma identity and real inference are evidenced when AI integration is claimed;
- no secrets, real data, audio, database, logs, models, or personal paths are tracked;
- `git diff --check` passes and Git state is explicitly reported;
- branch, commits, push, and non-merge status are accurately reported.

## Expected report

Summarize: base and working branch; behavior and files changed; synthetic accounts or fixtures used; tests with counts and durations; smoke and HTTP results; Ollama/Gemma model result or limitation; visual checks; security scan; commits and SHAs; push/PR state; remaining limitations; and explicit confirmation that no merge or sensitive artifacts were introduced.
