-- Apply ONLY to the isolated Flask development/test databases, using the guarded setup script.
-- Existing business tables, calculations and constraints are unchanged.
CREATE TABLE web_commands (
    actor TEXT NOT NULL,
    command_key UUID NOT NULL,
    action TEXT NOT NULL,
    payload_hash CHAR(64) NOT NULL,
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (actor, command_key)
);

CREATE TABLE web_command_audit (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor TEXT NOT NULL,
    command_key UUID NOT NULL,
    resource TEXT NOT NULL,
    reason TEXT NOT NULL CHECK (length(btrim(reason)) > 0),
    before_state JSONB NOT NULL,
    after_state JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (actor, command_key) REFERENCES web_commands (actor, command_key),
    UNIQUE (actor, command_key)
);
