CREATE TABLE buses (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    registration_number VARCHAR(20) NOT NULL UNIQUE,

    route_id INTEGER NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',

    date_acquired DATE,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT buses_route_fk
        FOREIGN KEY (route_id)
        REFERENCES routes(id),

    CONSTRAINT buses_status_check
        CHECK (status IN ('ACTIVE', 'INACTIVE'))
);