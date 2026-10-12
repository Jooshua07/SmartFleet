BEGIN;

-- =========================================================
-- STEP 3: FLEET HISTORY AND SAFE EDITING
--
-- Additive history storage for bus status and route changes.
-- Current buses.status and buses.route_id remain the quick current
-- state used by existing screens.
-- =========================================================

CREATE TABLE bus_status_history (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bus_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT bus_status_history_bus_fk
        FOREIGN KEY (bus_id)
        REFERENCES buses(id),

    CONSTRAINT bus_status_history_status_check
        CHECK (status IN ('ACTIVE', 'INACTIVE')),

    CONSTRAINT bus_status_history_dates_check
        CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

CREATE UNIQUE INDEX unique_current_bus_status_history
ON bus_status_history (bus_id)
WHERE effective_to IS NULL;

CREATE INDEX idx_bus_status_history_lookup
ON bus_status_history (bus_id, effective_from, effective_to);

CREATE TABLE bus_route_history (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bus_id INTEGER NOT NULL,
    route_id INTEGER NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT bus_route_history_bus_fk
        FOREIGN KEY (bus_id)
        REFERENCES buses(id),

    CONSTRAINT bus_route_history_route_fk
        FOREIGN KEY (route_id)
        REFERENCES routes(id),

    CONSTRAINT bus_route_history_dates_check
        CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

CREATE UNIQUE INDEX unique_current_bus_route_history
ON bus_route_history (bus_id)
WHERE effective_to IS NULL;

CREATE INDEX idx_bus_route_history_lookup
ON bus_route_history (bus_id, effective_from, effective_to);

INSERT INTO bus_status_history (bus_id, status, effective_from, reason)
SELECT
    b.id,
    b.status,
    COALESCE(b.date_acquired, DATE '2026-10-01'),
    'Initial status history created during Step 3 migration'
FROM buses b;

INSERT INTO bus_route_history (bus_id, route_id, effective_from, notes)
SELECT
    b.id,
    b.route_id,
    COALESCE(b.date_acquired, DATE '2026-10-01'),
    'Initial route history created during Step 3 migration'
FROM buses b;

DO $$
DECLARE
    tab TEXT;
BEGIN
    FOREACH tab IN ARRAY ARRAY[
        'bus_status_history',
        'bus_route_history'
    ] LOOP
        EXECUTE format(
          'CREATE TRIGGER sf_touch_updated_at BEFORE UPDATE ON public.%I '
          || 'FOR EACH ROW EXECUTE FUNCTION sf_touch_updated_at()',
          tab
        );
    END LOOP;
END;
$$;

COMMIT;

