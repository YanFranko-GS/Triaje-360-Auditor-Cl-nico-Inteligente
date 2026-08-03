# Synthetic demo access

All identities, facilities, histories, and credentials below exist solely for local demonstration. They are intentionally public and must never be reused for real systems. The seed stores professional passwords as scrypt hashes; this guide lists only the deliberate plaintext demo values.

## Facilities

| Identifier | Display name | Typical demo profile |
| --- | --- | --- |
| `DEMO_FAC_A` | Centro Andino | Patient, nurse, attending physician, supervisor, admin |
| `DEMO_FAC_B` | Policlínico Costa | Triage physician |

These are synthetic facilities. Names referencing insurance categories inside patient fixtures do not imply integration, partnership, or approval.

## Patient access

| Scenario | Identifier | Second factor | Expected access |
| --- | --- | --- | --- |
| Existing patient | `76543210` | Birth date `1999-01-01` | Portal, own history, tracking |
| Existing patient 2 | `87654321` | Birth date `1990-02-02` | Portal scoped to Patient 02 |
| Existing patient 3 | `11223344` | Birth date `1985-03-03` | Portal scoped to Patient 03 |
| New patient | Use **Register new patient** | New synthetic details | Newly created local profile |

Use fictitious names, contacts, addresses, allergies, medication, and narrative when registering a new patient.

## Professional accounts

| Profile | Username | Password | Facility | Expected views |
| --- | --- | --- | --- | --- |
| Triage nurse | `nurse.demo` | `Clinica360-N1!` | Centro Andino | Home, triage station |
| Triage physician | `triage.doctor` | `Clinica360-TD!` | Policlínico Costa | Home, triage station |
| Attending physician | `attending.demo` | `Clinica360-M1!` | Centro Andino | Home, physician panel |
| Supervisor | `supervisor.demo` | `Clinica360-S1!` | Centro Andino | Home, operational review, audit |
| Administrator | `admin.demo` | `Clinica360-A1!` | Centro Andino | All demo views, audit, safe schema catalog |

The supervisor and administrator may authenticate across demo facilities by design. Other accounts are facility-scoped.

## Suggested test flow

1. Run `scripts/create_demo_accounts.py` and `scripts/seed_demo_data.py`.
2. Log in as patient `76543210`; confirm the displayed synthetic identity and birth date.
3. Consent, enter a synthetic symptom narrative, review the text, and complete follow-up fields.
4. Submit to triage; verify tracking does not expose other patients.
5. Log out and enter as `nurse.demo`; open **Estación de triaje**.
6. Select the synthetic encounter, review narrative and history, add fictitious vital signs, and inspect the proposed level.
7. Record a professional demo disposition with an explicit synthetic justification.
8. Log in as `attending.demo`; review current summary, history, triaje, missing data, and cited source limitations.
9. Log in as `supervisor.demo`; inspect the permitted audit view.
10. Log in as `admin.demo`; inspect audit events and the filtered table catalog without hashes or credentials.

## Expected safety behavior

- Patient pages do not diagnose or prescribe.
- Inferred fields require confirmation.
- Model unavailability activates a visible deterministic fallback.
- A proposed triage level is stored separately from the professional decision.
- Roles cannot navigate to unauthorized pages.
- Failed logins are recorded without passwords.
- Audio content is not persisted by default.
- Audit and admin screens never display password hashes, salts, or secrets.
