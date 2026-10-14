BEGIN;
ALTER TABLE maintenance ADD COLUMN transport_cost NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (transport_cost >= 0);
ALTER TABLE maintenance ADD COLUMN is_servicing BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE maintenance ADD COLUMN payment_date DATE;
ALTER TABLE maintenance DROP COLUMN total_cost;
ALTER TABLE maintenance ADD COLUMN total_cost NUMERIC(12,2) GENERATED ALWAYS AS (parts_cost + labour_cost + transport_cost) STORED;
CREATE UNIQUE INDEX maintenance_servicing_expense_unique ON maintenance(expense_id) WHERE is_servicing AND expense_id IS NOT NULL;
INSERT INTO expense_categories(name) VALUES ('Servicing') ON CONFLICT(name) DO NOTHING;
INSERT INTO maintenance_schedules(bus_id, schedule_name, interval_days, next_due_date, notes)
SELECT b.id, 'Servicing', 35, DATE '2026-10-18', 'Owner-confirmed initial servicing date'
FROM buses b
WHERE b.registration_number IN ('AIF 9681','AIG 5301','AIH 2715')
  AND NOT EXISTS (SELECT 1 FROM maintenance_schedules ms WHERE ms.bus_id=b.id)
  AND NOT EXISTS (SELECT 1 FROM maintenance m WHERE m.bus_id=b.id AND m.status='COMPLETED');
COMMIT;
