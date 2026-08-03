# Security policy

## Scope

TRIaje 360 is a local research and validation platform using synthetic data. Demo authentication, Streamlit sessions, and SQLite are not a production clinical security architecture.

## Safe operation

- Never enter or import real patient, staff, credential, or institution data.
- Keep Streamlit and Ollama bound to localhost; do not expose port 8501 or 11434 to a LAN or the internet.
- Keep `ALLOW_LAN_ACCESS=false` and `STORE_DEMO_AUDIO=false` unless a narrowly scoped local test requires otherwise.
- Do not commit `.env`, databases, logs, audio, model files, hashes, salts, session IDs, tokens, or private keys.
- Use the public demo credentials only in a disposable local synthetic environment.
- Treat model output and retrieved text as untrusted input requiring validation and professional review.

## Reporting a vulnerability

Do not open a public issue containing exploit details, sensitive logs, local database contents, credentials, or potentially identifiable information.

Use the repository's **Security** tab to submit a private vulnerability report when private reporting is enabled. If that option is unavailable, contact the repository owner privately through the contact method on their GitHub profile and provide only the minimum information needed to establish a secure channel.

Include:

- affected commit or version;
- component and preconditions;
- reproducible steps using synthetic data;
- expected and observed behavior;
- impact and suggested mitigation, if known.

Do not include real health data. Maintainers will acknowledge a valid private report, investigate scope, coordinate a fix, and disclose it only after affected users have a reasonable mitigation path.

## Not a clinical emergency channel

Security reports are not monitored as a clinical service. Do not send medical emergencies or personal health information to the project. Contact local emergency services or an authorized healthcare professional.
