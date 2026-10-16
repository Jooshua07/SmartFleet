# SmartFleet Technical Audit Report

Date: 2026-10-15 (Africa/Lusaka)  
Scope: pre-migration assessment only; no migration implementation.

## 1. Repository and evidence

- Repository: [Jooshua07/SmartFleet](https://github.com/Jooshua07/SmartFleet).
- Audited branch: `migration/fastapi-flet`.
- Audited commit: [46c76438b53b12f7779b89d0e2e74f72c6eb0d4f](https://github.com/Jooshua07/SmartFleet/tree/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f), message `checkpoint: smartfleet before migration`, committed 2026-10-15 21:00:31 +02:00.
- Remote `codex/expense-finance-refinement` points to that checkpoint. Remote default HEAD was `e8b70f4370e1ca1efcaa0fc7d73c09ffbfbbd9ad`, an older initial-services checkpoint. A reader opening GitHub's default branch will not necessarily see this audited application.
- Working tree was clean before this audit. The only intended additions are these six audit documents.
- Evidence labels: **Source** = inspected source/catalog query logic; **Live** = read-only inspection of the configured database/environment; **Unverified** = not exercised or not accessible in this audit.
- All Python modules were inventoried; financial, transaction, UI-state and migration hot paths received targeted source review. This is not a claim that every possible execution path or every live data row was exhaustively tested.

Companion documents: [Reusability Matrix](02_existing_code_reusability_matrix.md), [PostgreSQL Integrity](03_postgresql_integrity_and_migration_risks.md), [Target Architecture](04_fastapi_flet_target_architecture.md), [Migration Plan](05_migration_implementation_plan.md), [Environment Guide](06_environment_and_dependency_setup.md).

## 2. Executive decision

**Ready to begin a controlled, read-only migration prototype. Not ready to expose financial write APIs to the internet.**

The services already separate much of the business logic from Streamlit. PostgreSQL is a valuable part of the application, not a disposable storage layer. Preserve it and reuse the psycopg services initially. Replacing the UI, database access layer and schema simultaneously would add unnecessary risk.

Before remote financial entry: introduce authenticated server-side permissions, replace the superuser runtime connection, protect commands against retries/concurrent duplicates, establish accountable corrections, baseline the actual schema, and prove backup restoration on an isolated database. The bus-report discrepancy must be resolved before claiming reporting parity.

## 3. Application inventory

101 Python files including package markers: 24 in services, 8 utils, 2 database, 18 app_pages, 6 components, 27 tests, 15 scripts, and root app.py. There are 25 test_*.py modules. The function-level inventory is in Document 2.

17 registered screens: Home, Buses, Finance, More, Record Cashing, Record Expense, Add Bus, Reminders, Backups, Bus Accounts, Business Presets, Reports, Driver Money, Loans, Owner Money, Record Servicing, and Help & Guide.

- UI/navigation: `app.py`, `app_pages/*`, `components/*`; Streamlit session state, widgets, reruns, CSS/fixed controls and process-local caches.
- Data: `database/connection.py:get_connection:9` uses psycopg and environment settings. Services contain parameterized PostgreSQL SQL. No SQLAlchemy model layer was found.
- Domain: cashing obligations/allocations, expense classification, salaries/advance recovery, lender and owner money, maintenance, reporting presets, ledger and operating performance.
- Schema: 31 ordered SQL migration files (001-031), plus `smartfleet_integrity_tests_corrected.sql`.
- Configuration: requirements.txt, .env loading, .streamlit/config.toml, .gitignore. Secrets were not reproduced in the reports.
- Documentation: architecture, module reference, feature status, testing, Step 4/5 reports, UI specification/reference images, and historical business records. These describe successive states, not one guaranteed current specification.

## 4. Findings by severity

### C1. No application authentication or authorization
**Critical before internet deployment; Source.** `app.py` registers pages without a user/role gate. The service interface accepts record IDs and commands without an authenticated actor. No user/role schema or implemented authentication layer was found.

A backend would otherwise allow access to business records and financial changes without accountable identity. Hiding a Flet button is not authorization. Require server-side roles for reading, recording, correcting, payroll, presets, balances, exports and backups. See Document 4 for a proposed permission model.

### C2. Application uses a highly privileged PostgreSQL role
**Critical before deployment; Live.** The configured role has superuser, create-database, create-role and bypass-RLS privileges. No role name or credential is included here.

Use a separate non-owner, non-superuser runtime role with explicit required grants; a separate migration/admin identity; and a private database network. Test every service and integrity function with the restricted role. No privilege changes were made during this audit.

### H1. Financial consistency does not prevent duplicate commands
**High; Source, concurrency not reproduced.** `services/smart_cashing_service.py:_find_existing_entries:243` checks existing entries before `record_smart_cashing_collection:378` inserts. The unique remittance index covers `(collection_id, bus_id)`, not a bus/date across two different collections. Concurrent requests can both pass the pre-check.

A retry after an internet timeout can also repeat an otherwise valid expense, owner payment or loan payment. Existing foreign keys and ledger checks do not identify the user's original request. Add durable idempotency for financial commands, payload comparison, atomic result storage, and a reviewed business-key locking/uniqueness policy. Do not assume all multiple collections on one date are invalid: confirm the intended cashing rule first.

### H2. Correction history is incomplete and not actor-attributed
**High; Source.** `services/correction_service.py:record_correction_audit:23` supports snapshots; migration 030 creates correction_audit. That table has no actor/user ID. Ordinary `expense_service.update_business_expense:276`, `delete_business_expense:404` and direct cashing edit/delete paths do not consistently use that audit helper.

Some money-workflow cancellation paths snapshot and physically remove records/dependent rows. Therefore this is not an immutable event ledger. Define permitted correction/reversal policy, authenticated actor, reason and before/after values before porting destructive endpoints. Preserve existing historical evidence; do not silently reinterpret old records.

### H3. Bus summary and bus detail use different cost definitions
**High; Source.** `services/bus_account_service.py:get_bus_contribution_summary:10` applies OPERATING_EXPENSE_PREDICATE and includes attributable earned salary. `get_bus_account_detail:170` builds expense-only trend/category/recent lists without that exclusion predicate or the same salary branch.

For periods with payroll or historical non-operating expense classifications, totals can disagree. This is a confirmed query-definition mismatch, not a claim that a particular live month's data is corrupt. Establish the canonical measure and add summary/detail/category reconciliation fixtures before migrating these screens.

### H4. No recorded schema baseline for migration tooling
**High; Source + Live.** Numbered SQL exists, but no database migration-ledger table was found. Later files replace functions introduced earlier. Migration 031's servicing objects are present; that does not prove every historical script was executed exactly as committed.

Do not run ORM create_all or replay 001-031 on the live database. Capture actual definitions, compare them with the final intended schema, restore to an isolated instance, and establish a reviewed baseline. PostgreSQL triggers, partial indexes, checks, generated values and deferred behavior must survive.

### H5. Backup listing is not a restoration proof
**High release gate; Source, restoration Unverified this audit.** `services/backup_service.py:create_database_backup:44` invokes PostgreSQL tools; `verify_backup:80` checks the archive listing. `scripts/verify_step4_backup.py` provides restoration-oriented tooling but was not executed in this no-write audit.

Before cutover, prove an isolated restore, permissions, sequences, constraints, functions and representative business totals; retain encrypted off-host copies and agreed recovery objectives. A successful archive listing alone is insufficient.

### M1. Multi-query reports do not share a snapshot
**Medium; Source.** `business_report_service.get_business_report:27` aggregates services and _query calls that each open connections. A concurrent write may be visible in some sections but not others. Current tests do not prove report consistency under concurrent entry. Adapt report reads to one read-only repeatable-read snapshot or an equivalent coherent reporting design.

### M2. Money/allocation rules remain mixed into UI code
**Medium; Source.** `app_pages/record_cashing.py:41,122,263,273,549,590` includes classification, expected amounts, allocation/correction arithmetic and float conversions next to widgets. `utils/validation.py:28,40` validates Decimal positivity, but does not itself enforce a two-decimal REST contract.

Extract these rules into testable domain functions; validate currency scale/range on the server. Transport amounts as decimal strings. Convert to float only in chart presentation, never for allocation or ledger calculations.

### M3. Historical interval protections are incomplete
**Medium; Source + Live.** Migration 026 enforces one open status/route interval, but no exclusion constraint prevents overlapping closed intervals. Live bus-status overlap count was zero. `bus_service.get_bus_active_day_counts:410` counts qualifying history; overlapping intervals could inflate results. Review inclusive boundaries and ended driver assignments in historical queries. Add transition/overlap/backdated tests without inventing missing history.

### M4. Balance and profitability definitions need explicit contracts
**Medium; Source.** `finance_service.get_business_balance:144` sums ledger movements from baseline without an upper date; `get_period_balance:49` has different period/account-opening/transfer treatment. `performance_service.get_operating_summary:87` measures operating performance rather than all money movements. These are not interchangeable.

Keep the agreed UX: Business Balance Now independent of date filters; filtered Money Received/Money Paid Out below; opening/closing in Reports. Specify whether future-dated entries count, how opening balances relate to the clean-slate date, and exclude internal transfers from consolidated cashflow. A transfer fee remains a real outflow. Do not silently relabel financing as revenue.

### M5. Some features are partial, intentionally absent, or not validated
**Medium; Source.**
- `account_service.get_negative_balance_warnings:78` returns an empty list: not an implemented negative-balance detector.
- Bus document metadata/expiry handling is present; a complete secure file-upload/storage/download workflow was not found.
- Loan payments can remain unidentified and loan principal can be unknown. UI association/correction needs an explicit design; never fabricate the 15,000 loan's terms.
- Tables/triggers for transfers do not constitute a complete user-facing transfer workflow.
- Driver employment/assignment lifecycle operations are not a complete general management UI.
- Expected cashing in reports derives from recorded remittances and available expectations, not proof of complete calendar earnings. Unknown must remain distinguishable from zero.

### M6. Operational/test gaps remain
**Medium; Source + Live environment.** No REST endpoint, authorization, mobile retry, concurrent command or packaged-device test suite exists yet. Streamlit caches are not a multi-worker API invalidation scheme. get_connection has no explicit application pool or connection timeout configuration. TLS behavior was not established, so this report does not assert TLS is disabled.

`scripts/seed_demo_data.py:208` selects its target via a provided database name; CLI default is smartfleet_demo, but no mandatory demo-name guard was observed. Keep seed/write-smoke tools off production and enforce isolated test targets. These scripts were not run here.

### M7. Repository/data exposure requires review
**Medium; Source, repository visibility Unverified.** Tracked files include `docs/bus book records from july to august.csv` and its XLSX companion. Review repository access and whether operational/driver information belongs in Git history. .env is not tracked; no claim of exposed credentials is made. Confirm secret scanning and protected deployment configuration before release.

## 5. Verification performed and limits

Fresh run: **98 tests passed in 11.722 seconds**, using unittest discovery, disabled bytecode writes and PostgreSQL default_transaction_read_only=on. Temporary test output was directed beneath backups/runtime-temp. Standard Streamlit missing-context warnings did not fail the suite.

Read-only live catalog inspection confirmed PostgreSQL 18.6, 39 tables, 39 PKs, 51 FKs, 100 CHECK constraints, 11 UNIQUE constraints, 276 NOT NULL constraints, 51 enabled non-internal triggers (19 deferred integrity triggers), and 20 sf_* functions. NOT NULL counts reflect PostgreSQL 18 catalog representation.

Not performed: production mutation, new migration, package install, backup restore drill, load/race simulation, public-network exposure check, security penetration test, mobile build, API implementation, or testing all real financial records. Older completion reports are historical evidence, not fresh execution results.

## 6. Recommended next action

Approve the proposed contracts and safeguards, then build only a local read-only bus-list API/Flet prototype against an isolated/read-only target. Do not begin with payroll, loans or schema rewriting. Advance to remote writes only after the release gates in Document 5 pass.

