BEGIN;

-- =========================================================
-- DRIVER SALARY RECORDS
-- One salary record represents one employment's payroll
-- calculation for a particular month.
-- =========================================================

CREATE TABLE driver_salaries (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    employment_id INTEGER NOT NULL,

    salary_year INTEGER NOT NULL,
    salary_month INTEGER NOT NULL,

    base_salary NUMERIC(12,2) NOT NULL,

    prorated_salary NUMERIC(12,2) NOT NULL,

    advance_recovery NUMERIC(12,2) NOT NULL DEFAULT 0.00,

    other_deductions NUMERIC(12,2) NOT NULL DEFAULT 0.00,

    net_salary NUMERIC(12,2) GENERATED ALWAYS AS (
        prorated_salary
        - advance_recovery
        - other_deductions
    ) STORED,

    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',

    payment_date DATE,

    financial_transaction_id INTEGER,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT driver_salaries_employment_fk
        FOREIGN KEY (employment_id)
        REFERENCES driver_employments(id),

    CONSTRAINT driver_salaries_transaction_fk
        FOREIGN KEY (financial_transaction_id)
        REFERENCES financial_transactions(id),

    CONSTRAINT driver_salaries_year_check
        CHECK (salary_year >= 2000),

    CONSTRAINT driver_salaries_month_check
        CHECK (salary_month BETWEEN 1 AND 12),

    CONSTRAINT driver_salaries_base_salary_check
        CHECK (base_salary >= 0),

    CONSTRAINT driver_salaries_prorated_salary_check
        CHECK (prorated_salary >= 0),

    CONSTRAINT driver_salaries_advance_recovery_check
        CHECK (advance_recovery >= 0),

    CONSTRAINT driver_salaries_other_deductions_check
        CHECK (other_deductions >= 0),

    CONSTRAINT driver_salaries_net_salary_check
        CHECK (
            prorated_salary
            - advance_recovery
            - other_deductions
            >= 0
        ),

    CONSTRAINT driver_salaries_status_check
        CHECK (
            status IN (
                'PENDING',
                'PAID',
                'CANCELLED'
            )
        ),

    CONSTRAINT driver_salaries_payment_check
        CHECK (
            (status = 'PAID'
                AND payment_date IS NOT NULL
                AND financial_transaction_id IS NOT NULL)
            OR
            (status IN ('PENDING', 'CANCELLED'))
        ),

    CONSTRAINT driver_salaries_month_unique
        UNIQUE (
            employment_id,
            salary_year,
            salary_month
        )
);

COMMIT;

