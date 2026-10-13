BEGIN;

-- Step 2 money workflows: allow loan repayment terms to be unknown
-- while keeping the original loan principal required.
ALTER TABLE business_loans
    ALTER COLUMN default_monthly_repayment DROP NOT NULL;

ALTER TABLE business_loans
    DROP CONSTRAINT business_loans_repayment_check;

ALTER TABLE business_loans
    ADD CONSTRAINT business_loans_repayment_check
        CHECK (default_monthly_repayment IS NULL OR default_monthly_repayment > 0);

INSERT INTO business_settings (setting_key, setting_value, setting_type, notes)
VALUES (
    'DRIVER_ADVANCE_LIMIT',
    '1000.00',
    'NUMBER',
    'Maximum total outstanding salary advance allowed per driver employment'
)
ON CONFLICT (setting_key) DO NOTHING;

COMMIT;
