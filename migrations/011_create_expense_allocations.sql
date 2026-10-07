BEGIN;

CREATE TABLE expense_allocations (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    expense_id INTEGER NOT NULL,
    bus_id INTEGER NOT NULL,

    allocated_amount NUMERIC(12,2) NOT NULL,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT expense_allocations_expense_fk
        FOREIGN KEY (expense_id)
        REFERENCES expenses(id),

    CONSTRAINT expense_allocations_bus_fk
        FOREIGN KEY (bus_id)
        REFERENCES buses(id),

    CONSTRAINT expense_allocations_amount_check
        CHECK (allocated_amount > 0),

    CONSTRAINT expense_allocations_unique_bus
        UNIQUE (expense_id, bus_id)
);


INSERT INTO expense_categories (name, notes)
VALUES
    ('Maintenance', 'Repairs, servicing and maintenance-related costs'),
    ('Parts', 'Bus parts and replacement components'),
    ('Driver Salaries', 'Driver salary payments'),
    ('Driver Advances', 'Money advanced to drivers'),
    ('Transfer Fees', 'Bank and mobile money transfer charges'),
    ('Loan Repayments', 'Repayments of business loans'),
    ('Owner Drawings', 'Business money withdrawn by the owner for personal use'),
    ('Office & Administration', 'General administrative business expenses'),
    ('Other', 'Expenses that do not fit another category');

COMMIT;
