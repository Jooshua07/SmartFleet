-- SmartFleet migration 022: Schema V1 integrity hardening
-- Requires migrations 001-021 already applied.
-- Run as ONE file. All DDL and seed adjustments are atomic.
-- IMPORTANT: The application must write related business records and ledger rows
-- in the SAME transaction; deferred constraints validate the completed operation.
BEGIN;

-- 1. Structural improvements and one-time configuration correction.
ALTER TABLE financial_transactions
    ADD COLUMN transfer_id INTEGER REFERENCES transfers(id);

ALTER TABLE financial_transactions DROP CONSTRAINT financial_transactions_type_check;
ALTER TABLE financial_transactions ADD CONSTRAINT financial_transactions_type_check
    CHECK (transaction_type IN (
        'CASHING','EXPENSE','TRANSFER','TRANSFER_FEE','OWNER_LOAN',
        'OWNER_LOAN_REPAYMENT','OWNER_DRAWING','LOAN_RECEIVED',
        'LOAN_REPAYMENT','DRIVER_ADVANCE','DRIVER_SALARY','OTHER'
    ));

ALTER TABLE financial_transactions ADD CONSTRAINT financial_transactions_transfer_link_check
    CHECK ((transfer_id IS NOT NULL) = (transaction_type IN ('TRANSFER','TRANSFER_FEE')));

ALTER TABLE expenses ADD CONSTRAINT expenses_financial_link_check CHECK (
    (payment_source = 'BUSINESS_ACCOUNT' AND financial_transaction_id IS NOT NULL)
    OR (payment_source = 'OWNER_PERSONAL' AND financial_transaction_id IS NULL)
);

-- Zero-cashing events are valid; there is no K0 ledger movement to insert.
ALTER TABLE remittance_collections ADD CONSTRAINT remittance_collections_ledger_check CHECK (
    (total_amount = 0 AND financial_transaction_id IS NULL)
    OR (total_amount > 0 AND financial_transaction_id IS NOT NULL)
);
ALTER TABLE driver_advances ALTER COLUMN financial_transaction_id SET NOT NULL;
-- A zero-net salary can be settled without a zero-value ledger movement.
ALTER TABLE driver_salaries DROP CONSTRAINT driver_salaries_payment_check;
ALTER TABLE driver_salaries ADD CONSTRAINT driver_salaries_payment_check CHECK (
    (status = 'PAID' AND payment_date IS NOT NULL AND
        ((net_salary = 0 AND financial_transaction_id IS NULL)
         OR (net_salary > 0 AND financial_transaction_id IS NOT NULL)))
    OR (status IN ('PENDING','CANCELLED') AND payment_date IS NULL
        AND financial_transaction_id IS NULL)
);
ALTER TABLE remittances ADD CONSTRAINT remittances_variance_reason_check CHECK (
    actual_amount = (normal_days * normal_daily_rate + sunday_days * sunday_rate)
    OR NULLIF(BTRIM(explanation), '') IS NOT NULL
);
ALTER TABLE maintenance ADD CONSTRAINT maintenance_completed_date_check CHECK (
    (status = 'COMPLETED' AND completed_date IS NOT NULL)
    OR (status <> 'COMPLETED' AND completed_date IS NULL)
);
ALTER TABLE transfers ADD CONSTRAINT transfers_external_recipient_check CHECK (
    destination_account_id IS NOT NULL
    OR NULLIF(BTRIM(recipient_description), '') IS NOT NULL
);

-- A ledger entry must not be reused to pay multiple unrelated items of one kind.
CREATE UNIQUE INDEX ux_expenses_financial_tx ON expenses(financial_transaction_id)
    WHERE financial_transaction_id IS NOT NULL;
CREATE UNIQUE INDEX ux_cashing_financial_tx ON remittance_collections(financial_transaction_id);
CREATE UNIQUE INDEX ux_advance_financial_tx ON driver_advances(financial_transaction_id);
CREATE UNIQUE INDEX ux_salaries_financial_tx ON driver_salaries(financial_transaction_id)
    WHERE financial_transaction_id IS NOT NULL;
CREATE UNIQUE INDEX ux_owner_loan_financial_tx ON owner_loan_transactions(financial_transaction_id)
    WHERE financial_transaction_id IS NOT NULL;
CREATE UNIQUE INDEX ux_owner_funded_expense ON owner_loan_transactions(expense_id)
    WHERE expense_id IS NOT NULL;
CREATE UNIQUE INDEX ux_business_loan_repayment_financial_tx ON loan_repayments(financial_transaction_id)
    WHERE financial_transaction_id IS NOT NULL;
