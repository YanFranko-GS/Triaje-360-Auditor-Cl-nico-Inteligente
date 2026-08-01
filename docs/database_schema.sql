PRAGMA foreign_keys=ON;

CREATE TABLE actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consultation_id INTEGER NOT NULL REFERENCES consultations(id) ON DELETE CASCADE,
                action_id TEXT NOT NULL,
                value_json TEXT NOT NULL,
                completed INTEGER NOT NULL,
                actor TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

CREATE TABLE allergies(
                id INTEGER PRIMARY KEY AUTOINCREMENT, patient_dni TEXT NOT NULL REFERENCES patients(dni) ON DELETE CASCADE,
                substance TEXT NOT NULL, status TEXT NOT NULL, source TEXT NOT NULL,
                confirmed_by TEXT, confirmed_at TEXT, created_at TEXT NOT NULL
            );

CREATE TABLE audit_events(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER REFERENCES encounters(id),
                patient_dni TEXT REFERENCES patients(dni), event_type TEXT NOT NULL,
                actor_id TEXT, details_json TEXT NOT NULL, created_at TEXT NOT NULL
            );

CREATE TABLE audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consultation_id INTEGER REFERENCES consultations(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL,
                details_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

CREATE TABLE checklist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consultation_id INTEGER NOT NULL REFERENCES consultations(id) ON DELETE CASCADE,
                action_id TEXT NOT NULL,
                label TEXT NOT NULL,
                action_type TEXT NOT NULL,
                constraints_json TEXT NOT NULL DEFAULT '{}',
                value_json TEXT,
                completed INTEGER NOT NULL DEFAULT 0,
                UNIQUE(consultation_id, action_id)
            );

CREATE TABLE clinical_notes(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES encounters(id),
                section TEXT NOT NULL, note TEXT NOT NULL, confirmed INTEGER NOT NULL DEFAULT 1,
                recorded_by TEXT NOT NULL, recorded_at TEXT NOT NULL
            );

CREATE TABLE closures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consultation_id INTEGER NOT NULL REFERENCES consultations(id) ON DELETE CASCADE,
                permitted INTEGER NOT NULL,
                reason TEXT NOT NULL,
                actor TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

CREATE TABLE consultations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dni TEXT NOT NULL,
                symptoms TEXT NOT NULL,
                protocol_id TEXT NOT NULL,
                priority TEXT NOT NULL,
                model_name TEXT NOT NULL,
                model_used INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'blocked',
                block_reason TEXT,
                created_at TEXT NOT NULL,
                closed_at TEXT
            );

CREATE TABLE conversation_turns(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER REFERENCES encounters(id),
                patient_dni TEXT NOT NULL REFERENCES patients(dni), turn_no INTEGER NOT NULL,
                speaker TEXT NOT NULL, question TEXT, response TEXT, resolution_reason TEXT,
                source TEXT NOT NULL, created_at TEXT NOT NULL
            );

CREATE TABLE demo_allergies(id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE);

CREATE TABLE demo_audio_segments(
                id TEXT PRIMARY KEY, audio_session_id TEXT NOT NULL REFERENCES demo_audio_sessions(id) ON DELETE CASCADE,
                sequence_no INTEGER NOT NULL, mime_type TEXT NOT NULL, duration_seconds REAL NOT NULL,
                sample_rate INTEGER NOT NULL, audio_sha256 TEXT NOT NULL, signal_status TEXT NOT NULL,
                stored_path TEXT, created_at TEXT NOT NULL, UNIQUE(audio_session_id,sequence_no)
            );

