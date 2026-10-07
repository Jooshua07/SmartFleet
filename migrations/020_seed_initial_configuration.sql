BEGIN;

-- =========================================================
-- 1. FINANCIAL ACCOUNTS
-- These represent the business money locations currently
-- tracked by SmartFleet.
--
-- Opening balances remain 0 for now.
-- Real opening balances should be established during
-- business-data setup/import.
-- =========================================================

INSERT INTO financial_accounts (
    name,
    account_type,
    opening_balance,
    notes
)
VALUES
    (
        'Cash',
        'CASH',
        0.00,
        'Physical business cash'
    ),
    (
        'Airtel Money',
        'AIRTEL_MONEY',
        0.00,
        'Tracks only the business portion of the Airtel Money balance'
    ),
    (
        'Bank',
        'BANK',
        0.00,
        'Primary business bank account'
    );


-- =========================================================
-- 2. CURRENT CASHING SCHEDULE
--
-- 1 = Monday
-- 2 = Tuesday
-- 3 = Wednesday
-- 4 = Thursday
-- 5 = Friday
-- 6 = Saturday
-- 7 = Sunday
--
-- These are configurable business settings.
-- They do NOT prevent cashing on another day.
-- =========================================================

INSERT INTO cashing_schedules (
    day_of_week,
    active,
    notes
)
VALUES
    (
        4,
        TRUE,
        'Current normal Thursday cashing day'
    ),
    (
        7,
        TRUE,
        'Current normal Sunday cashing day'
    );


COMMIT;