CREATE UNIQUE INDEX ux_business_loan_repayment_owner_tx ON loan_repayments(owner_loan_transaction_id)
    WHERE owner_loan_transaction_id IS NOT NULL;
CREATE INDEX idx_financial_transactions_transfer ON financial_transactions(transfer_id)
    WHERE transfer_id IS NOT NULL;
CREATE INDEX idx_owner_loan_tx_owner ON owner_loan_transactions(owner_loan_id);
CREATE INDEX idx_recoveries_advance ON salary_advance_recoveries(advance_id);
CREATE INDEX idx_deduction_allocations_deduction ON salary_deduction_allocations(deduction_id);

UPDATE transfer_fee_rules
SET minimum_amount = 1.00
WHERE transfer_type = 'AIRTEL_TO_BANK' AND minimum_amount = 0.01 AND maximum_amount = 5000.00;

-- Suggested fee stays in PostgreSQL, not in a Streamlit-only calculation.
-- NULL means the transfer needs a manual fee (e.g. Airtel-to-Airtel over K10,000).
-- For Airtel-to-Bank above the last configured band, extend the agreed K50/5,000 rule.
CREATE FUNCTION sf_suggest_transfer_fee(p_type TEXT, p_amount NUMERIC)
RETURNS NUMERIC LANGUAGE plpgsql STABLE AS $$
DECLARE
    suggested NUMERIC(12,2);
    maximum_configured NUMERIC(12,2);
BEGIN
    IF p_amount < 1 THEN RETURN NULL; END IF;
    SELECT fee_amount INTO suggested FROM transfer_fee_rules
      WHERE active AND transfer_type = p_type
        AND p_amount >= minimum_amount
        AND (maximum_amount IS NULL OR p_amount <= maximum_amount)
      ORDER BY minimum_amount DESC LIMIT 1;
    IF FOUND THEN RETURN suggested; END IF;
    SELECT MAX(maximum_amount) INTO maximum_configured FROM transfer_fee_rules
      WHERE active AND transfer_type = p_type;
    IF p_type = 'AIRTEL_TO_BANK' AND maximum_configured IS NOT NULL
       AND p_amount > maximum_configured THEN
        RETURN CEIL(p_amount / 5000.00) * 50.00;
    END IF;
    RETURN NULL;
END;
$$;

-- An outward Airtel payment to an *external* party is a genuine payment,
-- not an internal transfer. Its one principal OUT ledger row may also be linked
-- to the salary, advance, expense, or loan it paid, without a second debit.
CREATE FUNCTION sf_is_external_transfer(p_financial_tx_id INTEGER)
RETURNS BOOLEAN LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
      SELECT 1 FROM financial_transactions f
      JOIN transfers t ON t.id = f.transfer_id
      WHERE f.id = p_financial_tx_id
        AND f.transaction_type = 'TRANSFER' AND f.direction = 'OUT'
        AND t.destination_account_id IS NULL
  );
$$;

-- 2. Named validation functions. These raise exceptions, never silently repair data.
CREATE FUNCTION sf_assert_transfer(p_id INTEGER) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    t transfers%ROWTYPE;
    src_type TEXT;
    dst_type TEXT;
    n_all INTEGER;
    n_src INTEGER;
    n_dst INTEGER;
    n_fee INTEGER;
    expected_dst INTEGER;
    expected_fee INTEGER;
    expected_all INTEGER;
