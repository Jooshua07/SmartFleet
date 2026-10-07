BEGIN;

-- =========================================================
-- 1. DRIVER ADVANCES
-- Money advanced to a driver and recovered from future salary.
-- =========================================================

CREATE TABLE driver_advances (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    employment_id INTEGER NOT NULL,

    advance_date DATE NOT NULL,

    amount NUMERIC(12,2) NOT NULL,

    planned_repayment_amount NUMERIC(12,2),

    financial_transaction_id INTEGER,

    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',

    reason TEXT,
    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT driver_advances_employment_fk
        FOREIGN KEY (employment_id)
        REFERENCES driver_employments(id),

    CONSTRAINT driver_advances_transaction_fk
        FOREIGN KEY (financial_transaction_id)
        REFERENCES financial_transactions(id),

    CONSTRAINT driver_advances_amount_check
        CHECK (amount > 0),

    CONSTRAINT driver_advances_repayment_check
        CHECK (
            planned_repayment_amount IS NULL
            OR planned_repayment_amount > 0
        ),

    CONSTRAINT driver_advances_status_check
        CHECK (
            status IN (
                'ACTIVE',
                'REPAID',
                'CANCELLED'
            )
        )
);


-- =========================================================
-- 2. DRIVER DEDUCTIONS
-- Non-advance deductions such as penalties.
-- =========================================================

CREATE TABLE driver_deductions (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    employment_id INTEGER NOT NULL,

    deduction_date DATE NOT NULL,

    amount NUMERIC(12,2) NOT NULL,

    deduction_type VARCHAR(30) NOT NULL,

    reason TEXT NOT NULL,

    applied BOOLEAN NOT NULL DEFAULT FALSE,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT driver_deductions_employment_fk
        FOREIGN KEY (employment_id)
        REFERENCES driver_employments(id),

    CONSTRAINT driver_deductions_amount_check
        CHECK (amount > 0),

    CONSTRAINT driver_deductions_type_check
        CHECK (
            deduction_type IN (
                'PENALTY',
                'OTHER'
            )
        )
);

COMMIT;
