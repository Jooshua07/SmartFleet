CREATE TABLE driver_employments (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    driver_id INTEGER NOT NULL,

    start_date DATE NOT NULL,
    end_date DATE,

    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',

    monthly_salary NUMERIC(10,2) NOT NULL DEFAULT 2000.00,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT driver_employments_driver_fk
        FOREIGN KEY (driver_id)
        REFERENCES drivers(id),

    CONSTRAINT driver_employments_status_check
        CHECK (status IN ('ACTIVE', 'INACTIVE', 'TERMINATED')),

    CONSTRAINT driver_employments_salary_check
        CHECK (monthly_salary >= 0),

    CONSTRAINT driver_employments_dates_check
        CHECK (end_date IS NULL OR end_date >= start_date)
);