CREATE TABLE transfer_fee_rules (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    transfer_type VARCHAR(30) NOT NULL,

    minimum_amount NUMERIC(12,2) NOT NULL,
    maximum_amount NUMERIC(12,2),

    fee_amount NUMERIC(12,2) NOT NULL,

    active BOOLEAN NOT NULL DEFAULT TRUE,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT transfer_fee_rules_type_check
        CHECK (
            transfer_type IN (
                'AIRTEL_TO_BANK',
                'AIRTEL_TO_AIRTEL'
            )
        ),

    CONSTRAINT transfer_fee_rules_amounts_check
        CHECK (
            minimum_amount >= 0
            AND (maximum_amount IS NULL OR maximum_amount >= minimum_amount)
        ),

    CONSTRAINT transfer_fee_rules_fee_check
        CHECK (fee_amount >= 0)
);


CREATE TABLE transfers (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    transfer_date DATE NOT NULL,

    source_account_id INTEGER NOT NULL,
    destination_account_id INTEGER,

    transfer_type VARCHAR(30) NOT NULL,

    amount NUMERIC(12,2) NOT NULL,

    fee_amount NUMERIC(12,2) NOT NULL DEFAULT 0.00,

    fee_rule_id INTEGER,

    recipient_description VARCHAR(150),

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT transfers_source_account_fk
        FOREIGN KEY (source_account_id)
        REFERENCES financial_accounts(id),

    CONSTRAINT transfers_destination_account_fk
        FOREIGN KEY (destination_account_id)
        REFERENCES financial_accounts(id),

    CONSTRAINT transfers_fee_rule_fk
        FOREIGN KEY (fee_rule_id)
        REFERENCES transfer_fee_rules(id),

    CONSTRAINT transfers_type_check
        CHECK (
            transfer_type IN (
                'INTERNAL',
                'AIRTEL_TO_BANK',
                'AIRTEL_TO_AIRTEL'
            )
        ),

    CONSTRAINT transfers_amount_check
        CHECK (amount > 0),

    CONSTRAINT transfers_fee_check
        CHECK (fee_amount >= 0),

    CONSTRAINT transfers_different_accounts_check
        CHECK (
            destination_account_id IS NULL
            OR source_account_id <> destination_account_id
        )
);
