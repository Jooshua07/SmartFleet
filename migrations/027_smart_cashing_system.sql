BEGIN;

-- =========================================================
-- STEP 4: SMART CASHING SYSTEM
--
-- Preserve the existing collection/remittance ledger model while
-- adding coverage dates, allocation provenance, unallocated
-- differences and confirmed outstanding obligations.
-- =========================================================

ALTER TABLE remittance_collections
    ADD COLUMN coverage_start DATE,
    ADD COLUMN coverage_end DATE,
    ADD COLUMN expected_total NUMERIC(12,2) NOT NULL DEFAULT 0,
    ADD COLUMN unallocated_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    ADD COLUMN cashing_mode VARCHAR(30) NOT NULL DEFAULT 'DIRECT',
    ADD COLUMN difference_classification VARCHAR(40) NOT NULL DEFAULT 'MATCHED';

ALTER TABLE remittances
    ADD COLUMN allocation_provenance VARCHAR(40) NOT NULL DEFAULT 'CONFIRMED_ACTUAL',
    ADD COLUMN difference_classification VARCHAR(40) NOT NULL DEFAULT 'MATCHED',
    ADD COLUMN worked_days_adjusted BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN sunday_worked BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE remittance_collections
    ADD CONSTRAINT remittance_collections_coverage_dates_check
        CHECK (
            coverage_start IS NULL
            OR coverage_end IS NULL
            OR coverage_end >= coverage_start
        ),
    ADD CONSTRAINT remittance_collections_expected_total_check
        CHECK (expected_total >= 0),
    ADD CONSTRAINT remittance_collections_mode_check
        CHECK (cashing_mode IN ('DIRECT', 'STANDARD', 'ADJUSTED')),
    ADD CONSTRAINT remittance_collections_difference_check
        CHECK (
            difference_classification IN (
                'MATCHED',
                'UNKNOWN_DIFFERENCE',
                'SURPLUS',
                'REDUCED_WORKDAYS',
                'UNDERPERFORMANCE',
                'CONFIRMED_UNPAID_OBLIGATION'
            )
        );

ALTER TABLE remittances
    ADD CONSTRAINT remittances_allocation_provenance_check
        CHECK (
            allocation_provenance IN (
                'CONFIRMED_ACTUAL',
                'ESTIMATED_STANDARD',
                'MANUAL_ADJUSTMENT'
            )
        ),
    ADD CONSTRAINT remittances_difference_classification_check
        CHECK (
            difference_classification IN (
                'MATCHED',
                'UNKNOWN_DIFFERENCE',
                'SURPLUS',
                'REDUCED_WORKDAYS',
                'UNDERPERFORMANCE',
                'CONFIRMED_UNPAID_OBLIGATION'
            )
        );

CREATE TABLE cashing_obligations (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    collection_id INTEGER NOT NULL,
    remittance_id INTEGER NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    outstanding_amount NUMERIC(12,2) NOT NULL,
    responsible_party_type VARCHAR(30) NOT NULL,
    responsible_party_name VARCHAR(150) NOT NULL,
    driver_id INTEGER,
    recognized_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT cashing_obligations_collection_fk
        FOREIGN KEY (collection_id)
        REFERENCES remittance_collections(id),

    CONSTRAINT cashing_obligations_remittance_fk
        FOREIGN KEY (remittance_id)
        REFERENCES remittances(id),

    CONSTRAINT cashing_obligations_driver_fk
        FOREIGN KEY (driver_id)
        REFERENCES drivers(id),

    CONSTRAINT cashing_obligations_amount_check
        CHECK (amount > 0),

    CONSTRAINT cashing_obligations_outstanding_check
        CHECK (outstanding_amount >= 0 AND outstanding_amount <= amount),

    CONSTRAINT cashing_obligations_party_type_check
        CHECK (responsible_party_type IN ('HEAD_DRIVER', 'ASSIGNED_DRIVER', 'OTHER')),

    CONSTRAINT cashing_obligations_status_check
        CHECK (status IN ('OPEN', 'PARTIALLY_SETTLED', 'SETTLED', 'VOID'))
);

CREATE INDEX idx_cashing_obligations_collection
ON cashing_obligations (collection_id);

CREATE INDEX idx_cashing_obligations_status
ON cashing_obligations (status);

CREATE TABLE cashing_obligation_payments (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    obligation_id INTEGER NOT NULL,
    payment_date DATE NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    financial_account_id INTEGER NOT NULL,
    financial_transaction_id INTEGER NOT NULL,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT cashing_obligation_payments_obligation_fk
        FOREIGN KEY (obligation_id)
        REFERENCES cashing_obligations(id),

    CONSTRAINT cashing_obligation_payments_account_fk
        FOREIGN KEY (financial_account_id)
        REFERENCES financial_accounts(id),

    CONSTRAINT cashing_obligation_payments_transaction_fk
        FOREIGN KEY (financial_transaction_id)
        REFERENCES financial_transactions(id),

    CONSTRAINT cashing_obligation_payments_amount_check
        CHECK (amount > 0)
);

CREATE OR REPLACE FUNCTION sf_assert_collection(p_id INTEGER) RETURNS VOID
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
    IF child_total + c.unallocated_amount <> c.total_amount THEN
        RAISE EXCEPTION 'Collection % total % differs from allocations % plus unallocated %',
            p_id, c.total_amount, child_total, c.unallocated_amount;
    END IF;
END;
$$;

DO $$
DECLARE
    tab TEXT;
BEGIN
    FOREACH tab IN ARRAY ARRAY[
        'cashing_obligations'
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