CREATE TABLE demo_audio_sessions(
                id TEXT PRIMARY KEY, encounter_id INTEGER REFERENCES demo_encounters(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL, noise_profile TEXT NOT NULL, consent INTEGER NOT NULL,
                store_audio INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL, created_at TEXT NOT NULL, completed_at TEXT
            );

CREATE TABLE demo_audit_events(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER REFERENCES demo_encounters(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL, details_json TEXT NOT NULL, actor_id TEXT,
                source TEXT NOT NULL, created_at TEXT NOT NULL
            );

CREATE TABLE demo_clinical_notes(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES demo_encounters(id) ON DELETE CASCADE,
                section TEXT NOT NULL, note TEXT NOT NULL, source TEXT NOT NULL,
                created_by TEXT, created_at TEXT NOT NULL
            );

CREATE TABLE demo_conversation_turns(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER REFERENCES demo_encounters(id) ON DELETE CASCADE,
                turn_no INTEGER NOT NULL, speaker TEXT NOT NULL, question TEXT, response TEXT,
                source TEXT NOT NULL, confirmed_by TEXT, created_at TEXT NOT NULL
            );

CREATE TABLE demo_encounters(
                id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT NOT NULL REFERENCES demo_patients(id),
                facility_id TEXT NOT NULL REFERENCES demo_facilities(id), status TEXT NOT NULL,
                chief_complaint TEXT NOT NULL, narrative TEXT NOT NULL, duration TEXT,
                pain_present INTEGER NOT NULL DEFAULT 0, pain_score INTEGER, pain_location TEXT,
                onset TEXT, evolution TEXT, accompanying_symptoms_json TEXT NOT NULL DEFAULT '[]',
                consent_demo INTEGER NOT NULL DEFAULT 0, mobility TEXT, companion TEXT,
                pregnancy_possible TEXT, source TEXT NOT NULL, created_by TEXT, updated_by TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );

CREATE TABLE demo_facilities(
                id TEXT PRIMARY KEY, institution_id TEXT NOT NULL REFERENCES demo_institutions(id),
                name TEXT NOT NULL, triage_role TEXT NOT NULL, source TEXT NOT NULL, status TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );

CREATE TABLE demo_field_confirmations(
                id INTEGER PRIMARY KEY AUTOINCREMENT, extraction_id INTEGER NOT NULL REFERENCES demo_field_extractions(id) ON DELETE CASCADE,
                confirmed_value_json TEXT, status TEXT NOT NULL, confirmed_by TEXT NOT NULL,
                source TEXT NOT NULL, created_at TEXT NOT NULL
            );

CREATE TABLE demo_field_extractions(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER REFERENCES demo_encounters(id) ON DELETE CASCADE,
                field_name TEXT NOT NULL, value_json TEXT, source TEXT NOT NULL,
                confidence_status TEXT NOT NULL, requires_confirmation INTEGER NOT NULL,
                model_run_id INTEGER REFERENCES demo_model_runs(id), created_at TEXT NOT NULL
            );

CREATE TABLE demo_institutions(
                id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL, country TEXT NOT NULL,
                source TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );

CREATE TABLE demo_login_events(
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, username_fingerprint TEXT,
                role_id TEXT, success INTEGER NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL
            );

CREATE TABLE demo_medications(id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE);

CREATE TABLE demo_model_runs(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER REFERENCES demo_encounters(id) ON DELETE CASCADE,
                provider TEXT NOT NULL, model_name TEXT NOT NULL, state TEXT NOT NULL,
                model_used INTEGER NOT NULL, fallback_reason TEXT, duration_seconds REAL,
                validated INTEGER NOT NULL, result_json TEXT, created_at TEXT NOT NULL
            );

CREATE TABLE demo_password_credentials(
                user_id TEXT PRIMARY KEY REFERENCES demo_users(id) ON DELETE CASCADE,
                username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, salt TEXT NOT NULL,
                algorithm TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );

CREATE TABLE demo_patient_access(
                user_id TEXT PRIMARY KEY REFERENCES demo_users(id) ON DELETE CASCADE,
                patient_id TEXT NOT NULL REFERENCES demo_patients(id) ON DELETE CASCADE,
                birth_date TEXT NOT NULL, created_at TEXT NOT NULL
            );

CREATE TABLE demo_patient_allergies(
                patient_id TEXT NOT NULL REFERENCES demo_patients(id) ON DELETE CASCADE,
                allergy_id TEXT NOT NULL REFERENCES demo_allergies(id), source TEXT NOT NULL,
                PRIMARY KEY(patient_id,allergy_id)
            );

CREATE TABLE demo_patient_medications(
                patient_id TEXT NOT NULL REFERENCES demo_patients(id) ON DELETE CASCADE,
                medication_id TEXT NOT NULL REFERENCES demo_medications(id), status TEXT NOT NULL,
                source TEXT NOT NULL, PRIMARY KEY(patient_id,medication_id)
            );

CREATE TABLE demo_patients(
                id TEXT PRIMARY KEY, synthetic_identifier TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL,
                age INTEGER NOT NULL, registered_sex TEXT NOT NULL, insurer TEXT NOT NULL,
                facility_id TEXT NOT NULL REFERENCES demo_facilities(id), source TEXT NOT NULL,
                status TEXT NOT NULL, created_by TEXT, updated_by TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );

CREATE TABLE demo_rag_retrievals(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER REFERENCES demo_encounters(id) ON DELETE CASCADE,
                source_id TEXT NOT NULL, chunk_id TEXT NOT NULL, score REAL NOT NULL,
                retrieval_reason TEXT NOT NULL, created_at TEXT NOT NULL
            );

CREATE TABLE demo_requested_considerations(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES demo_encounters(id) ON DELETE CASCADE,
                statement TEXT NOT NULL, source_ids_json TEXT NOT NULL, applicability TEXT NOT NULL,
                professional_decision TEXT NOT NULL, justification TEXT, created_by TEXT, created_at TEXT NOT NULL
            );

CREATE TABLE demo_roles(id TEXT PRIMARY KEY, label TEXT NOT NULL);

CREATE TABLE demo_sessions(
                id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES demo_users(id), role_id TEXT NOT NULL,
                facility_id TEXT, created_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, ended_at TEXT
            );

CREATE TABLE demo_transcriptions(
                id TEXT PRIMARY KEY, audio_segment_id TEXT REFERENCES demo_audio_segments(id) ON DELETE SET NULL,
                encounter_id INTEGER REFERENCES demo_encounters(id) ON DELETE CASCADE,
                provider TEXT NOT NULL, text TEXT NOT NULL, confidence REAL, confirmed INTEGER NOT NULL DEFAULT 0,
                edited_text TEXT, created_at TEXT NOT NULL, confirmed_at TEXT
            );

CREATE TABLE demo_triage_assessments(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES demo_encounters(id) ON DELETE CASCADE,
                proposed_level TEXT NOT NULL, confirmed_level TEXT, decision TEXT NOT NULL,
                justification TEXT, reevaluation_requested INTEGER NOT NULL DEFAULT 0,
                scale_name TEXT NOT NULL, source TEXT NOT NULL, created_by TEXT, created_at TEXT NOT NULL
            );

CREATE TABLE demo_user_roles(
                user_id TEXT NOT NULL REFERENCES demo_users(id) ON DELETE CASCADE,
                role_id TEXT NOT NULL REFERENCES demo_roles(id), PRIMARY KEY(user_id,role_id)
            );

CREATE TABLE demo_users(
                id TEXT PRIMARY KEY, display_name TEXT NOT NULL, demo_profile INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );

CREATE TABLE demo_vital_signs(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES demo_encounters(id) ON DELETE CASCADE,
                systolic INTEGER, diastolic INTEGER, heart_rate INTEGER, respiratory_rate INTEGER,
                temperature REAL, oxygen_saturation INTEGER, glucose INTEGER, consciousness_scale TEXT,
                weight REAL, height REAL, pain_score INTEGER, population TEXT NOT NULL,
                source TEXT NOT NULL, created_by TEXT, created_at TEXT NOT NULL
            );

CREATE TABLE demo_workflow_requirements(
                facility_id TEXT NOT NULL REFERENCES demo_facilities(id), population TEXT NOT NULL,
                stage TEXT NOT NULL, field_name TEXT NOT NULL, required INTEGER NOT NULL,
                version TEXT NOT NULL, updated_at TEXT NOT NULL,
                PRIMARY KEY(facility_id,population,stage,field_name)
            );

CREATE TABLE diagnoses(
                id INTEGER PRIMARY KEY AUTOINCREMENT, patient_dni TEXT NOT NULL REFERENCES patients(dni),
                encounter_id INTEGER REFERENCES encounters(id), description TEXT NOT NULL, code TEXT,
                recorded_by TEXT NOT NULL, recorded_at TEXT NOT NULL, status TEXT NOT NULL
            );

CREATE TABLE encounters(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_dni TEXT NOT NULL REFERENCES patients(dni),
                facility_id TEXT REFERENCES facilities(id), legacy_encounter_id INTEGER UNIQUE,
                status TEXT NOT NULL, chief_complaint TEXT NOT NULL, narrative TEXT NOT NULL,
                started_at TEXT NOT NULL, ended_at TEXT, created_by TEXT, updated_at TEXT NOT NULL
            );

CREATE TABLE facilities(
                id TEXT PRIMARY KEY, institution_id TEXT NOT NULL REFERENCES institutions(id),
                name TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );

CREATE TABLE field_confirmations(
                id INTEGER PRIMARY KEY AUTOINCREMENT, extraction_id INTEGER NOT NULL REFERENCES field_extractions(id) ON DELETE CASCADE,
                value_json TEXT, status TEXT NOT NULL, reason TEXT, confirmed_by TEXT NOT NULL, confirmed_at TEXT NOT NULL
            );

CREATE TABLE field_extractions(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER REFERENCES encounters(id),
                patient_dni TEXT NOT NULL REFERENCES patients(dni), field_name TEXT NOT NULL,
                value_json TEXT, source TEXT NOT NULL, confidence_status TEXT NOT NULL,
                requires_confirmation INTEGER NOT NULL, created_at TEXT NOT NULL
            );

CREATE TABLE imaging_results(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES encounters(id),
                study_name TEXT NOT NULL, result TEXT NOT NULL, recorded_at TEXT NOT NULL, status TEXT NOT NULL
            );

CREATE TABLE institutions(
                id TEXT PRIMARY KEY, name TEXT NOT NULL, institution_type TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );

CREATE TABLE laboratory_results(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES encounters(id),
                test_name TEXT NOT NULL, result TEXT NOT NULL, unit TEXT, reference_text TEXT,
                recorded_at TEXT NOT NULL, status TEXT NOT NULL
            );

CREATE TABLE medical_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_dni TEXT NOT NULL REFERENCES patients(dni) ON DELETE CASCADE,
                category TEXT NOT NULL,
                detail TEXT NOT NULL,
                event_date TEXT,
                is_demo INTEGER NOT NULL DEFAULT 1
            );

CREATE TABLE medications(
                id INTEGER PRIMARY KEY AUTOINCREMENT, patient_dni TEXT NOT NULL REFERENCES patients(dni) ON DELETE CASCADE,
                name TEXT NOT NULL, dose TEXT, frequency TEXT, status TEXT NOT NULL,
                source TEXT NOT NULL, confirmed_by TEXT, confirmed_at TEXT, created_at TEXT NOT NULL
            );

CREATE TABLE model_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consultation_id INTEGER NOT NULL REFERENCES consultations(id) ON DELETE CASCADE,
                model_name TEXT NOT NULL,
                model_used INTEGER NOT NULL,
                validated INTEGER NOT NULL,
                response_json TEXT NOT NULL,
                error_detail TEXT,
                created_at TEXT NOT NULL
            );