BEGIN
    SELECT * INTO t FROM transfers WHERE id = p_id FOR UPDATE;
    IF NOT FOUND THEN RETURN; END IF;
    SELECT account_type INTO src_type FROM financial_accounts WHERE id = t.source_account_id;
    IF t.destination_account_id IS NOT NULL THEN
        SELECT account_type INTO dst_type FROM financial_accounts WHERE id = t.destination_account_id;
    END IF;
    IF t.transfer_type IN ('AIRTEL_TO_BANK','AIRTEL_TO_AIRTEL') AND src_type <> 'AIRTEL_MONEY' THEN
        RAISE EXCEPTION 'Transfer % requires Airtel Money source', p_id;
    END IF;
    IF t.transfer_type IN ('AIRTEL_TO_BANK','AIRTEL_TO_AIRTEL') AND t.amount < 1 THEN
        RAISE EXCEPTION 'Airtel transfer % must be at least K1', p_id;
    END IF;
    IF t.transfer_type = 'AIRTEL_TO_BANK'
       AND (t.destination_account_id IS NULL OR dst_type <> 'BANK') THEN
        RAISE EXCEPTION 'Transfer % requires tracked BANK destination', p_id;
    END IF;
    IF t.transfer_type = 'AIRTEL_TO_AIRTEL'
       AND t.destination_account_id IS NOT NULL AND dst_type <> 'AIRTEL_MONEY' THEN
        RAISE EXCEPTION 'Transfer % destination must be Airtel or external', p_id;
    END IF;
    IF t.transfer_type = 'INTERNAL' AND t.destination_account_id IS NULL THEN
        RAISE EXCEPTION 'Internal transfer % requires a destination account', p_id;
    END IF;
    IF t.fee_rule_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM transfer_fee_rules r WHERE r.id = t.fee_rule_id
          AND r.transfer_type = t.transfer_type
          AND t.amount >= r.minimum_amount
          AND (r.maximum_amount IS NULL OR t.amount <= r.maximum_amount)
    ) THEN
        RAISE EXCEPTION 'Transfer % cites a fee rule for the wrong type or amount', p_id;
    END IF;

    SELECT COUNT(*) INTO n_all FROM financial_transactions WHERE transfer_id = p_id;
    SELECT COUNT(*) INTO n_src FROM financial_transactions
      WHERE transfer_id = p_id AND transaction_type = 'TRANSFER' AND direction = 'OUT'
        AND account_id = t.source_account_id AND amount = t.amount
        AND transaction_date = t.transfer_date;
    SELECT COUNT(*) INTO n_dst FROM financial_transactions
      WHERE transfer_id = p_id AND transaction_type = 'TRANSFER' AND direction = 'IN'
        AND account_id = t.destination_account_id AND amount = t.amount
        AND transaction_date = t.transfer_date;
    SELECT COUNT(*) INTO n_fee FROM financial_transactions
      WHERE transfer_id = p_id AND transaction_type = 'TRANSFER_FEE' AND direction = 'OUT'
        AND account_id = t.source_account_id AND amount = t.fee_amount
        AND transaction_date = t.transfer_date;
    -- Compute the expected entries separately; do not embed CASE in IF parsing.
    expected_dst := 0;
    IF t.destination_account_id IS NOT NULL THEN
        expected_dst := 1;
    END IF;
    expected_fee := 0;
    IF t.fee_amount > 0 THEN
        expected_fee := 1;
    END IF;
    expected_all := 1 + expected_dst + expected_fee;
    IF n_src <> 1 OR n_dst <> expected_dst
       OR n_fee <> expected_fee OR n_all <> expected_all THEN
        RAISE EXCEPTION 'Transfer % ledger mismatch (principal/destination/fee)', p_id;
    END IF;
END;
$$;

CREATE FUNCTION sf_assert_expense(p_id INTEGER) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    e expenses%ROWTYPE;
    f financial_transactions%ROWTYPE;
    n INTEGER;
    allocated NUMERIC(14,2);
BEGIN
    SELECT * INTO e FROM expenses WHERE id = p_id FOR UPDATE;
    IF NOT FOUND THEN RETURN; END IF;
    SELECT COALESCE(SUM(allocated_amount),0) INTO allocated
      FROM expense_allocations WHERE expense_id = p_id;
    IF (e.scope = 'MULTI_BUS' AND allocated <> e.amount)
       OR (e.scope <> 'MULTI_BUS' AND allocated <> 0) THEN
        RAISE EXCEPTION 'Expense % allocation total % invalid for scope % and amount %',
            p_id, allocated, e.scope, e.amount;
    END IF;
    IF e.payment_source = 'BUSINESS_ACCOUNT' THEN
        SELECT * INTO f FROM financial_transactions WHERE id = e.financial_transaction_id;
        IF NOT FOUND OR f.direction <> 'OUT' OR f.account_id <> e.financial_account_id
           OR f.amount <> e.amount OR f.transaction_date <> e.expense_date
           OR f.transaction_type NOT IN
              ('EXPENSE','OWNER_DRAWING','TRANSFER_FEE','DRIVER_SALARY',
               'LOAN_REPAYMENT','DRIVER_ADVANCE','OTHER')
               AND NOT sf_is_external_transfer(f.id) THEN
            RAISE EXCEPTION 'Expense % must match a valid OUT financial transaction', p_id;
        END IF;
    ELSE
        SELECT COUNT(*) INTO n FROM owner_loan_transactions o
          WHERE o.expense_id = e.id AND o.transaction_type = 'OWNER_FUNDED'
            AND o.amount = e.amount AND o.transaction_date = e.expense_date
            AND o.financial_transaction_id IS NULL;
        IF n <> 1 THEN
            RAISE EXCEPTION 'Owner-personal expense % needs matching OWNER_FUNDED transaction', p_id;
        END IF;
    END IF;
