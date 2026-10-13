BEGIN;

CREATE TABLE correction_audit (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    corrected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    area VARCHAR(50) NOT NULL,
    record_type VARCHAR(80) NOT NULL,
    record_id INTEGER NOT NULL,
    action VARCHAR(40) NOT NULL,
    reason TEXT NOT NULL,
    snapshot JSONB NOT NULL
);

CREATE INDEX correction_audit_corrected_at_idx
    ON correction_audit(corrected_at DESC);

COMMIT;
