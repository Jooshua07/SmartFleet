CREATE TABLE driver_assignments (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    employment_id INTEGER NOT NULL,
    bus_id INTEGER NOT NULL,

    assignment_type VARCHAR(20) NOT NULL,

    start_date DATE NOT NULL,
    end_date DATE,

    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT driver_assignments_employment_fk
        FOREIGN KEY (employment_id)
        REFERENCES driver_employments(id),

    CONSTRAINT driver_assignments_bus_fk
        FOREIGN KEY (bus_id)
        REFERENCES buses(id),

    CONSTRAINT driver_assignments_type_check
        CHECK (assignment_type IN ('PERMANENT', 'TEMPORARY')),

    CONSTRAINT driver_assignments_status_check
        CHECK (status IN ('ACTIVE', 'ENDED')),

    CONSTRAINT driver_assignments_dates_check
        CHECK (end_date IS NULL OR end_date >= start_date)
);