CREATE TABLE financial_accounts (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    name VARCHAR(100) NOT NULL UNIQUE,

    account_type VARCHAR(30) NOT NULL,

    opening_balance NUMERIC(12,2) NOT NULL DEFAULT 0.00,

    active BOOLEAN NOT NULL DEFAULT TRUE,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT financial_accounts_type_check
        CHECK (account_type IN ('CASH', 'AIRTEL_MONEY', 'BANK'))
);
