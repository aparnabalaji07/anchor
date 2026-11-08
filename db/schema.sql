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
    simulated       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS readings (
    time        TIMESTAMPTZ NOT NULL,
    device_id   TEXT NOT NULL,
    power_on    BOOLEAN,
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
    reviewed_at  TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS rejected_messages (
    id          SERIAL PRIMARY KEY,
    device_id   TEXT,
    reason      TEXT,
    received_at TIMESTAMPTZ DEFAULT NOW()
);