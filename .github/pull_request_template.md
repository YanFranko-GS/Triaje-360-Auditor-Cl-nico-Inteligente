## Summary

Describe the focused change and why it is needed.

## Scope

- [ ] Product code
- [ ] Tests
- [ ] Documentation
- [ ] CI or operations
- [ ] RAG source governance
- [ ] Database migration

## Safety and privacy

- [ ] Uses synthetic data only.
- [ ] Preserves professional confirmation and non-diagnostic wording.
- [ ] Preserves Pydantic validation, deterministic fallback, and auditability where applicable.
- [ ] Does not add secrets, `.env`, databases, logs, audio, model files, or personal paths.
- [ ] Does not claim certification, official endorsement, automatic diagnosis, or prescription.

Explain any clinical, privacy, authorization, evidence, or failure-mode impact:

## Test evidence

Include exact commands, exit codes, counts, and relevant sanitized output.

```text
python -m pytest -q -m "not integration"

# If locally available:
python -m pytest -q
01_PROBAR_TODO.bat
GET /_stcore/health ->
```

## Visual evidence

For UI changes, attach real screenshots using synthetic records. Do not show passwords or private desktop/browser content.

## Checklist

- [ ] Branch is based on `develop` and does not target `main` directly.
- [ ] Relevant documentation and changelog are updated.
- [ ] Migrations and seeds remain idempotent.
- [ ] `git diff --check` passes.
- [ ] I reviewed the diff for sensitive or generated artifacts.
