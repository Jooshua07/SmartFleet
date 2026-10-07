CREATE TABLE expense_categories (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    name VARCHAR(100) NOT NULL UNIQUE,

    active BOOLEAN NOT NULL DEFAULT TRUE,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE expenses (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    expense_date DATE NOT NULL,

    category_id INTEGER NOT NULL,

    amount NUMERIC(12,2) NOT NULL,

    description TEXT NOT NULL,

    scope VARCHAR(20) NOT NULL,

    bus_id INTEGER,

    payment_source VARCHAR(30) NOT NULL,

    financial_account_id INTEGER,

    financial_transaction_id INTEGER,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT expenses_category_fk
        FOREIGN KEY (category_id)
        REFERENCES expense_categories(id),

    CONSTRAINT expenses_bus_fk
        FOREIGN KEY (bus_id)
        REFERENCES buses(id),

    CONSTRAINT expenses_financial_account_fk
        FOREIGN KEY (financial_account_id)
        REFERENCES financial_accounts(id),

    CONSTRAINT expenses_financial_transaction_fk
        FOREIGN KEY (financial_transaction_id)
        REFERENCES financial_transactions(id),

    CONSTRAINT expenses_amount_check
        CHECK (amount > 0),

    CONSTRAINT expenses_scope_check
        CHECK (scope IN ('BUS', 'MULTI_BUS', 'GENERAL')),

    CONSTRAINT expenses_payment_source_check
        CHECK (
            payment_source IN (
                'BUSINESS_ACCOUNT',
                'OWNER_PERSONAL'
            )
        ),

    CONSTRAINT expenses_bus_scope_check
        CHECK (
            (scope = 'BUS' AND bus_id IS NOT NULL)
            OR
            (scope IN ('MULTI_BUS', 'GENERAL') AND bus_id IS NULL)
        ),

    CONSTRAINT expenses_payment_account_check
        CHECK (
            (payment_source = 'BUSINESS_ACCOUNT'
                AND financial_account_id IS NOT NULL)
            OR
            (payment_source = 'OWNER_PERSONAL'
                AND financial_account_id IS NULL)
        )
);
