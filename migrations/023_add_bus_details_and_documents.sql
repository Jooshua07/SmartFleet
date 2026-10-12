BEGIN;

-- Add the practical bus details needed by the mobile Add Bus flow.
ALTER TABLE buses
    ADD COLUMN IF NOT EXISTS model VARCHAR(100),
    ADD COLUMN IF NOT EXISTS seating_capacity INTEGER,
    ADD COLUMN IF NOT EXISTS chassis_number VARCHAR(80);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'buses_seating_capacity_check'
    ) THEN
        ALTER TABLE buses
            ADD CONSTRAINT buses_seating_capacity_check
            CHECK (seating_capacity IS NULL OR seating_capacity > 0);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS bus_documents (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    bus_id INTEGER NOT NULL,

    document_type VARCHAR(40) NOT NULL,
    document_number VARCHAR(100),

    issue_date DATE,
    expiry_date DATE,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT bus_documents_bus_fk
        FOREIGN KEY (bus_id)
        REFERENCES buses(id),

    CONSTRAINT bus_documents_type_check
        CHECK (
            document_type IN (
                'INSURANCE',
                'ROAD_TAX',
                'FITNESS',
                'ROAD_SERVICE_LICENSE',
                'OTHER'
            )
        ),

    CONSTRAINT bus_documents_dates_check
        CHECK (
            expiry_date IS NULL
            OR issue_date IS NULL
            OR expiry_date >= issue_date
        )
);

CREATE INDEX IF NOT EXISTS idx_bus_documents_bus
ON bus_documents (bus_id);

CREATE INDEX IF NOT EXISTS idx_bus_documents_expiry
ON bus_documents (expiry_date)
WHERE expiry_date IS NOT NULL;

CREATE OR REPLACE FUNCTION sf_touch_updated_at() RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'sf_touch_updated_at_bus_documents'
          AND tgrelid = 'public.bus_documents'::regclass
    ) THEN
        CREATE TRIGGER sf_touch_updated_at_bus_documents
        BEFORE UPDATE ON bus_documents
        FOR EACH ROW EXECUTE FUNCTION sf_touch_updated_at();
    END IF;
END $$;

COMMIT;