CREATE TABLE model_runs(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER REFERENCES encounters(id),
                stage TEXT NOT NULL, provider TEXT NOT NULL, model_name TEXT NOT NULL,
                model_used INTEGER NOT NULL, validated INTEGER NOT NULL, duration_seconds REAL,
                result_json TEXT, error_detail TEXT, created_at TEXT NOT NULL
            );

CREATE TABLE pain_assessments(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES encounters(id) ON DELETE CASCADE,
                present INTEGER, score INTEGER CHECK(score BETWEEN 0 AND 10), location TEXT,
                source TEXT NOT NULL, confirmed_by TEXT, created_at TEXT NOT NULL
            );

CREATE TABLE patient_identifiers(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_dni TEXT NOT NULL REFERENCES patients(dni) ON DELETE CASCADE,
                identifier_type TEXT NOT NULL,
                identifier_value TEXT NOT NULL UNIQUE,
                synthetic INTEGER NOT NULL CHECK(synthetic=1),
                created_at TEXT NOT NULL
            );

CREATE TABLE patients (
                dni TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER NOT NULL CHECK(age >= 0),
                sex TEXT NOT NULL,
                is_demo INTEGER NOT NULL DEFAULT 1
            , given_names TEXT, family_names TEXT, birth_date TEXT, phone TEXT, email TEXT, address TEXT, emergency_contact TEXT, insurance_type TEXT, facility_id TEXT, consent_at TEXT, created_at TEXT, updated_at TEXT);

