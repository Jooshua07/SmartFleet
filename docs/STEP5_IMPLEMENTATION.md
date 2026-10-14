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

Stage 1 commit: `84392e3`.

## Stage 2 cleanup

Removed the unreachable direct-cashing entry form and its private amount/option helpers, which had no callers after Smart Cashing became the only new-entry path. Historical DIRECT record editing and the tested direct-cashing services/utilities remain. Removed unused Home/cashing imports, expense option helper and unused card/list wrappers. Historical migrations, constraints, financial audit rows, backups and reusable compatibility services remain.

Ordinary expense classification now uses one fixed SQL predicate in `financial_rules.py` across operating reporting and Bus Accounts. Summary and daily chart use one dated operating-activity query, preserving collection-header receipts, owner-paid operating expenses, earned salaries recognized on the first of the payroll month, and standalone fees exactly once. Ledger rows are reused for period balance/timeline/reconciliation. Report warning checks reuse one connection.

Measured finance/performance SQL executions: summary 5 -> 2, daily series 4 -> 1, timeline 7 -> 3. Warning-check connections: 11 -> 1. These are measured work reductions, not a promised wall-clock speed percentage.

## Service reload investigation

A disposable local app imported a helper returning `before`. An external service edit under the default `auto` event watcher remained `before` after a manual rerun. In this Windows/tool environment the event watcher missed the edit, leaving the Python module cached. It was unrelated to PostgreSQL records or the financial result caches.

Repeating the same edit with `server.fileWatcherType = "poll"` and `server.runOnSave = true` updated the helper automatically without restart. These two supported configuration settings are the smallest reliable fix. Removed the conditional/unconditional `importlib.reload` workarounds from the expense page/service and Smart Cashing service; normal imports now rely on Streamlit's watcher/eviction mechanism.

`scripts/smoke_service_reload.py` generates a disposable fixture and verifies both changed dependencies and a newly added export without restart, then terminates its server. It needs a brief startup wait for watcher registration. The first automated attempt raced registration and timed out; the corrected test passed. Polling has a small local file-check overhead. The result is verified on this machine, not a universal diagnosis of every Streamlit reload problem.

## Regression and safety

- Final unittest suite: 98 passed (baseline 93; two Help tests and three ledger/classification tests added).
- Smart Cashing, expense/finance, money workflows and Step 4 servicing/report/export scenarios passed in disposable PostgreSQL databases.
- All 17 pages passed read-only AppTest, including Finance period persistence, invalid dates and independent Home/chart controls.
- Changed screens and Help passed 390px/1440px browser checks; chart scrolling/tooltips still work.
- Before/after October, historical and empty November/December calculations match exactly for balances, daily/weekly timelines, Bus Accounts, reports, exports and reconciliation.
- All rows in 39 live public tables remain unchanged.
- No new dependencies, schema changes, scheduled backups, authentication or hosting.
- Compilation and whitespace checks passed.

## Review checklist and limitations

1. More > Help & Guide: search `advance`, choose Drivers, expand a question, try an unmatched search, then clear it.
2. Read Business Balance and Correction guides: verify their explanations match the simplified Finance screen and real loan/correction buttons.
3. Check cashing/backfill previews, older expense history and servicing history without saving test payments into the real DB.
4. Compare Finance/Reports totals and open an Excel export. The existing unidentified K15,000 loan is still unidentified and no association-link UI was added.

Stopped after Stage 2. Existing local app remains running for review. Deployment/daily-use infrastructure is not part of this run.
