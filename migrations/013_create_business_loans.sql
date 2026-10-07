BEGIN;

CREATE TABLE business_loans (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    loan_name VARCHAR(150) NOT NULL,
    lender VARCHAR(150) NOT NULL,

    original_amount NUMERIC(12,2) NOT NULL,

    start_date DATE NOT NULL,

    term_months INTEGER,

    default_monthly_repayment NUMERIC(12,2) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT business_loans_amount_check
        CHECK (original_amount > 0),

    CONSTRAINT business_loans_repayment_check
        CHECK (default_monthly_repayment > 0),

    CONSTRAINT business_loans_term_check
        CHECK (term_months IS NULL OR term_months > 0),

    CONSTRAINT business_loans_status_check
        CHECK (status IN ('ACTIVE', 'COMPLETED', 'INACTIVE'))
);


CREATE TABLE loan_repayments (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    loan_id INTEGER NOT NULL,

    repayment_date DATE NOT NULL,

    amount NUMERIC(12,2) NOT NULL,

    payment_source VARCHAR(30) NOT NULL,

    financial_transaction_id INTEGER,

    owner_loan_transaction_id INTEGER,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT loan_repayments_loan_fk
        FOREIGN KEY (loan_id)
        REFERENCES business_loans(id),

    CONSTRAINT loan_repayments_financial_transaction_fk
        FOREIGN KEY (financial_transaction_id)
        REFERENCES financial_transactions(id),

    CONSTRAINT loan_repayments_owner_loan_transaction_fk
        FOREIGN KEY (owner_loan_transaction_id)
        REFERENCES owner_loan_transactions(id),

    CONSTRAINT loan_repayments_amount_check
        CHECK (amount > 0),

    CONSTRAINT loan_repayments_source_check
        CHECK (
            payment_source IN (
                'BUSINESS_ACCOUNT',
                'OWNER_PERSONAL'
            )
        ),

    CONSTRAINT loan_repayments_source_link_check
        CHECK (
            (
                payment_source = 'BUSINESS_ACCOUNT'
                AND financial_transaction_id IS NOT NULL
                AND owner_loan_transaction_id IS NULL
            )
            OR
            (
                payment_source = 'OWNER_PERSONAL'
                AND financial_transaction_id IS NULL
                AND owner_loan_transaction_id IS NOT NULL
            )
        )
);

COMMIT;