CREATE TABLE prescriptions(
                id INTEGER PRIMARY KEY AUTOINCREMENT, patient_dni TEXT NOT NULL REFERENCES patients(dni),
                encounter_id INTEGER REFERENCES encounters(id), medication_name TEXT NOT NULL,
                instructions TEXT, prescribed_by TEXT NOT NULL, prescribed_at TEXT NOT NULL, status TEXT NOT NULL
            );

CREATE TABLE procedures(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES encounters(id),
                description TEXT NOT NULL, recorded_by TEXT NOT NULL, recorded_at TEXT NOT NULL
            );

CREATE TABLE rag_chunks(
                chunk_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES rag_documents(source_id),
                title TEXT NOT NULL, institution TEXT NOT NULL, year INTEGER NOT NULL,
                population TEXT NOT NULL, section TEXT NOT NULL, page TEXT NOT NULL,
                url TEXT NOT NULL, license TEXT NOT NULL, text TEXT NOT NULL,
                applicability TEXT NOT NULL, limitations TEXT NOT NULL,
                content_hash TEXT NOT NULL UNIQUE, ingested_at TEXT NOT NULL
            );

CREATE VIRTUAL TABLE rag_chunks_fts USING fts5(chunk_id UNINDEXED, text, title, section);

CREATE TABLE 'rag_chunks_fts_config'(k PRIMARY KEY, v) WITHOUT ROWID;