END;
$$;

CREATE FUNCTION sf_assert_collection(p_id INTEGER) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    c remittance_collections%ROWTYPE;
    f financial_transactions%ROWTYPE;
    child_total NUMERIC(12,2);
BEGIN
    SELECT * INTO c FROM remittance_collections WHERE id = p_id FOR UPDATE;
    IF NOT FOUND THEN RETURN; END IF;
    IF c.total_amount > 0 THEN
        SELECT * INTO f FROM financial_transactions WHERE id = c.financial_transaction_id;
        IF NOT FOUND OR f.transaction_type <> 'CASHING' OR f.direction <> 'IN'
           OR f.account_id <> c.financial_account_id OR f.amount <> c.total_amount
           OR f.transaction_date <> c.collection_date THEN
            RAISE EXCEPTION 'Cashing collection % does not match its IN ledger transaction', p_id;
        END IF;
    END IF;
    SELECT COALESCE(SUM(actual_amount), 0) INTO child_total FROM remittances
      WHERE collection_id = p_id;
    IF child_total <> c.total_amount THEN
        RAISE EXCEPTION 'Collection % total % differs from remittances total %',
            p_id, c.total_amount, child_total;
    END IF;
END;
$$;

CREATE FUNCTION sf_assert_advance(p_id INTEGER) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    a driver_advances%ROWTYPE;
    f financial_transactions%ROWTYPE;
    recovered NUMERIC(12,2);
BEGIN
    SELECT * INTO a FROM driver_advances WHERE id = p_id FOR UPDATE;
    IF NOT FOUND THEN RETURN; END IF;
    SELECT * INTO f FROM financial_transactions WHERE id = a.financial_transaction_id;
    IF NOT FOUND OR (f.transaction_type <> 'DRIVER_ADVANCE'
                     AND NOT sf_is_external_transfer(f.id)) OR f.direction <> 'OUT'
       OR f.amount <> a.amount OR f.transaction_date <> a.advance_date THEN
        RAISE EXCEPTION 'Driver advance % must match its OUT ledger transaction', p_id;
    END IF;
    -- Only PAID payroll actually recovers an advance; pending payroll is a plan.
    SELECT COALESCE(SUM(ar.amount),0) INTO recovered
       FROM salary_advance_recoveries ar
       JOIN driver_salaries s ON s.id = ar.salary_id
       WHERE ar.advance_id = p_id AND s.status = 'PAID';
    IF recovered > a.amount THEN
        RAISE EXCEPTION 'Driver advance % over-recovered: % > %', p_id, recovered, a.amount;
    END IF;
    IF a.status = 'REPAID' AND recovered <> a.amount THEN
        RAISE EXCEPTION 'Driver advance % marked REPAID before full recovery', p_id;
    END IF;
    IF EXISTS (
        SELECT 1 FROM salary_advance_recoveries ar
        JOIN driver_salaries s ON s.id = ar.salary_id
        WHERE ar.advance_id = p_id AND s.employment_id <> a.employment_id
    ) THEN
        RAISE EXCEPTION 'Driver advance % is allocated to a different employment', p_id;
    END IF;
END;
$$;

CREATE FUNCTION sf_assert_deduction(p_id INTEGER) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    d driver_deductions%ROWTYPE;
    allocated NUMERIC(12,2);
BEGIN
    SELECT * INTO d FROM driver_deductions WHERE id = p_id FOR UPDATE;
    IF NOT FOUND THEN RETURN; END IF;
    -- A pending salary does not yet make a deduction 'applied'.
    SELECT COALESCE(SUM(da.amount),0) INTO allocated
      FROM salary_deduction_allocations da
      JOIN driver_salaries s ON s.id = da.salary_id
      WHERE da.deduction_id = p_id AND s.status = 'PAID';
    IF allocated > d.amount THEN
        RAISE EXCEPTION 'Driver deduction % over-applied: % > %', p_id, allocated, d.amount;
    END IF;
    IF d.applied IS DISTINCT FROM (allocated = d.amount) THEN
        RAISE EXCEPTION 'Driver deduction % applied flag must mean fully allocated', p_id;
    END IF;
    IF EXISTS (
        SELECT 1 FROM salary_deduction_allocations da
        JOIN driver_salaries s ON s.id = da.salary_id
        WHERE da.deduction_id = p_id AND s.employment_id <> d.employment_id
    ) THEN
        RAISE EXCEPTION 'Driver deduction % is allocated to a different employment', p_id;
    END IF;
