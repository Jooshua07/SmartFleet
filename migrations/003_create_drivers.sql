CREATE TABLE drivers (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    full_name VARCHAR(150) NOT NULL,

    phone VARCHAR(30),

    address TEXT,

    next_of_kin_name VARCHAR(150),

    next_of_kin_phone VARCHAR(30),

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
