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
    v_found BOOLEAN := FALSE;
BEGIN
    UPDATE payments
    SET status = 'captured', razorpay_payment_id = p_payment_id
    WHERE razorpay_order_id = p_order_id AND status <> 'captured';
    GET DIAGNOSTICS v_found = ROW_COUNT;
    RETURN v_found;
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

-- =============================================================================
-- SEED DATA — 5 specialties, doctors, symptom map, and bookable slots
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