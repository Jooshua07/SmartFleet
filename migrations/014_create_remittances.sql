BEGIN;

-- =========================================================
-- 1. CASHING SCHEDULE
-- Defines the days on which cashing would normally occur.
-- This is for scheduling/reminders only.
-- It does NOT restrict when cashing can actually be recorded.
-- =========================================================

CREATE TABLE cashing_schedules (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    day_of_week INTEGER NOT NULL,

    active BOOLEAN NOT NULL DEFAULT TRUE,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT cashing_schedules_day_check
        CHECK (day_of_week BETWEEN 1 AND 7),

    CONSTRAINT cashing_schedules_day_unique
        UNIQUE (day_of_week)
);


-- =========================================================
-- 2. COLLECTION EVENT
-- Represents money actually received by the owner on a
-- particular cashing occasion.
-- =========================================================

CREATE TABLE remittance_collections (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    collection_date DATE NOT NULL,

    financial_account_id INTEGER NOT NULL,

    total_amount NUMERIC(12,2) NOT NULL,

    financial_transaction_id INTEGER,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT remittance_collections_account_fk
        FOREIGN KEY (financial_account_id)
        REFERENCES financial_accounts(id),

    CONSTRAINT remittance_collections_transaction_fk
        FOREIGN KEY (financial_transaction_id)
        REFERENCES financial_transactions(id),

    CONSTRAINT remittance_collections_amount_check
        CHECK (total_amount >= 0)
);


-- =========================================================
-- 3. BUS CASHING
-- One record per bus included in a cashing collection.
-- We do NOT track actual daily bus revenue.
-- =========================================================

CREATE TABLE remittances (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    collection_id INTEGER NOT NULL,
    bus_id INTEGER NOT NULL,

    normal_days INTEGER NOT NULL DEFAULT 0,
    normal_daily_rate NUMERIC(12,2) NOT NULL DEFAULT 600.00,

    sunday_days INTEGER NOT NULL DEFAULT 0,
    sunday_rate NUMERIC(12,2) NOT NULL DEFAULT 300.00,

    expected_amount NUMERIC(12,2) GENERATED ALWAYS AS (
        (normal_days * normal_daily_rate)
        +
        (sunday_days * sunday_rate)
    ) STORED,

    actual_amount NUMERIC(12,2) NOT NULL,

    variance NUMERIC(12,2) GENERATED ALWAYS AS (
        actual_amount -
        (
            (normal_days * normal_daily_rate)
            +
            (sunday_days * sunday_rate)
        )
    ) STORED,

    explanation TEXT,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT remittances_collection_fk
        FOREIGN KEY (collection_id)
        REFERENCES remittance_collections(id),

    CONSTRAINT remittances_bus_fk
        FOREIGN KEY (bus_id)
        REFERENCES buses(id),

    CONSTRAINT remittances_normal_days_check
        CHECK (normal_days >= 0),

    CONSTRAINT remittances_sunday_days_check
        CHECK (sunday_days >= 0),

    CONSTRAINT remittances_normal_rate_check
        CHECK (normal_daily_rate >= 0),

    CONSTRAINT remittances_sunday_rate_check
        CHECK (sunday_rate >= 0),

    CONSTRAINT remittances_actual_check
        CHECK (actual_amount >= 0),

    CONSTRAINT remittances_collection_bus_unique
        UNIQUE (collection_id, bus_id)
);

COMMIT;