END;
$$;

CREATE FUNCTION sf_assert_salary(p_id INTEGER) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    s driver_salaries%ROWTYPE;
    f financial_transactions%ROWTYPE;
    recovered NUMERIC(12,2);
    deducted NUMERIC(12,2);
BEGIN
    SELECT * INTO s FROM driver_salaries WHERE id = p_id FOR UPDATE;
    IF NOT FOUND THEN RETURN; END IF;
    SELECT COALESCE(SUM(amount),0) INTO recovered FROM salary_advance_recoveries
      WHERE salary_id = p_id;
    SELECT COALESCE(SUM(amount),0) INTO deducted FROM salary_deduction_allocations
      WHERE salary_id = p_id;
    IF recovered <> s.advance_recovery OR deducted <> s.other_deductions THEN
        RAISE EXCEPTION 'Salary % allocations do not reconcile (advance %, deduction %)',
             p_id, recovered, deducted;
    END IF;
    IF EXISTS (
      SELECT 1 FROM salary_advance_recoveries ar
      JOIN driver_advances a ON a.id = ar.advance_id
      WHERE ar.salary_id = p_id AND a.employment_id <> s.employment_id
    ) OR EXISTS (
      SELECT 1 FROM salary_deduction_allocations da
      JOIN driver_deductions d ON d.id = da.deduction_id
      WHERE da.salary_id = p_id AND d.employment_id <> s.employment_id
    ) THEN
        RAISE EXCEPTION 'Salary % contains an allocation from another employment', p_id;
    END IF;
    IF s.status = 'CANCELLED' AND (recovered <> 0 OR deducted <> 0) THEN
        RAISE EXCEPTION 'Cancelled salary % cannot keep advance/deduction allocations', p_id;
    END IF;
    IF s.status = 'PAID' AND s.net_salary > 0 THEN
        SELECT * INTO f FROM financial_transactions WHERE id = s.financial_transaction_id;
        IF NOT FOUND OR f.direction <> 'OUT'
           OR (f.transaction_type <> 'DRIVER_SALARY' AND NOT sf_is_external_transfer(f.id))
           OR f.amount <> s.net_salary OR f.transaction_date <> s.payment_date THEN
            RAISE EXCEPTION 'Paid salary % must match its OUT payment ledger entry', p_id;
        END IF;
    END IF;
    -- Salary status transitions change the *effective* recovered/applied totals.
    PERFORM sf_assert_advance(ar.advance_id)
        FROM salary_advance_recoveries ar WHERE ar.salary_id = p_id;
    PERFORM sf_assert_deduction(da.deduction_id)
        FROM salary_deduction_allocations da WHERE da.salary_id = p_id;
END;
$$;

CREATE FUNCTION sf_assert_owner_loan_transaction(p_id INTEGER) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    o owner_loan_transactions%ROWTYPE;
    e expenses%ROWTYPE;
    f financial_transactions%ROWTYPE;
    r loan_repayments%ROWTYPE;
