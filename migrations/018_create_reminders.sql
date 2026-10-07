BEGIN;

-- =========================================================
-- REMINDERS
-- Generic reminder system for operational and financial
-- events that SmartFleet needs to surface to the user.
-- =========================================================

CREATE TABLE reminders (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    reminder_type VARCHAR(30) NOT NULL,

    title VARCHAR(150) NOT NULL,
    description TEXT,

    due_date DATE NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',

    -- Optional links to the business record that caused
    -- or relates to the reminder.
    bus_id INTEGER,
    maintenance_schedule_id INTEGER,
    business_loan_id INTEGER,

    completed_date DATE,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT reminders_bus_fk
        FOREIGN KEY (bus_id)
        REFERENCES buses(id),

    CONSTRAINT reminders_maintenance_schedule_fk
        FOREIGN KEY (maintenance_schedule_id)
        REFERENCES maintenance_schedules(id),

    CONSTRAINT reminders_business_loan_fk
        FOREIGN KEY (business_loan_id)
        REFERENCES business_loans(id),

    CONSTRAINT reminders_type_check
        CHECK (
            reminder_type IN (
                'MAINTENANCE',
                'LOAN_REPAYMENT',
                'DOCUMENT_EXPIRY',
                'REGULATORY',
                'OTHER'
            )
        ),

    CONSTRAINT reminders_status_check
        CHECK (
            status IN (
                'PENDING',
                'COMPLETED',
                'DISMISSED'
            )
        ),

    CONSTRAINT reminders_completion_check
        CHECK (
            (status = 'COMPLETED' AND completed_date IS NOT NULL)
            OR
            (status IN ('PENDING', 'DISMISSED'))
        )
);

COMMIT;
