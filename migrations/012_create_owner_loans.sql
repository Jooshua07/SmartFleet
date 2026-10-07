BEGIN;

CREATE TABLE owner_loans (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    name VARCHAR(100) NOT NULL,

    active BOOLEAN NOT NULL DEFAULT TRUE,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE owner_loan_transactions (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    owner_loan_id INTEGER NOT NULL,

    transaction_date DATE NOT NULL,

    transaction_type VARCHAR(20) NOT NULL,

    amount NUMERIC(12,2) NOT NULL,

    description TEXT NOT NULL,

    expense_id INTEGER,

    financial_transaction_id INTEGER,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT owner_loan_transactions_loan_fk
        FOREIGN KEY (owner_loan_id)
        REFERENCES owner_loans(id),

    CONSTRAINT owner_loan_transactions_expense_fk
        FOREIGN KEY (expense_id)
        REFERENCES expenses(id),

    CONSTRAINT owner_loan_transactions_financial_transaction_fk
        FOREIGN KEY (financial_transaction_id)
        REFERENCES financial_transactions(id),

    CONSTRAINT owner_loan_transactions_type_check
        CHECK (
            transaction_type IN (
                'OWNER_FUNDED',
                'REPAYMENT'
            )
        ),

    CONSTRAINT owner_loan_transactions_amount_check
        CHECK (amount > 0)
);


INSERT INTO owner_loans (name, notes)
VALUES (
    'Owner Loan Account',
    'Tracks personal money provided by the owner to fund business activities'
);

COMMIT;
