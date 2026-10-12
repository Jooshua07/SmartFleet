BEGIN;

-- =========================================================
-- STEP 2: FINANCIAL FOUNDATION AND BUSINESS PRESETS
--
-- Additive preset storage and reporting support. Existing
-- operational and financial rows are preserved.
-- =========================================================

CREATE TABLE business_settings (
    setting_key VARCHAR(80) PRIMARY KEY,
    setting_value TEXT NOT NULL,
    setting_type VARCHAR(20) NOT NULL DEFAULT 'TEXT',
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT business_settings_type_check
        CHECK (setting_type IN ('TEXT', 'DATE', 'NUMBER', 'BOOLEAN', 'ACCOUNT_TYPE'))
);

CREATE TABLE business_preset_audit (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    preset_area VARCHAR(80) NOT NULL,
    preset_key VARCHAR(120) NOT NULL,
    old_value TEXT,
    new_value TEXT NOT NULL,
    effective_date DATE,
    notes TEXT,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE cashing_schedule_rules (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    collection_day INTEGER NOT NULL,
    covered_days INTEGER[] NOT NULL,
    include_previous_sunday BOOLEAN NOT NULL DEFAULT FALSE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    effective_from DATE NOT NULL DEFAULT DATE '2026-10-01',
    effective_to DATE,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT cashing_schedule_rules_collection_day_check
        CHECK (collection_day BETWEEN 1 AND 7),

    CONSTRAINT cashing_schedule_rules_covered_days_check
        CHECK (
            array_length(covered_days, 1) > 0
            AND covered_days <@ ARRAY[1,2,3,4,5,6,7]
        ),

    CONSTRAINT cashing_schedule_rules_dates_check
        CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

CREATE TABLE driver_salary_presets (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    driver_id INTEGER,
    monthly_salary NUMERIC(12,2) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    effective_from DATE NOT NULL DEFAULT DATE '2026-10-01',
    effective_to DATE,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT driver_salary_presets_driver_fk
        FOREIGN KEY (driver_id)
        REFERENCES drivers(id),

    CONSTRAINT driver_salary_presets_amount_check
        CHECK (monthly_salary >= 0),

    CONSTRAINT driver_salary_presets_dates_check
        CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

CREATE UNIQUE INDEX unique_active_driver_salary_default
ON driver_salary_presets ((driver_id IS NULL))
WHERE active = TRUE AND driver_id IS NULL;

CREATE UNIQUE INDEX unique_active_driver_salary_override
ON driver_salary_presets (driver_id)
WHERE active = TRUE AND driver_id IS NOT NULL;

CREATE TABLE reminder_presets (
    preset_key VARCHAR(80) PRIMARY KEY,
    warning_days INTEGER NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT reminder_presets_days_check
        CHECK (warning_days >= 0)
);

INSERT INTO business_settings (setting_key, setting_value, setting_type, notes)
VALUES
    ('REPORTING_BASELINE_DATE', '2026-10-01', 'DATE', 'Clean business reporting baseline'),
    ('DEFAULT_COLLECTION_ACCOUNT_TYPE', 'AIRTEL_MONEY', 'ACCOUNT_TYPE', 'Airtel Money is the operational collection destination')
ON CONFLICT (setting_key) DO NOTHING;

INSERT INTO cashing_schedule_rules (
    collection_day,
    covered_days,
    include_previous_sunday,
    notes
)
VALUES
    (4, ARRAY[1,2,3], TRUE, 'Thursday collection covers Monday-Wednesday plus selected previous Sunday work'),
    (7, ARRAY[4,5,6], FALSE, 'Sunday collection covers Thursday-Saturday')
ON CONFLICT DO NOTHING;

INSERT INTO driver_salary_presets (
    driver_id,
    monthly_salary,
    notes
)
VALUES (
    NULL,
    2000.00,
    'Standard driver salary preset; does not record a salary payment'
)
ON CONFLICT DO NOTHING;

INSERT INTO reminder_presets (preset_key, warning_days, notes)
VALUES
    ('MAINTENANCE_WARNING_DAYS', 21, 'Default maintenance warning period'),
    ('DOCUMENT_EXPIRY_WARNING_DAYS', 21, 'Default document expiry warning period'),
    ('OVERDUE_CASHING_WARNING_DAYS', 1, 'Default overdue cashing reminder period')
ON CONFLICT (preset_key) DO NOTHING;

-- Allow a loan repayment to be recorded before the original loan is known.
-- The financial transaction remains the real money movement. Linking to a
-- business loan can happen later without duplicating the payment.
ALTER TABLE loan_repayments
    ALTER COLUMN loan_id DROP NOT NULL;

CREATE OR REPLACE FUNCTION sf_assert_loan_repayment(p_id INTEGER) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    r loan_repayments%ROWTYPE;
    f financial_transactions%ROWTYPE;
    o owner_loan_transactions%ROWTYPE;
BEGIN
    SELECT * INTO r FROM loan_repayments WHERE id = p_id;
    IF NOT FOUND THEN RETURN; END IF;

    IF r.loan_id IS NULL AND NULLIF(BTRIM(COALESCE(r.notes, '')), '') IS NULL THEN
        RAISE EXCEPTION 'Unidentified loan repayment % requires explanatory notes', p_id;
    END IF;

    IF r.payment_source = 'BUSINESS_ACCOUNT' THEN
        SELECT * INTO f FROM financial_transactions WHERE id = r.financial_transaction_id;
        IF NOT FOUND OR (f.transaction_type <> 'LOAN_REPAYMENT'
                         AND NOT sf_is_external_transfer(f.id)) OR f.direction <> 'OUT'
           OR f.amount <> r.amount OR f.transaction_date <> r.repayment_date THEN
            RAISE EXCEPTION 'Loan repayment % does not match OUT ledger entry', p_id;
        END IF;
    ELSE
        SELECT * INTO o FROM owner_loan_transactions WHERE id = r.owner_loan_transaction_id;
        IF NOT FOUND OR o.transaction_type <> 'OWNER_FUNDED' OR o.expense_id IS NOT NULL
           OR o.financial_transaction_id IS NOT NULL OR o.amount <> r.amount
           OR o.transaction_date <> r.repayment_date THEN
            RAISE EXCEPTION 'Loan repayment % does not match owner-personal funding', p_id;
        END IF;
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION sf_integrity_deferred() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
DECLARE
    old_ledger_id INTEGER;
    new_ledger_id INTEGER;
BEGIN
    IF TG_OP IN ('UPDATE','DELETE') THEN
        CASE TG_TABLE_NAME
        WHEN 'financial_transactions' THEN
            PERFORM sf_assert_ledger(OLD.id);
            IF OLD.transfer_id IS NOT NULL THEN PERFORM sf_assert_transfer(OLD.transfer_id); END IF;
        WHEN 'transfers' THEN PERFORM sf_assert_transfer(OLD.id);
        WHEN 'expenses' THEN
            PERFORM sf_assert_expense(OLD.id);
            PERFORM sf_assert_maintenance(m.id) FROM maintenance m WHERE m.expense_id = OLD.id;
            old_ledger_id := OLD.financial_transaction_id;
        WHEN 'remittance_collections' THEN
            PERFORM sf_assert_collection(OLD.id);
            old_ledger_id := OLD.financial_transaction_id;
        WHEN 'remittances' THEN PERFORM sf_assert_collection(OLD.collection_id);
        WHEN 'expense_allocations' THEN
            PERFORM sf_assert_expense(OLD.expense_id);
            PERFORM sf_assert_maintenance(m.id) FROM maintenance m WHERE m.expense_id = OLD.expense_id;
        WHEN 'driver_advances' THEN
            PERFORM sf_assert_advance(OLD.id);
            old_ledger_id := OLD.financial_transaction_id;
        WHEN 'driver_deductions' THEN PERFORM sf_assert_deduction(OLD.id);
        WHEN 'driver_salaries' THEN
            PERFORM sf_assert_salary(OLD.id);
            old_ledger_id := OLD.financial_transaction_id;
        WHEN 'salary_advance_recoveries' THEN
            PERFORM sf_assert_salary(OLD.salary_id);
            PERFORM sf_assert_advance(OLD.advance_id);
        WHEN 'salary_deduction_allocations' THEN
            PERFORM sf_assert_salary(OLD.salary_id);
            PERFORM sf_assert_deduction(OLD.deduction_id);
        WHEN 'owner_loan_transactions' THEN
            PERFORM sf_assert_owner_loan_transaction(OLD.id);
            PERFORM sf_assert_owner_balance(OLD.owner_loan_id);
            IF OLD.expense_id IS NOT NULL THEN PERFORM sf_assert_expense(OLD.expense_id); END IF;
            old_ledger_id := OLD.financial_transaction_id;
        WHEN 'loan_repayments' THEN
            PERFORM sf_assert_loan_repayment(OLD.id);
            IF OLD.loan_id IS NOT NULL THEN PERFORM sf_assert_business_loan(OLD.loan_id); END IF;
            old_ledger_id := OLD.financial_transaction_id;
            IF OLD.owner_loan_transaction_id IS NOT NULL THEN
                PERFORM sf_assert_owner_loan_transaction(OLD.owner_loan_transaction_id);
            END IF;
        WHEN 'business_loans' THEN PERFORM sf_assert_business_loan(OLD.id);
        WHEN 'driver_assignments' THEN PERFORM sf_assert_employment(OLD.employment_id);
        WHEN 'driver_employments' THEN PERFORM sf_assert_employment(OLD.id);
        WHEN 'maintenance' THEN PERFORM sf_assert_maintenance(OLD.id);
        WHEN 'cashing_rates' THEN PERFORM sf_assert_rate(OLD.id);
        WHEN 'transfer_fee_rules' THEN
            PERFORM sf_assert_fee_rule(OLD.id);
            PERFORM sf_assert_transfer(t.id) FROM transfers t WHERE t.fee_rule_id = OLD.id;
        END CASE;
        IF old_ledger_id IS NOT NULL THEN PERFORM sf_assert_ledger(old_ledger_id); END IF;
    END IF;

    IF TG_OP IN ('INSERT','UPDATE') THEN
        CASE TG_TABLE_NAME
        WHEN 'financial_transactions' THEN
            PERFORM sf_assert_ledger(NEW.id);
            IF NEW.transfer_id IS NOT NULL THEN PERFORM sf_assert_transfer(NEW.transfer_id); END IF;
        WHEN 'transfers' THEN PERFORM sf_assert_transfer(NEW.id);
        WHEN 'expenses' THEN
            PERFORM sf_assert_expense(NEW.id);
            PERFORM sf_assert_maintenance(m.id) FROM maintenance m WHERE m.expense_id = NEW.id;
            new_ledger_id := NEW.financial_transaction_id;
        WHEN 'remittance_collections' THEN
            PERFORM sf_assert_collection(NEW.id);
            new_ledger_id := NEW.financial_transaction_id;
        WHEN 'remittances' THEN PERFORM sf_assert_collection(NEW.collection_id);
        WHEN 'expense_allocations' THEN
            PERFORM sf_assert_expense(NEW.expense_id);
            PERFORM sf_assert_maintenance(m.id) FROM maintenance m WHERE m.expense_id = NEW.expense_id;
        WHEN 'driver_advances' THEN
            PERFORM sf_assert_advance(NEW.id);
            new_ledger_id := NEW.financial_transaction_id;
        WHEN 'driver_deductions' THEN PERFORM sf_assert_deduction(NEW.id);
        WHEN 'driver_salaries' THEN
            PERFORM sf_assert_salary(NEW.id);
            new_ledger_id := NEW.financial_transaction_id;
        WHEN 'salary_advance_recoveries' THEN
            PERFORM sf_assert_salary(NEW.salary_id);
            PERFORM sf_assert_advance(NEW.advance_id);
        WHEN 'salary_deduction_allocations' THEN
            PERFORM sf_assert_salary(NEW.salary_id);
            PERFORM sf_assert_deduction(NEW.deduction_id);
        WHEN 'owner_loan_transactions' THEN
            PERFORM sf_assert_owner_loan_transaction(NEW.id);
            PERFORM sf_assert_owner_balance(NEW.owner_loan_id);
            IF NEW.expense_id IS NOT NULL THEN PERFORM sf_assert_expense(NEW.expense_id); END IF;
            new_ledger_id := NEW.financial_transaction_id;
        WHEN 'loan_repayments' THEN
            PERFORM sf_assert_loan_repayment(NEW.id);
            IF NEW.loan_id IS NOT NULL THEN PERFORM sf_assert_business_loan(NEW.loan_id); END IF;
            new_ledger_id := NEW.financial_transaction_id;
            IF NEW.owner_loan_transaction_id IS NOT NULL THEN
                PERFORM sf_assert_owner_loan_transaction(NEW.owner_loan_transaction_id);
            END IF;
        WHEN 'business_loans' THEN PERFORM sf_assert_business_loan(NEW.id);
        WHEN 'driver_assignments' THEN PERFORM sf_assert_employment(NEW.employment_id);
        WHEN 'driver_employments' THEN PERFORM sf_assert_employment(NEW.id);
        WHEN 'maintenance' THEN PERFORM sf_assert_maintenance(NEW.id);
        WHEN 'cashing_rates' THEN PERFORM sf_assert_rate(NEW.id);
        WHEN 'transfer_fee_rules' THEN
            PERFORM sf_assert_fee_rule(NEW.id);
            PERFORM sf_assert_transfer(t.id) FROM transfers t WHERE t.fee_rule_id = NEW.id;
        END CASE;
        IF new_ledger_id IS NOT NULL THEN PERFORM sf_assert_ledger(new_ledger_id); END IF;
    END IF;
    RETURN NULL;
END;
$$;

DO $$
DECLARE
    tab TEXT;
BEGIN
    FOREACH tab IN ARRAY ARRAY[
        'business_settings',
        'cashing_schedule_rules',
        'driver_salary_presets',
        'reminder_presets'
    ] LOOP
        EXECUTE format(
          'CREATE TRIGGER sf_touch_updated_at BEFORE UPDATE ON public.%I '
          || 'FOR EACH ROW EXECUTE FUNCTION sf_touch_updated_at()',
          tab
        );
    END LOOP;
END;
$$;

COMMIT;
