BEGIN;

-- Make the current default rates available from the clean reporting
-- baseline so October 2026 backfill can calculate expected cashing.
-- The active current rate windows are preserved.

INSERT INTO cashing_rates (
    rate_type,
    amount,
    active,
    effective_from,
    effective_to,
    notes
)
SELECT
    cr.rate_type,
    cr.amount,
    FALSE,
    DATE '2026-10-01',
    cr.effective_from - 1,
    'Historical baseline rate for October 2026 backfill'
FROM cashing_rates cr
WHERE cr.active = TRUE
  AND cr.effective_from > DATE '2026-10-01'
  AND NOT EXISTS (
      SELECT 1
      FROM cashing_rates existing
      WHERE existing.rate_type = cr.rate_type
        AND existing.effective_from = DATE '2026-10-01'
        AND existing.effective_to = cr.effective_from - 1
  );

COMMIT;