CREATE TABLE 'rag_chunks_fts_content'(id INTEGER PRIMARY KEY, c0, c1, c2, c3);

CREATE TABLE 'rag_chunks_fts_data'(id INTEGER PRIMARY KEY, block BLOB);

CREATE TABLE 'rag_chunks_fts_docsize'(id INTEGER PRIMARY KEY, sz BLOB);

CREATE TABLE 'rag_chunks_fts_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID;

CREATE TABLE rag_documents(
                source_id TEXT PRIMARY KEY, title TEXT NOT NULL, institution TEXT NOT NULL,
                country TEXT NOT NULL, year INTEGER NOT NULL, document_type TEXT NOT NULL,
                population TEXT NOT NULL, clinical_scope TEXT NOT NULL, url TEXT NOT NULL,
                license TEXT NOT NULL, access_date TEXT NOT NULL, status TEXT NOT NULL,
                approved_for_demo INTEGER NOT NULL CHECK(approved_for_demo IN (0,1)), notes TEXT NOT NULL
            );

CREATE TABLE rag_retrievals(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER REFERENCES encounters(id),
                source_id TEXT NOT NULL, institution TEXT NOT NULL, year TEXT NOT NULL, population TEXT NOT NULL,
                url TEXT NOT NULL, fragment TEXT NOT NULL, limitations TEXT NOT NULL,
                score REAL NOT NULL, created_at TEXT NOT NULL
            );

CREATE TABLE roles(
                id TEXT PRIMARY KEY, label TEXT NOT NULL, created_at TEXT NOT NULL
            );

CREATE TABLE sessions(
                id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
                role_id TEXT NOT NULL REFERENCES roles(id), facility_id TEXT REFERENCES facilities(id),
                started_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, ended_at TEXT
            );

CREATE TABLE symptoms(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES encounters(id) ON DELETE CASCADE,
                name TEXT NOT NULL, onset TEXT, duration TEXT, evolution TEXT, location TEXT,
                source TEXT NOT NULL, confirmed_by TEXT, created_at TEXT NOT NULL
            );

CREATE TABLE triage_assessments(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES encounters(id),
                proposed_level INTEGER CHECK(proposed_level BETWEEN 1 AND 5),
                confirmed_level INTEGER CHECK(confirmed_level BETWEEN 1 AND 5),
                scale_name TEXT NOT NULL, decision TEXT NOT NULL, justification TEXT,
                reevaluation_requested INTEGER NOT NULL DEFAULT 0,
                recorded_by TEXT NOT NULL, recorded_at TEXT NOT NULL
            );

CREATE TABLE user_roles(
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role_id TEXT NOT NULL REFERENCES roles(id),
                facility_id TEXT REFERENCES facilities(id),
                PRIMARY KEY(user_id,role_id,facility_id)
            );

CREATE TABLE users(
                id TEXT PRIMARY KEY, username TEXT UNIQUE, display_name TEXT NOT NULL,
                password_hash TEXT, active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );

CREATE TABLE vital_signs(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES encounters(id) ON DELETE CASCADE,
                systolic INTEGER, diastolic INTEGER, heart_rate INTEGER, respiratory_rate INTEGER,
                temperature REAL, oxygen_saturation INTEGER, glucose INTEGER, consciousness TEXT,
                weight REAL, height REAL, pain_score INTEGER CHECK(pain_score BETWEEN 0 AND 10),
                recorded_by TEXT NOT NULL, recorded_at TEXT NOT NULL
            );
