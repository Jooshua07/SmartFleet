# Step 5: Help and controlled cleanup

## Starting evidence

- Baseline: 93 tests passed.
- Checkpoint: `6948b3a`, tag `smartfleet-before-step5-20261014` includes approved simplified Finance Balances.
- Backup: `smartfleet_20261014_210400.dump`, 381 archive entries verified.
- All rows in 39 public tables captured read-only in ignored `backups/step5_before_records.json` for preservation verification.
- No schema changes, public deployment or daily-use infrastructure in this scope.

## Stage 1

More > Help & Guide has Welcome, Getting Started, searchable/category-filtered expandable task instructions, plain financial terms and safe correction/troubleshooting guidance. Content lives in immutable `utils/help_content.py` guides and matches current labels, including Backfill / edit date and the simplified Balances page. It does not promise a repayment-association action that is not implemented.

Two focused search/filter and page interaction tests passed. Browser More navigation, expansion, search, empty-state and restoring all guides passed at 390x844 and 1440x1000. No viewport-wide overflow or app exceptions. Stage 1 is ready for the cleanup stage.
