-- =============================================================================
-- Healthcare AI Voice Agent — PostgreSQL schema
-- =============================================================================
-- Run with:  psql "$DATABASE_URL" -f backend/schema.sql
--
-- All application data access goes through the stored procedures defined here.
-- Repositories never inline SQL, so this file is the single source of truth
-- for the data model.
--
-- Requires:  CREATE EXTENSION pgcrypto;  (for bcrypt password hashing)
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- =============================================================================
-- TABLES
-- =============================================================================

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS patients (
    id                    SERIAL PRIMARY KEY,
    user_id               INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    name                  TEXT NOT NULL,
    date_of_birth         DATE,
    gender                TEXT,
    contact_number        TEXT,
    medical_record_number TEXT UNIQUE,
    blood_group           TEXT,
    marital_status        TEXT
);

CREATE TABLE IF NOT EXISTS medical_history (
    patient_id            INTEGER PRIMARY KEY REFERENCES patients(id) ON DELETE CASCADE,
    past_diagnoses        TEXT,
    surgeries             TEXT,
    hospital_admissions   TEXT,
    immunization_records  TEXT,
    family_medical_history TEXT,
    lifestyle_factors     TEXT
);

CREATE TABLE IF NOT EXISTS specialties (
    id   SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

-- Maps a normalized clinical symptom term to the specialties that treat it.
-- sp_get_specialists() joins against this table.
CREATE TABLE IF NOT EXISTS symptom_specialty_map (
    symptom   TEXT NOT NULL,
    specialty TEXT NOT NULL REFERENCES specialties(name) ON DELETE CASCADE,
    PRIMARY KEY (symptom, specialty)
);

CREATE TABLE IF NOT EXISTS doctors (
    id            SERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    specialization TEXT NOT NULL REFERENCES specialties(name),
    rating        NUMERIC(2,1) NOT NULL DEFAULT 4.5,
    fees          INTEGER NOT NULL DEFAULT 0,
    hospital      TEXT
);

-- Makes the seed idempotent: re-running schema.sql must not duplicate doctors.
CREATE UNIQUE INDEX IF NOT EXISTS uq_doctor_identity
    ON doctors (name, specialization, hospital);

CREATE TABLE IF NOT EXISTS appointment_slots (
    id         SERIAL PRIMARY KEY,
    doctor_id  INTEGER NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    slot_date  DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time   TIME NOT NULL,
    is_booked  BOOLEAN NOT NULL DEFAULT FALSE
);

-- Guards against two patients booking the same slot concurrently.
CREATE UNIQUE INDEX IF NOT EXISTS uq_slot_unique
    ON appointment_slots (doctor_id, slot_date, start_time);

CREATE INDEX IF NOT EXISTS ix_slots_lookup
    ON appointment_slots (doctor_id, slot_date)
    WHERE is_booked = FALSE;

CREATE TABLE IF NOT EXISTS payments (
    id           SERIAL PRIMARY KEY,
    razorpay_order_id   TEXT UNIQUE,
    razorpay_payment_id TEXT,
    amount       INTEGER NOT NULL,
    currency     TEXT NOT NULL DEFAULT 'INR',
    status       TEXT NOT NULL DEFAULT 'created',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS appointments (
    id          SERIAL PRIMARY KEY,
    patient_id  INTEGER NOT NULL REFERENCES patients(id),
    doctor_id   INTEGER NOT NULL REFERENCES doctors(id),
    slot_id     INTEGER NOT NULL REFERENCES appointment_slots(id),
    reason      TEXT,
    payment_id  INTEGER REFERENCES payments(id),
    status      TEXT NOT NULL DEFAULT 'confirmed',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One live appointment per slot. The application already guards this with a
-- conditional UPDATE; this makes double-booking impossible even if some other
-- code path writes directly.
CREATE UNIQUE INDEX IF NOT EXISTS uq_appointment_slot
    ON appointments (slot_id);


-- =============================================================================
-- CONVERSATIONS AND TRIAGE AUDIT
-- =============================================================================
-- Conversation state lives here rather than in the browser. The client used to
-- own the transcript in a React ref, which meant a reload lost the history and
-- the server had to trust whatever history the caller sent.

CREATE TABLE IF NOT EXISTS conversations (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_conversations_user
    ON conversations (user_id, started_at DESC);

CREATE TABLE IF NOT EXISTS messages (
    id              BIGSERIAL PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('patient', 'agent')),
    content         TEXT NOT NULL,
    -- Which graph node produced an agent message. NULL for patient messages.
    node            TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_messages_conversation
    ON messages (conversation_id, id);

-- One row per triage run. This is the compliance artefact: it answers
-- "why was this patient escalated?" without archaeology. It also records the
-- model and prompt version, so a prompt edit cannot silently change clinical
-- behaviour with no trace.
CREATE TABLE IF NOT EXISTS triage_decisions (
    id                  BIGSERIAL PRIMARY KEY,
    conversation_id     UUID REFERENCES conversations(id) ON DELETE SET NULL,
    symptom_text        TEXT,
    urgency             TEXT,
    is_emergency        BOOLEAN NOT NULL DEFAULT FALSE,
    -- Which deterministic rules fired, by name, not just a boolean.
    triggered_red_flags TEXT[],
    escalated_by        TEXT NOT NULL DEFAULT 'rules'
                        CHECK (escalated_by IN ('rules', 'llm', 'none')),
    provider            TEXT,
    model               TEXT,
    prompt_version      TEXT,
    latency_ms          INTEGER,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_decisions_conversation
    ON triage_decisions (conversation_id, created_at DESC);

-- Short-lived reservation while a patient completes payment, so a slot is not
-- advertised to two people while both are typing card details.
CREATE TABLE IF NOT EXISTS slot_holds (
    slot_id    INTEGER PRIMARY KEY REFERENCES appointment_slots(id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL
);

-- Makes a retried booking request safe: the same key returns the original
-- appointment instead of creating a second one.
CREATE TABLE IF NOT EXISTS idempotency_keys (
    key            TEXT PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    appointment_id INTEGER REFERENCES appointments(id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- STORED PROCEDURES
-- =============================================================================
-- Dropped first so this file is safely re-runnable (CREATE OR REPLACE cannot
-- change a function's return type in place).
DO $$
DECLARE r RECORD;
BEGIN
    FOR r IN (
        SELECT p.oid::regprocedure AS sig
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public' AND p.proname LIKE 'sp\_%'
    )
    LOOP
        EXECUTE 'DROP FUNCTION ' || r.sig || ' CASCADE';
    END LOOP;
END $$;

-- Auth: verify credentials. Returns the user id, or no row if invalid.
-- Passwords are stored as bcrypt hashes; plaintext is never persisted.
CREATE OR REPLACE FUNCTION sp_login_user(p_email TEXT, p_password TEXT)
RETURNS TABLE (user_id INTEGER) AS $$
BEGIN
    RETURN QUERY
    SELECT u.id
    FROM users u
    WHERE u.email = lower(trim(p_email))
      AND u.password_hash = crypt(p_password, u.password_hash);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Auth: create a user and their patient record in one transaction.
CREATE OR REPLACE FUNCTION sp_register_user(p_name TEXT, p_email TEXT, p_password TEXT)
RETURNS TABLE (user_id INTEGER) AS $$
DECLARE
    v_user_id    INTEGER;
    v_patient_id INTEGER;
BEGIN
    INSERT INTO users (email, password_hash)
    VALUES (lower(trim(p_email)), crypt(p_password, gen_salt('bf')))
    RETURNING id INTO v_user_id;

    INSERT INTO patients (user_id, name, medical_record_number)
    VALUES (v_user_id, trim(p_name), 'MRN-' || lpad(v_user_id::TEXT, 6, '0'))
    RETURNING id INTO v_patient_id;

    INSERT INTO medical_history (patient_id) VALUES (v_patient_id)
    ON CONFLICT DO NOTHING;

    RETURN QUERY SELECT v_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION sp_get_patient_id(p_user_id INTEGER)
RETURNS TABLE (patient_id INTEGER) AS $$
    SELECT p.id FROM patients p WHERE p.user_id = p_user_id;
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION sp_get_patient_details(p_user_id INTEGER)
RETURNS TABLE (
    name                  TEXT,
    date_of_birth         DATE,
    gender                TEXT,
    contact_number        TEXT,
    medical_record_number TEXT,
    blood_group           TEXT,
    marital_status        TEXT,
    patient_id            INTEGER
) AS $$
    SELECT p.name, p.date_of_birth, p.gender, p.contact_number,
           p.medical_record_number, p.blood_group, p.marital_status, p.id
    FROM patients p
    WHERE p.user_id = p_user_id;
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION sp_get_medical_history(p_patient_id INTEGER)
RETURNS TABLE (
    past_diagnoses         TEXT,
    surgeries              TEXT,
    hospital_admissions    TEXT,
    immunization_records   TEXT,
    family_medical_history TEXT,
    lifestyle_factors      TEXT
) AS $$
    SELECT past_diagnoses, surgeries, hospital_admissions,
           immunization_records, family_medical_history, lifestyle_factors
    FROM medical_history
    WHERE patient_id = p_patient_id;
$$ LANGUAGE sql;

-- Triage: map a set of normalized symptoms to the specialties that treat them.
-- Set-based on purpose — one round trip for the whole symptom array.
CREATE OR REPLACE FUNCTION sp_get_specialists(p_symptoms TEXT[])
RETURNS TABLE (specialty TEXT) AS $$
    SELECT DISTINCT m.specialty
    FROM unnest(p_symptoms) AS s(symptom)
    JOIN symptom_specialty_map m
      ON lower(m.symptom) = lower(s.symptom)
    ORDER BY 1;
$$ LANGUAGE sql;

-- Discovery: for each doctor in the given specialties, return the doctor plus
-- their earliest unbooked slot. One row per doctor.
CREATE OR REPLACE FUNCTION sp_get_doctors_by_specialists(p_specialists TEXT[])
RETURNS TABLE (
    doctor_id            INTEGER,
    name                 TEXT,
    specialization       TEXT,
    rating               NUMERIC,
    fees                 INTEGER,
    hospital             TEXT,
    next_available_date  DATE,
    start_time           TIME,
    end_time             TIME,
    slot_id              INTEGER
) AS $$
    SELECT d.id, d.name, d.specialization, d.rating, d.fees, d.hospital,
           s.slot_date, s.start_time, s.end_time, s.id
    FROM doctors d
    JOIN LATERAL (
        SELECT a.id, a.slot_date, a.start_time, a.end_time
        FROM appointment_slots a
        WHERE a.doctor_id = d.id
          AND a.is_booked = FALSE
          AND a.slot_date >= CURRENT_DATE
        ORDER BY a.slot_date, a.start_time
        LIMIT 1
    ) s ON TRUE
    WHERE d.specialization = ANY (p_specialists)
    ORDER BY d.rating DESC, s.slot_date, s.start_time;
$$ LANGUAGE sql;

-- Booking: create an appointment and mark the slot booked, atomically.
-- Raises if the slot was already taken, so the caller gets a clean error
-- rather than a double booking.
CREATE OR REPLACE FUNCTION sp_create_appointment(
    p_patient_id INTEGER,
    p_doctor_id  INTEGER,
    p_slot_id    INTEGER,
    p_reason     TEXT,
    p_payment_id TEXT DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    v_appointment_id INTEGER;
BEGIN
    UPDATE appointment_slots
    SET is_booked = TRUE
    WHERE id = p_slot_id
      AND is_booked = FALSE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Slot % is no longer available', p_slot_id;
    END IF;

INSERT INTO appointments (patient_id, doctor_id, slot_id, reason, payment_id)
    SELECT p.id, p_doctor_id, s.id, p_reason,
           CASE WHEN p_payment_id IS NULL THEN NULL
                ELSE (SELECT id FROM payments WHERE razorpay_payment_id = p_payment_id)
           END
    FROM patients p
    JOIN appointment_slots s ON s.id = p_slot_id AND s.doctor_id = p_doctor_id
    WHERE p.id = p_patient_id
    RETURNING id INTO v_appointment_id;

    IF v_appointment_id IS NULL THEN
        RAISE EXCEPTION 'Invalid patient/doctor/slot combination';
    END IF;

    RETURN v_appointment_id;
END;
$$ LANGUAGE plpgsql;


-- Payments: record an order when it is created, so verification can be
-- matched against an amount the client cannot choose.
CREATE OR REPLACE FUNCTION sp_record_payment_order(
    p_order_id TEXT,
    p_amount   INTEGER,
    p_currency TEXT DEFAULT 'INR'
)
RETURNS INTEGER AS $$
DECLARE
    v_id INTEGER;
BEGIN
    INSERT INTO payments (razorpay_order_id, amount, currency, status)
    VALUES (p_order_id, p_amount, p_currency, 'created')
    ON CONFLICT (razorpay_order_id) DO UPDATE SET amount = EXCLUDED.amount
    RETURNING id INTO v_id;
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Mark an order captured. Returns FALSE when the order is unknown, which is
-- how a verified signature for an order we never created gets rejected.
CREATE OR REPLACE FUNCTION sp_capture_payment(
    p_order_id   TEXT,
    p_payment_id TEXT
)
RETURNS BOOLEAN AS $$
DECLARE
    v_rows INTEGER := 0;
BEGIN
    UPDATE payments
    SET status = 'captured', razorpay_payment_id = p_payment_id
    WHERE razorpay_order_id = p_order_id AND status <> 'captured';
    GET DIAGNOSTICS v_rows = ROW_COUNT;
    RETURN v_rows > 0;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION sp_get_payment(p_payment_id TEXT)
RETURNS TABLE (
    payment_id TEXT,
    amount     INTEGER,
    status     TEXT
) AS $$
    SELECT p.razorpay_payment_id, p.amount, p.status
    FROM payments p
    WHERE p.razorpay_payment_id = p_payment_id;
$$ LANGUAGE sql;

-- ─── Conversations ─────────────────────────────────────────────────────────
-- Create a conversation, or return the caller's most recent open one so a
-- reload resumes rather than starting over.
CREATE OR REPLACE FUNCTION sp_get_or_create_conversation(p_user_id INTEGER)
RETURNS UUID AS $$
DECLARE
    v_id UUID;
BEGIN
    SELECT id INTO v_id
    FROM conversations
    WHERE user_id = p_user_id AND closed_at IS NULL
    ORDER BY started_at DESC
    LIMIT 1;

    IF v_id IS NULL THEN
        INSERT INTO conversations (user_id) VALUES (p_user_id) RETURNING id INTO v_id;
    END IF;

    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION sp_add_message(
    p_conversation_id UUID,
    p_role            TEXT,
    p_content         TEXT,
    p_node            TEXT DEFAULT NULL
)
RETURNS BIGINT AS $$
    INSERT INTO messages (conversation_id, role, content, node)
    VALUES (p_conversation_id, p_role, p_content, p_node)
    RETURNING id;
$$ LANGUAGE sql;

-- Oldest-first, capped: the model only ever needs the recent window, and an
-- unbounded transcript is both a cost and an injection surface.
CREATE OR REPLACE FUNCTION sp_get_conversation_history(
    p_conversation_id UUID,
    p_limit            INTEGER DEFAULT 20
)
RETURNS TABLE (
    message_id BIGINT,
    role       TEXT,
    content    TEXT,
    node       TEXT,
    created_at TIMESTAMPTZ
) AS $$
    SELECT id, role, content, node, created_at
    FROM (
        SELECT m.id, m.role, m.content, m.node, m.created_at
        FROM messages m
        WHERE m.conversation_id = p_conversation_id
        ORDER BY m.id DESC
        LIMIT p_limit
    ) recent
    ORDER BY recent.id ASC;
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION sp_close_conversation(p_conversation_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_rows INTEGER := 0;
BEGIN
    UPDATE conversations SET closed_at = now()
    WHERE id = p_conversation_id AND closed_at IS NULL;
    GET DIAGNOSTICS v_rows = ROW_COUNT;
    RETURN v_rows > 0;
END;
$$ LANGUAGE plpgsql;

-- ─── Triage audit ──────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION sp_record_triage_decision(
    p_conversation_id UUID,
    p_symptom_text    TEXT,
    p_urgency         TEXT,
    p_is_emergency    BOOLEAN,
    p_red_flags       TEXT[],
    p_escalated_by    TEXT,
    p_provider        TEXT,
    p_model           TEXT,
    p_prompt_version  TEXT
)
RETURNS BIGINT AS $$
    INSERT INTO triage_decisions (
        conversation_id, symptom_text, urgency, is_emergency,
        triggered_red_flags, escalated_by, provider, model, prompt_version
    )
    VALUES (
        p_conversation_id, p_symptom_text, p_urgency, p_is_emergency,
        p_red_flags, p_escalated_by, p_provider, p_model, p_prompt_version
    )
    RETURNING id;
$$ LANGUAGE sql;

-- ─── Slot holds ────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION sp_hold_slot(
    p_slot_id    INTEGER,
    p_user_id    INTEGER,
    p_ttl_seconds INTEGER DEFAULT 600
)
RETURNS BOOLEAN AS $$
DECLARE
    v_rows INTEGER := 0;
BEGIN
    -- Release any hold that has already expired before checking availability.
    DELETE FROM slot_holds WHERE expires_at < now();

    UPDATE slot_holds
    SET user_id = p_user_id, expires_at = now() + make_interval(secs => p_ttl_seconds)
    WHERE slot_id = p_slot_id;

    IF FOUND THEN
        RETURN FALSE;               -- already held by someone, possibly us
    END IF;

    INSERT INTO slot_holds (slot_id, user_id, expires_at)
    SELECT p_slot_id, p_user_id, now() + make_interval(secs => p_ttl_seconds)
    WHERE EXISTS (
        SELECT 1 FROM appointment_slots
        WHERE id = p_slot_id AND is_booked = FALSE
    )
    ON CONFLICT (slot_id) DO NOTHING;

    GET DIAGNOSTICS v_rows = ROW_COUNT;
    RETURN v_rows > 0;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION sp_release_expired_holds()
RETURNS INTEGER AS $$
    WITH released AS (
        DELETE FROM slot_holds WHERE expires_at < now() RETURNING 1
    )
    SELECT count(*)::INTEGER FROM released;
$$ LANGUAGE sql;

-- ─── Idempotency ───────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION sp_get_idempotent_appointment(p_key TEXT)
RETURNS INTEGER AS $$
    SELECT appointment_id FROM idempotency_keys WHERE key = p_key;
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION sp_record_idempotency_key(
    p_key            TEXT,
    p_user_id        INTEGER,
    p_appointment_id INTEGER
)
RETURNS VOID AS $$
    INSERT INTO idempotency_keys (key, user_id, appointment_id)
    VALUES (p_key, p_user_id, p_appointment_id)
    ON CONFLICT (key) DO NOTHING;
$$ LANGUAGE sql;

-- =============================================================================
-- SEED DATA — 7 specialties, doctors, symptom map, and bookable slots
-- =============================================================================
-- Safe to re-run: every insert is idempotent.

INSERT INTO specialties (name) VALUES
    ('General Medicine'),
    ('Cardiology'),
    ('Neurology'),
    ('Orthopaedics'),
    ('Dermatology'),
    ('Gastroenterology'),
    ('ENT')
ON CONFLICT (name) DO NOTHING;

-- Symptom -> specialty mapping.
--
-- Both colloquial and CLINICAL terms are listed deliberately. The conversational
-- pipeline emits clinical terms ("rhinorrhea", "gastritis") while patients speak
-- colloquial ones ("runny nose", "tummy ache"), so a map keyed on only one
-- vocabulary returns nothing for half of all traffic.
INSERT INTO symptom_specialty_map (symptom, specialty) VALUES
    -- General / undifferentiated presentations
    ('fever',                  'General Medicine'),
    ('low-grade fever',       'General Medicine'),
    ('high fever',            'General Medicine'),
    ('fatigue',               'General Medicine'),
    ('body ache',             'General Medicine'),
    ('general body ache',     'General Medicine'),
    ('malaise',               'General Medicine'),
    ('chills',                'General Medicine'),
    ('weakness',              'General Medicine'),
    ('dehydration',           'General Medicine'),
    ('flu',                   'General Medicine'),
    ('influenza',             'General Medicine'),
    ('viral infection',       'General Medicine'),
    ('viral upper respiratory infection', 'General Medicine'),
    ('common cold',           'General Medicine'),
    ('cough',                 'General Medicine'),
    ('dry cough',             'General Medicine'),
    ('congestion',            'General Medicine'),
    ('nasal congestion',      'General Medicine'),
    ('runny nose',            'General Medicine'),
    ('rhinorrhea',            'General Medicine'),
    ('sore throat',           'General Medicine'),
    ('pharyngitis',           'ENT'),
    ('tonsillitis',           'ENT'),
    ('ear pain',              'ENT'),
    ('hearing loss',          'ENT'),
    ('sinus pain',            'ENT'),
    ('sinusitis',             'ENT'),
    ('nosebleed',             'ENT'),

    -- Cardiac
    ('chest pain',            'Cardiology'),
    ('chest discomfort',      'Cardiology'),
    ('chest tightness',       'Cardiology'),
    ('palpitations',          'Cardiology'),
    ('irregular heartbeat',   'Cardiology'),
    ('shortness of breath',   'Cardiology'),
    ('high blood pressure',   'Cardiology'),
    ('hypertension',          'Cardiology'),
    ('angina',                'Cardiology'),
    ('swelling in legs',      'Cardiology'),
    ('murmur',                'Cardiology'),

    -- Neurological
    ('headache',              'Neurology'),
    ('migraine',              'Neurology'),
    ('migraines',             'Neurology'),
    ('dizziness',             'Neurology'),
    ('vertigo',               'Neurology'),
    ('numbness',              'Neurology'),
    ('tingling',              'Neurology'),
    ('tremor',                'Neurology'),
    ('tremors',               'Neurology'),
    ('seizure',               'Neurology'),
    ('loss of consciousness', 'Neurology'),
    ('fainting',              'Neurology'),
    ('memory loss',           'Neurology'),
    ('confusion',             'Neurology'),
    ('neuropathy',            'Neurology'),

    -- Musculoskeletal
    ('joint pain',            'Orthopaedics'),
    ('back pain',             'Orthopaedics'),
    ('lower back pain',       'Orthopaedics'),
    ('lower back ache',       'Orthopaedics'),
    ('knee pain',             'Orthopaedics'),
    ('shoulder pain',         'Orthopaedics'),
    ('hip pain',              'Orthopaedics'),
    ('neck pain',             'Orthopaedics'),
    ('fracture',              'Orthopaedics'),
    ('sprain',                'Orthopaedics'),
    ('osteoarthritis',        'Orthopaedics'),
    ('muscle strain',         'Orthopaedics'),
    ('swollen joint',         'Orthopaedics'),

    -- Skin
    ('rash',                  'Dermatology'),
    ('skin rash',             'Dermatology'),
    ('itching',               'Dermatology'),
    ('skin lesion',           'Dermatology'),
    ('acne',                  'Dermatology'),
    ('eczema',                'Dermatology'),
    ('hives',                 'Dermatology'),
    ('hair loss',             'Dermatology'),
    ('skin discoloration',    'Dermatology'),
    ('wart',                  'Dermatology'),

    -- Gastrointestinal
    ('abdominal pain',        'Gastroenterology'),
    ('stomach pain',          'Gastroenterology'),
    ('tummy ache',            'Gastroenterology'),
    ('stomach ache',          'Gastroenterology'),
    ('nausea',                'Gastroenterology'),
    ('vomiting',              'Gastroenterology'),
    ('diarrhoea',             'Gastroenterology'),
    ('diarrhea',              'Gastroenterology'),
    ('constipation',          'Gastroenterology'),
    ('bloating',              'Gastroenterology'),
    ('acid reflux',           'Gastroenterology'),
    ('heartburn',             'Gastroenterology'),
    ('gastritis',             'Gastroenterology'),
    ('abdominal bloating',    'Gastroenterology'),
    ('loss of appetite',      'Gastroenterology')
ON CONFLICT DO NOTHING;

INSERT INTO doctors (name, specialization, rating, fees, hospital) VALUES
    ('Dr. Asha Menon',      'General Medicine', 4.6, 400, 'Sunrise Health Centre'),
    ('Dr. Varun Pillai',    'General Medicine', 4.5, 500, 'Manipal Hospital'),
    ('Dr. Nisha Batra',     'General Medicine', 4.7, 450, 'Fortis Multi Speciality'),
    ('Dr. Ananya Rao',     'Cardiology',      4.8, 800,  'Apollo Hospitals'),
    ('Dr. Vikram Desai',   'Cardiology',      4.5, 600,  'Fortis Heart Centre'),
    ('Dr. Meera Iyer',      'Cardiology',      4.9, 1200, 'Narayana Health'),
    ('Dr. Rohan Mehta',    'Neurology',       4.7, 900,  'Manipal Hospital'),
    ('Dr. Fatima Sheikh',  'Neurology',       4.6, 700,  'Sanjeevani Neuro Centre'),
    ('Dr. Suresh Kumar',   'Neurology',       4.4, 650,  'Apollo Hospitals'),
    ('Dr. Priya Nair',     'Orthopaedics',    4.8, 850,  'Fortis Bone & Joint'),
    ('Dr. Arjun Malhotra', 'Orthopaedics',    4.5, 600,  'Sunrise Ortho Institute'),
    ('Dr. Kavya Reddy',    'Orthopaedics',    4.7, 750,  'Manipal Hospital'),
    ('Dr. Neha Gupta',     'Dermatology',     4.9, 950,  'Apollo Skin Centre'),
    ('Dr. Sameer Joshi',   'Dermatology',     4.5, 700,  'DermaCare Clinic'),
    ('Dr. Riya Chatterjee','Dermatology',     4.6, 800,  'Fortis Multi Speciality'),
    ('Dr. Arjun Menon',    'Gastroenterology',4.8, 900,  'Manipal Gastro Institute'),
    ('Dr. Sneha Patil',    'Gastroenterology',4.6, 700,  'Apollo Hospitals'),
    ('Dr. Rahul Verma',    'Gastroenterology',4.4, 550,  'Sunrise Health Centre'),
    ('Dr. Leela Prasad',   'ENT',             4.6, 650,  'Apollo ENT Centre'),
    ('Dr. Girish Bhat',    'ENT',             4.4, 550,  'Sunrise Health Centre')
ON CONFLICT (name, specialization, hospital) DO NOTHING;

-- Slots for the next 14 days, 10:00 / 12:00 / 15:00 / 17:00 per doctor.
INSERT INTO appointment_slots (doctor_id, slot_date, start_time, end_time)
SELECT d.id,
       CURRENT_DATE + g.offset_day,
       s.start_time,
       s.start_time + INTERVAL '30 minutes'
FROM doctors d
CROSS JOIN generate_series(0, 13) AS g(offset_day)
CROSS JOIN (VALUES ('10:00'::TIME), ('12:00'::TIME), ('15:00'::TIME), ('17:00'::TIME))
     AS s(start_time)
ON CONFLICT DO NOTHING;