BEGIN
    SELECT * INTO o FROM owner_loan_transactions WHERE id = p_id;
    IF NOT FOUND THEN RETURN; END IF;
    IF o.transaction_type = 'REPAYMENT' THEN
        IF o.expense_id IS NOT NULL OR o.financial_transaction_id IS NULL THEN
            RAISE EXCEPTION 'Owner repayment % needs ledger, not expense', p_id;
        END IF;
        SELECT * INTO f FROM financial_transactions WHERE id = o.financial_transaction_id;
        IF NOT FOUND OR (f.transaction_type <> 'OWNER_LOAN_REPAYMENT'
                         AND NOT sf_is_external_transfer(f.id)) OR f.direction <> 'OUT'
           OR f.amount <> o.amount OR f.transaction_date <> o.transaction_date THEN
            RAISE EXCEPTION 'Owner repayment % has invalid OUT ledger transaction', p_id;
        END IF;
    ELSE
        IF o.expense_id IS NOT NULL AND o.financial_transaction_id IS NULL THEN
            SELECT * INTO e FROM expenses WHERE id = o.expense_id;
            IF NOT FOUND OR e.payment_source <> 'OWNER_PERSONAL'
               OR e.amount <> o.amount OR e.expense_date <> o.transaction_date THEN
                RAISE EXCEPTION 'Owner funding % does not match personal expense', p_id;
            END IF;
        ELSIF o.expense_id IS NULL AND o.financial_transaction_id IS NOT NULL THEN
            SELECT * INTO f FROM financial_transactions WHERE id = o.financial_transaction_id;
            IF NOT FOUND OR f.transaction_type <> 'OWNER_LOAN' OR f.direction <> 'IN'
               OR f.amount <> o.amount OR f.transaction_date <> o.transaction_date THEN
                RAISE EXCEPTION 'Owner funding % does not match IN ledger transaction', p_id;
            END IF;
        ELSIF o.expense_id IS NULL AND o.financial_transaction_id IS NULL THEN
            SELECT * INTO r FROM loan_repayments WHERE owner_loan_transaction_id = o.id;
            IF NOT FOUND OR r.payment_source <> 'OWNER_PERSONAL'
               OR r.amount <> o.amount OR r.repayment_date <> o.transaction_date THEN
                RAISE EXCEPTION 'Owner funding % requires linked personal-paid business loan', p_id;
            END IF;
        ELSE
            RAISE EXCEPTION 'Owner funding % cannot link expense and cash inflow together', p_id;
        END IF;
    END IF;
    IF EXISTS(SELECT 1 FROM loan_repayments WHERE owner_loan_transaction_id = o.id)
       AND (o.transaction_type <> 'OWNER_FUNDED' OR o.expense_id IS NOT NULL
            OR o.financial_transaction_id IS NOT NULL) THEN
        RAISE EXCEPTION 'Owner funding % is improperly reused by a loan repayment', p_id;
    END IF;
END;
$$;

CREATE FUNCTION sf_assert_owner_balance(p_id INTEGER) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    loan_exists BOOLEAN;
    balance NUMERIC(14,2);
BEGIN
    SELECT TRUE INTO loan_exists FROM owner_loans WHERE id = p_id FOR UPDATE;
    IF NOT FOUND THEN RETURN; END IF;
    SELECT COALESCE(SUM(CASE WHEN transaction_type='OWNER_FUNDED' THEN amount ELSE -amount END),0)
      INTO balance FROM owner_loan_transactions WHERE owner_loan_id = p_id;
    IF balance < 0 THEN
        RAISE EXCEPTION 'Owner loan % has negative outstanding balance %', p_id, balance;
    END IF;
END;
$$;

CREATE FUNCTION sf_assert_loan_repayment(p_id INTEGER) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    r loan_repayments%ROWTYPE;
    f financial_transactions%ROWTYPE;
    o owner_loan_transactions%ROWTYPE;
BEGIN
    SELECT * INTO r FROM loan_repayments WHERE id = p_id;
    IF NOT FOUND THEN RETURN; END IF;
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

CREATE FUNCTION sf_assert_business_loan(p_id INTEGER) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    l business_loans%ROWTYPE;
    repaid NUMERIC(14,2);
BEGIN
    SELECT * INTO l FROM business_loans WHERE id = p_id FOR UPDATE;
    IF NOT FOUND THEN RETURN; END IF;
    SELECT COALESCE(SUM(amount),0) INTO repaid FROM loan_repayments WHERE loan_id = p_id;
    IF repaid > l.original_amount THEN
        RAISE EXCEPTION 'Business loan % over-repaid: % > %', p_id, repaid, l.original_amount;
    END IF;
    IF l.status = 'COMPLETED' AND repaid <> l.original_amount THEN
        RAISE EXCEPTION 'Business loan % cannot be COMPLETED before full repayment', p_id;
    END IF;
END;
$$;

CREATE FUNCTION sf_assert_employment(p_id INTEGER) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    e driver_employments%ROWTYPE;
BEGIN
    SELECT * INTO e FROM driver_employments WHERE id = p_id;
    IF NOT FOUND THEN RETURN; END IF;
    IF EXISTS (
        SELECT 1 FROM driver_assignments a WHERE a.employment_id = p_id
          AND (a.start_date < e.start_date
               OR (e.end_date IS NOT NULL AND (a.end_date IS NULL OR a.end_date > e.end_date))
               OR (a.status = 'ACTIVE' AND e.status <> 'ACTIVE'))
    ) THEN
        RAISE EXCEPTION 'Employment % conflicts with its bus assignment dates/status', p_id;
    END IF;
END;
$$;

CREATE FUNCTION sf_assert_maintenance(p_id INTEGER) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    m maintenance%ROWTYPE;
    e expenses%ROWTYPE;
