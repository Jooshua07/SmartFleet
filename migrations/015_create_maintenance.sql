BEGIN;

-- =========================================================
-- 1. MAINTENANCE RECORDS
-- Records actual maintenance/repair work performed on a bus.
-- =========================================================

CREATE TABLE maintenance (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    bus_id INTEGER NOT NULL,

    maintenance_type VARCHAR(20) NOT NULL,

    description TEXT NOT NULL,

    reported_date DATE NOT NULL,
    start_date DATE,
    completed_date DATE,

    status VARCHAR(20) NOT NULL DEFAULT 'REPORTED',

    mechanic VARCHAR(150),

    parts_cost NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    labour_cost NUMERIC(12,2) NOT NULL DEFAULT 0.00,

    total_cost NUMERIC(12,2) GENERATED ALWAYS AS (
        parts_cost + labour_cost
    ) STORED,

    expense_id INTEGER,

    downtime_start DATE,
    downtime_end DATE,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT maintenance_bus_fk
        FOREIGN KEY (bus_id)
        REFERENCES buses(id),

    CONSTRAINT maintenance_expense_fk
        FOREIGN KEY (expense_id)
        REFERENCES expenses(id),

    CONSTRAINT maintenance_type_check
        CHECK (
            maintenance_type IN (
                'PLANNED',
                'UNPLANNED'
            )
        ),

    CONSTRAINT maintenance_status_check
        CHECK (
            status IN (
                'REPORTED',
                'IN_PROGRESS',
                'COMPLETED',
                'CANCELLED'
            )
        ),

    CONSTRAINT maintenance_parts_cost_check
        CHECK (parts_cost >= 0),

    CONSTRAINT maintenance_labour_cost_check
        CHECK (labour_cost >= 0),

    CONSTRAINT maintenance_dates_check
        CHECK (
            completed_date IS NULL
            OR start_date IS NULL
            OR completed_date >= start_date
        ),

    CONSTRAINT maintenance_downtime_check
        CHECK (
            downtime_end IS NULL
            OR downtime_start IS NULL
            OR downtime_end >= downtime_start
        )
);


-- =========================================================
-- 2. MAINTENANCE SCHEDULE
-- Tracks recurring maintenance timing for each bus.
-- =========================================================

CREATE TABLE maintenance_schedules (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    bus_id INTEGER NOT NULL,

    schedule_name VARCHAR(100) NOT NULL,

    interval_days INTEGER NOT NULL DEFAULT 35,

    last_completed_date DATE,

    next_due_date DATE,

    active BOOLEAN NOT NULL DEFAULT TRUE,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT maintenance_schedules_bus_fk
        FOREIGN KEY (bus_id)
        REFERENCES buses(id),

    CONSTRAINT maintenance_schedules_interval_check
        CHECK (interval_days > 0),

    CONSTRAINT maintenance_schedules_bus_name_unique
        UNIQUE (bus_id, schedule_name)
);

COMMIT;
