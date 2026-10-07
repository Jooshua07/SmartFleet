BEGIN;

-- =========================================================
-- 1. CASHING RATE CONFIGURATION
--
-- Stores the current/default cashing rates used by SmartFleet.
-- Historical remittances continue storing the actual rates
-- that were used at the time.
-- =========================================================

CREATE TABLE cashing_rates (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    rate_type VARCHAR(30) NOT NULL,

    amount NUMERIC(12,2) NOT NULL,

    active BOOLEAN NOT NULL DEFAULT TRUE,

    effective_from DATE NOT NULL DEFAULT CURRENT_DATE,
    effective_to DATE,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT cashing_rates_type_check
        CHECK (
            rate_type IN (
                'NORMAL_DAY',
                'SUNDAY'
            )
        ),

    CONSTRAINT cashing_rates_amount_check
        CHECK (amount >= 0),

    CONSTRAINT cashing_rates_dates_check
        CHECK (
            effective_to IS NULL
            OR effective_to >= effective_from
        )
);


-- Only one currently active rate of each type can exist.
CREATE UNIQUE INDEX unique_active_cashing_rate
ON cashing_rates (rate_type)
WHERE active = TRUE;


-- =========================================================
-- 2. SEED CURRENT BUSINESS RATES
-- =========================================================

INSERT INTO cashing_rates (
    rate_type,
    amount,
    active,
    notes
)
VALUES
    (
        'NORMAL_DAY',
        600.00,
        TRUE,
        'Current normal operating-day cashing rate'
    ),
    (
        'SUNDAY',
        300.00,
        TRUE,
        'Current Sunday cashing rate'
    );


-- =========================================================
-- 3. REMOVE HARDCODED DEFAULTS FROM REMITTANCES
--
-- Rates remain NOT NULL, meaning every historical cashing
-- record must preserve the rates actually used.
--
-- The application will fetch the active cashing rate and
-- insert it into the remittance record.
-- =========================================================

ALTER TABLE remittances
    ALTER COLUMN normal_daily_rate DROP DEFAULT;

ALTER TABLE remittances
    ALTER COLUMN sunday_rate DROP DEFAULT;


COMMIT;