BEGIN
    SELECT * INTO m FROM maintenance WHERE id = p_id;
    IF NOT FOUND OR m.expense_id IS NULL THEN RETURN; END IF;
    SELECT * INTO e FROM expenses WHERE id = m.expense_id;
    IF e.scope = 'BUS' AND e.bus_id <> m.bus_id THEN
        RAISE EXCEPTION 'Maintenance % is linked to expense belonging to another bus', p_id;
    END IF;
    IF e.scope = 'MULTI_BUS' AND NOT EXISTS (
        SELECT 1 FROM expense_allocations a WHERE a.expense_id = e.id AND a.bus_id = m.bus_id
    ) THEN
        RAISE EXCEPTION 'Maintenance % is not included in its linked multi-bus expense', p_id;
    END IF;
    -- Deliberately do NOT require maintenance.total_cost=expense.amount:
    -- one maintenance job can incur multiple/partial/estimated expenses.
END;
$$;

CREATE FUNCTION sf_assert_ledger(p_id INTEGER) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    f financial_transactions%ROWTYPE;
    x RECORD;
BEGIN
    SELECT * INTO f FROM financial_transactions WHERE id = p_id;
    IF NOT FOUND THEN RETURN; END IF;
    IF f.transfer_id IS NOT NULL THEN
        PERFORM sf_assert_transfer(f.transfer_id);
    END IF;
    FOR x IN SELECT id FROM expenses WHERE financial_transaction_id = p_id LOOP
        PERFORM sf_assert_expense(x.id);
    END LOOP;
    FOR x IN SELECT id FROM remittance_collections WHERE financial_transaction_id = p_id LOOP
        PERFORM sf_assert_collection(x.id);
    END LOOP;
    FOR x IN SELECT id FROM driver_advances WHERE financial_transaction_id = p_id LOOP
        PERFORM sf_assert_advance(x.id);
    END LOOP;
    FOR x IN SELECT id FROM driver_salaries WHERE financial_transaction_id = p_id LOOP
        PERFORM sf_assert_salary(x.id);
    END LOOP;
    FOR x IN SELECT id FROM loan_repayments WHERE financial_transaction_id = p_id LOOP
        PERFORM sf_assert_loan_repayment(x.id);
    END LOOP;
    FOR x IN SELECT id FROM owner_loan_transactions WHERE financial_transaction_id = p_id LOOP
        PERFORM sf_assert_owner_loan_transaction(x.id);
    END LOOP;

    -- One payment cannot simultaneously settle different primary obligations.
    -- An expense row may *also* describe its category, without debiting twice.
    IF (
      (SELECT COUNT(*) FROM remittance_collections WHERE financial_transaction_id = p_id) +
      (SELECT COUNT(*) FROM driver_advances WHERE financial_transaction_id = p_id) +
      (SELECT COUNT(*) FROM driver_salaries WHERE financial_transaction_id = p_id) +
      (SELECT COUNT(*) FROM loan_repayments WHERE financial_transaction_id = p_id) +
      (SELECT COUNT(*) FROM owner_loan_transactions WHERE financial_transaction_id = p_id)
    ) > 1 THEN
        RAISE EXCEPTION 'Ledger entry % is linked to multiple primary business events', p_id;
    END IF;

    -- Keep specialized ledger entry types from existing without their owning record.
    IF (f.transaction_type = 'CASHING' AND NOT EXISTS
           (SELECT 1 FROM remittance_collections WHERE financial_transaction_id = p_id))
       OR (f.transaction_type = 'DRIVER_ADVANCE' AND NOT EXISTS
           (SELECT 1 FROM driver_advances WHERE financial_transaction_id = p_id))
       OR (f.transaction_type = 'DRIVER_SALARY' AND NOT EXISTS
           (SELECT 1 FROM driver_salaries WHERE financial_transaction_id = p_id))
       OR (f.transaction_type = 'LOAN_REPAYMENT' AND NOT EXISTS
           (SELECT 1 FROM loan_repayments WHERE financial_transaction_id = p_id))
       OR (f.transaction_type = 'OWNER_LOAN' AND NOT EXISTS
           (SELECT 1 FROM owner_loan_transactions WHERE financial_transaction_id = p_id))
       OR (f.transaction_type = 'OWNER_LOAN_REPAYMENT' AND NOT EXISTS
           (SELECT 1 FROM owner_loan_transactions WHERE financial_transaction_id = p_id))
       OR (f.transaction_type IN ('EXPENSE','OWNER_DRAWING') AND NOT EXISTS
           (SELECT 1 FROM expenses WHERE financial_transaction_id = p_id)) THEN
        RAISE EXCEPTION 'Financial transaction % (%) is missing its business record',
            p_id, f.transaction_type;
    END IF;
