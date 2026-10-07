CREATE TABLE financial_transactions (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    account_id INTEGER NOT NULL,

    transaction_date DATE NOT NULL,

    transaction_type VARCHAR(40) NOT NULL,

    direction VARCHAR(10) NOT NULL,

    amount NUMERIC(12,2) NOT NULL,

    description TEXT,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT financial_transactions_account_fk
        FOREIGN KEY (account_id)
        REFERENCES financial_accounts(id),

    CONSTRAINT financial_transactions_direction_check
        CHECK (direction IN ('IN', 'OUT')),

    CONSTRAINT financial_transactions_amount_check
        CHECK (amount > 0),

    CONSTRAINT financial_transactions_type_check
        CHECK (
            transaction_type IN (
                'CASHING',
                'EXPENSE',
                'TRANSFER',
                'TRANSFER_FEE',
                'OWNER_LOAN',
                'OWNER_LOAN_REPAYMENT',
                'OWNER_DRAWING',
                'LOAN_RECEIVED',
                'LOAN_REPAYMENT',
                'OTHER'
            )
        )
);
