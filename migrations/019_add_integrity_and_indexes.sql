BEGIN;

-- =========================================================
-- 1. DRIVER ASSIGNMENT INTEGRITY
-- =========================================================

-- A bus can have only ONE active permanent driver.
-- Temporary drivers are still allowed to cover the bus.

CREATE UNIQUE INDEX unique_active_permanent_driver_per_bus
ON driver_assignments (bus_id)
WHERE status = 'ACTIVE'
AND assignment_type = 'PERMANENT';


-- One employment record cannot simultaneously have multiple
-- active permanent bus assignments.

CREATE UNIQUE INDEX unique_active_permanent_bus_per_employment
ON driver_assignments (employment_id)
WHERE status = 'ACTIVE'
AND assignment_type = 'PERMANENT';


-- =========================================================
-- 2. EMPLOYMENT INTEGRITY
-- =========================================================

-- A driver can only have one ACTIVE employment period.

CREATE UNIQUE INDEX unique_active_employment_per_driver
ON driver_employments (driver_id)
WHERE status = 'ACTIVE';


-- =========================================================
-- 3. SALARY → ADVANCE RECOVERY LINKING
-- =========================================================

CREATE TABLE salary_advance_recoveries (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    salary_id INTEGER NOT NULL,
    advance_id INTEGER NOT NULL,

    amount NUMERIC(12,2) NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT salary_advance_recoveries_salary_fk
        FOREIGN KEY (salary_id)
        REFERENCES driver_salaries(id),

    CONSTRAINT salary_advance_recoveries_advance_fk
        FOREIGN KEY (advance_id)
        REFERENCES driver_advances(id),

    CONSTRAINT salary_advance_recoveries_amount_check
        CHECK (amount > 0),

    CONSTRAINT salary_advance_recoveries_unique
        UNIQUE (salary_id, advance_id)
);


-- =========================================================
-- 4. SALARY → DEDUCTION LINKING
-- =========================================================

CREATE TABLE salary_deduction_allocations (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    salary_id INTEGER NOT NULL,
    deduction_id INTEGER NOT NULL,

    amount NUMERIC(12,2) NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT salary_deduction_allocations_salary_fk
        FOREIGN KEY (salary_id)
        REFERENCES driver_salaries(id),

    CONSTRAINT salary_deduction_allocations_deduction_fk
        FOREIGN KEY (deduction_id)
        REFERENCES driver_deductions(id),

    CONSTRAINT salary_deduction_allocations_amount_check
        CHECK (amount > 0),

    CONSTRAINT salary_deduction_allocations_unique
        UNIQUE (salary_id, deduction_id)
);


-- =========================================================
-- 5. COMMON QUERY INDEXES
-- These improve performance for dashboard/report queries.
-- =========================================================

CREATE INDEX idx_driver_employments_driver
ON driver_employments (driver_id);

CREATE INDEX idx_driver_assignments_employment
ON driver_assignments (employment_id);

CREATE INDEX idx_driver_assignments_bus
ON driver_assignments (bus_id);

CREATE INDEX idx_financial_transactions_account_date
ON financial_transactions (account_id, transaction_date);

CREATE INDEX idx_expenses_date
ON expenses (expense_date);

CREATE INDEX idx_expenses_bus
ON expenses (bus_id);

CREATE INDEX idx_expenses_category
ON expenses (category_id);

CREATE INDEX idx_remittances_bus
ON remittances (bus_id);

CREATE INDEX idx_remittance_collections_date
ON remittance_collections (collection_date);

CREATE INDEX idx_maintenance_bus
ON maintenance (bus_id);

CREATE INDEX idx_maintenance_status
ON maintenance (status);

CREATE INDEX idx_loan_repayments_loan
ON loan_repayments (loan_id);

CREATE INDEX idx_driver_salaries_employment_period
ON driver_salaries (
    employment_id,
    salary_year,
    salary_month
);

CREATE INDEX idx_reminders_due_status
ON reminders (
    due_date,
    status
);

COMMIT;