END;
$$;

-- Historical rate windows for the same rate type may not overlap.
CREATE FUNCTION sf_assert_rate(p_id INTEGER) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE r cashing_rates%ROWTYPE;
BEGIN
    SELECT * INTO r FROM cashing_rates WHERE id = p_id;
    IF NOT FOUND THEN RETURN; END IF;
    IF EXISTS (
      SELECT 1 FROM cashing_rates x WHERE x.id <> r.id AND x.rate_type = r.rate_type
        AND x.effective_from <= COALESCE(r.effective_to, 'infinity'::date)
        AND r.effective_from <= COALESCE(x.effective_to, 'infinity'::date)
    ) THEN
      RAISE EXCEPTION 'Cashing rate % overlaps another effective date window', p_id;
    END IF;
END;
$$;

-- Active fee bands must not overlap; deactivated historical rows may overlap.
CREATE FUNCTION sf_assert_fee_rule(p_id INTEGER) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE r transfer_fee_rules%ROWTYPE;
BEGIN
    SELECT * INTO r FROM transfer_fee_rules WHERE id = p_id;
    IF NOT FOUND OR NOT r.active THEN RETURN; END IF;
    IF EXISTS (
      SELECT 1 FROM transfer_fee_rules x
      WHERE x.id <> r.id AND x.active AND x.transfer_type = r.transfer_type
        AND x.minimum_amount <= COALESCE(r.maximum_amount, 999999999999::NUMERIC)
        AND r.minimum_amount <= COALESCE(x.maximum_amount, 999999999999::NUMERIC)
    ) THEN
      RAISE EXCEPTION 'Fee rule % overlaps another active transfer fee band', p_id;
    END IF;
END;
$$;

-- 3. One deferred trigger dispatcher for every cross-table invariant.
CREATE FUNCTION sf_integrity_deferred() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
DECLARE
    old_ledger_id INTEGER;
    new_ledger_id INTEGER;
BEGIN
    -- Validate both old and new relationships on an UPDATE, to prevent
    -- changing an FK from leaving the previous ledger/parent in an invalid state.
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
            PERFORM sf_assert_business_loan(OLD.loan_id);
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
            PERFORM sf_assert_business_loan(NEW.loan_id);
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
    RETURN NULL; -- AFTER triggers ignore returned row
END;
$$;

-- Deferred constraint triggers validate only at transaction end. For scenarios
-- spanning multiple tables, INSERT ALL related rows before COMMIT.
DO $$
DECLARE
    tab TEXT;
BEGIN
    FOREACH tab IN ARRAY ARRAY[
        'financial_transactions','transfers','expenses','expense_allocations',
        'remittance_collections','remittances',
        'driver_advances','driver_deductions','driver_salaries',
        'salary_advance_recoveries','salary_deduction_allocations',
        'owner_loan_transactions','loan_repayments','business_loans',
        'driver_assignments','driver_employments','maintenance',
        'cashing_rates','transfer_fee_rules'
    ] LOOP
        EXECUTE format(
          'CREATE CONSTRAINT TRIGGER %I AFTER INSERT OR UPDATE OR DELETE ON %I '
          || 'DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION sf_integrity_deferred()',
          'sf_integrity_' || tab, tab
        );
    END LOOP;
END;
$$;

-- Tracked account type is historical identity, not an editable label.
CREATE FUNCTION sf_preserve_account_type() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.account_type IS DISTINCT FROM NEW.account_type THEN
        RAISE EXCEPTION 'Account type cannot change; create another account instead';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER sf_preserve_account_type
BEFORE UPDATE OF account_type ON financial_accounts
FOR EACH ROW EXECUTE FUNCTION sf_preserve_account_type();

-- 4. Every modified record with an updated_at column receives an updated timestamp.
CREATE FUNCTION sf_touch_updated_at() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DO $$
DECLARE
    tab RECORD;
BEGIN
    FOR tab IN
        SELECT c.table_schema, c.table_name
        FROM information_schema.columns c
        WHERE c.table_schema = 'public' AND c.column_name = 'updated_at'
          AND c.table_name IN (SELECT table_name FROM information_schema.tables
                               WHERE table_schema = 'public' AND table_type = 'BASE TABLE')
    LOOP
        EXECUTE format(
          'CREATE TRIGGER sf_touch_updated_at BEFORE UPDATE ON %I.%I '
          || 'FOR EACH ROW EXECUTE FUNCTION sf_touch_updated_at()',
          tab.table_schema, tab.table_name
        );
    END LOOP;
END;
$$;

COMMIT;
