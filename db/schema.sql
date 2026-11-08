CREATE TABLE IF NOT EXISTS households (
    id              SERIAL PRIMARY KEY,
    device_id       TEXT UNIQUE NOT NULL,
    address         TEXT NOT NULL,
    zip             TEXT,
    lat             DOUBLE PRECISION,
    lng             DOUBLE PRECISION,
    lives_alone     BOOLEAN DEFAULT FALSE,
    medical_device  BOOLEAN DEFAULT FALSE,
    mobility_limits BOOLEAN DEFAULT FALSE,
    photo_consent   BOOLEAN DEFAULT FALSE,
    ai_reason       TEXT,
    simulated       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS readings (
    time        TIMESTAMPTZ NOT NULL,
    device_id   TEXT NOT NULL,
    power_on    BOOLEAN,
    sensors     JSONB,
    counter     BIGINT NOT NULL,
    hash        TEXT,
    prev_hash   TEXT,
    PRIMARY KEY (device_id, time)
);

SELECT create_hypertable('readings', by_range('time'), if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS call_requests (
    id           SERIAL PRIMARY KEY,
    household_id INT REFERENCES households(id),
    requested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS contact_status (
    household_id INT PRIMARY KEY REFERENCES households(id),
    status       TEXT NOT NULL DEFAULT 'not_contacted'
                 CHECK (status IN ('not_contacted', 'contacted', 'needs_follow_up', 'resolved')),
    updated_by   TEXT,
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS claim_drafts (
    id           SERIAL PRIMARY KEY,
    household_id INT REFERENCES households(id),
    draft        JSONB NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending_review'
                 CHECK (status IN ('pending_review', 'approved', 'rejected')),
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at  TIMESTAMPTZ,
    reviewed_by  TEXT
);

CREATE TABLE IF NOT EXISTS rejected_messages (
    id          SERIAL PRIMARY KEY,
    device_id   TEXT,
    reason      TEXT,
    received_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_briefs (
    id         SERIAL PRIMARY KEY,
    brief      TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agents (
    id            SERIAL PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL,
    name          TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS claim_photos (
    id              SERIAL PRIMARY KEY,
    household_id    INT REFERENCES households(id),
    device_id       TEXT NOT NULL,
    taken_at        TIMESTAMPTZ NOT NULL,
    sha256          TEXT UNIQUE NOT NULL,
    content_type    TEXT NOT NULL DEFAULT 'image/jpeg',
    image           BYTEA NOT NULL,
    analysis        JSONB,
    analysis_status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (analysis_status IN ('pending', 'done', 'failed')),
    uploaded_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS claim_photos_household_idx ON claim_photos (household_id, taken_at);
