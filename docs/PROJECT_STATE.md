# SmartFleet project state

Last updated: 2026-10-12
Audit context: local development project, Africa/Lusaka business date context.

## Purpose

SmartFleet is intended to become a phone-first fleet management system for a small bus transport business. The PostgreSQL database is the source of truth for buses, routes, drivers, cashing, collections, expenses, maintenance, payroll, accounts, transfers, loans and reminders. The Streamlit application is the user interface.

This document records the actual state found during the initial audit. It does not describe a finished system.

## Current development stage

The database foundation is substantially designed and migrated. The Python application layer now includes the Streamlit app shell, navigation foundation, shared UI helpers, real-data empty states, fleet setup write workflows, direct cashing entry/edit/delete, expense entry/edit/delete, account opening-balance management, backups, exports, setup warnings, Business Presets and a consolidated Business Balance view. Several advanced financial write workflows are still incomplete.

## Environment found

| Item | Current value |
| --- | --- |
| Python | 3.14.0 in `.venv` |
| Streamlit | 1.65.0 |
| PostgreSQL | 18.6 |
| psycopg | 3.3.6 |
| python-dotenv | 1.2.4 |
| pandas | 3.0.6 |
| altair | 6.3.0 |
| unittest | Built into Python; current baseline runner |
| pytest | Not installed in `.venv`; also missing from `requirements.txt` |

The `.env` file is present and contains the expected database keys: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` and `DB_PASSWORD`. Values were not documented here.

## Git state at audit

- The `pre-codex-development` tag exists.
- Work began from `master`.
- A development branch was created: `codex/audit-documentation`.
- The supplied UI reference folder `docs/ui-references/` existed as untracked content before documentation edits.

## Implemented

### Repository

- `database/connection.py`
  - Loads `.env`.
  - Creates a PostgreSQL connection with psycopg.
- `app.py`
  - Streamlit entrypoint using `st.navigation` with hidden native navigation and shared app framing.
- `.streamlit/config.toml`
  - Initial SmartFleet theme tokens.
- `app_pages/`
  - Initial Home, Buses, Finance, More, Add Bus, Record Cashing, Record Expense, Reminders, Backups, Accounts and Reports pages.
- `components/`
  - Shared layout, card and form helpers.
- `utils/`
  - Date, formatting and validation helpers.
- `services/route_service.py`
  - Lists routes.
  - Adds a route after trimming and validating the route name.
- `services/bus_service.py`
  - Lists buses with their route names.
  - Lists buses with route and assignment context.
  - Creates bus records with optional model, seating capacity, chassis number, document expiry metadata and initial assignment.
- `services/dashboard_service.py`
  - Provides period financial summary, bus status counts, bus performance and recent activity helpers.
- `services/driver_service.py`
  - Provides driver overview and available employment lookup.
  - Creates drivers with an initial active employment record.
- `services/finance_service.py`
  - Provides collection, expense, calculated account balance, consolidated Business Balance and business-ledger helpers.
- `services/cashing_service.py`
  - Provides Airtel Money collection-destination lookup, recent collection summaries, effective-dated cashing rate lookup, direct cashing recording, collection editing and collection deletion.
- `services/expense_service.py`
  - Provides active expense categories, active payment accounts, recent expense summaries and business-account expense recording/editing/deletion.
- `services/account_service.py`
  - Provides account management helpers for opening balances and calculated balance warnings.
- `services/backup_service.py`
  - Provides in-app PostgreSQL backup creation, verification and listing.
- `services/report_service.py`
  - Provides CSV export data for collections, expenses and balances.
- `services/validation_service.py`
  - Provides setup and data warnings for Home and More.
- `services/reminder_service.py`
  - Provides due maintenance, document expiry, deactivated bus and open reminder helpers.
- `services/preset_service.py`
  - Provides Business Presets for reporting baseline, Airtel collection destination, cashing rates, schedule rules, salary presets and reminder-warning days.
- `services/loan_service.py`
  - Provides a safe unidentified business-loan repayment workflow that records financing payments separately from operating expenses.
- `tests/test_connection.py`
  - Read-only database connectivity and core-table check.
- `tests/test_bus_service.py`
  - Read-only bus retrieval shape check.
- `tests/test_route_service.py`
  - Read-only route listing shape check.
- `tests/test_cashing_form.py`, `tests/test_cashing_service.py`, `tests/test_record_cashing_page.py`
  - Direct cashing form, service validation and Streamlit page-state tests.
- `tests/test_dashboard_charts.py`
  - Chart scaling and zero-baseline checks.
- `tests/test_expense_service.py`
  - Expense validation checks before database writes.
- `tests/inspect_buses.py`
  - Ad hoc schema inspection script for buses and routes.
- `migrations/`
  - Numbered SQL migrations `001` through `025`.
  - A corrected SQL integrity-test script.
- `docs/SmartFleet_Database_Schema_V1_Technical_Reference.docx`
  - Existing source-derived database reference.
- `docs/SmartFleet_Database_Schema_V1_Technical_Reference.pdf`
  - PDF version of the same reference.
- `docs/ui-references/`
  - Phone-first mockup images and a README explaining which screenshot details are conceptual only.

### Database

The live `smartfleet` database exists and contains 33 public tables:

| Area | Tables |
| --- | --- |
| Fleet and people | `routes`, `buses`, `bus_documents`, `drivers`, `driver_employments`, `driver_assignments` |
| Accounts and money movement | `financial_accounts`, `financial_transactions`, `transfers`, `transfer_fee_rules` |
| Expenses | `expense_categories`, `expenses`, `expense_allocations` |
| Cashing and collections | `cashing_schedules`, `cashing_rates`, `remittance_collections`, `remittances` |
| Owner and business loans | `owner_loans`, `owner_loan_transactions`, `business_loans`, `loan_repayments` |
| Driver finance and payroll | `driver_advances`, `driver_deductions`, `driver_salaries`, `salary_advance_recoveries`, `salary_deduction_allocations` |
| Maintenance and reminders | `maintenance`, `maintenance_schedules`, `reminders` |
| Business presets | `business_settings`, `business_preset_audit`, `cashing_schedule_rules`, `driver_salary_presets`, `reminder_presets` |

The database includes primary keys, foreign keys, uniqueness constraints, check constraints, partial unique indexes, deferred integrity triggers and timestamp triggers.

PostgreSQL functions currently installed:

- `sf_suggest_transfer_fee`
- `sf_is_external_transfer`
- `sf_assert_transfer`
- `sf_assert_expense`
- `sf_assert_collection`
- `sf_assert_advance`
- `sf_assert_deduction`
- `sf_assert_salary`
- `sf_assert_owner_loan_transaction`
- `sf_assert_owner_balance`
- `sf_assert_loan_repayment`
- `sf_assert_business_loan`
- `sf_assert_employment`
- `sf_assert_maintenance`
- `sf_assert_ledger`
- `sf_assert_rate`
- `sf_assert_fee_rule`
- `sf_integrity_deferred`
- `sf_preserve_account_type`
- `sf_touch_updated_at`

### Current seed and development data

| Table | Row count | Notes |
| --- | ---: | --- |
| `routes` | 2 | Registered business routes |
| `buses` | 3 | Registered buses |
| `bus_documents` | 6 | Bus document metadata |
| `drivers` | 3 | Registered drivers |
| `driver_employments` | 3 | Active employment records |
| `driver_assignments` | 3 | Active bus assignments |
| `financial_accounts` | 3 | Cash, Airtel Money, Bank |
| `expense_categories` | 9 | Maintenance, Parts, Driver Salaries, Driver Advances, Transfer Fees, Loan Repayments, Owner Drawings, Office & Administration, Other |
| `owner_loans` | 1 | Owner Loan Account |
| `cashing_rates` | 2 | NORMAL_DAY K600, SUNDAY K300 |
| `cashing_schedules` | 2 | Thursday and Sunday |
| `business_settings` | 2 | Reporting baseline and Airtel collection destination |
| `cashing_schedule_rules` | 2 | Thursday and Sunday collection coverage presets |
| `driver_salary_presets` | 1 | Default monthly salary preset |
| `reminder_presets` | 3 | Maintenance, document expiry and overdue cashing warning windows |
| `transfer_fee_rules` | 15 | Airtel-to-Airtel and Airtel-to-Bank fee bands |
| All operational transaction tables | 0 | No live cashing, expenses, payroll, maintenance, loan repayments or reminders |

## Tested

### Migration recreation

A uniquely named temporary PostgreSQL database was created, all numbered migrations `001` through `025` were applied successfully, and the temporary database was dropped afterward.

Result: pass.

### Safe baseline checks executed

| Command | Result |
| --- | --- |
| `.venv\Scripts\python.exe -m unittest discover -v` | Passed: 33 tests |
| `.venv\Scripts\python.exe -m pytest tests\test_connection.py tests\test_bus_service.py` | Historical failure because `pytest` is not installed |
| `.venv\Scripts\python.exe tests\test_connection.py` | Failed because running the file by path cannot import `database` |
| `.venv\Scripts\python.exe tests\test_bus_service.py` | Failed because running the file by path cannot import `services` |
| `.venv\Scripts\python.exe -m tests.test_connection` | Passed. Core database tables exist |
| `.venv\Scripts\python.exe -m tests.test_bus_service` | Passed. Bus rows have expected shape |
| `.venv\Scripts\python.exe -m compileall app.py app_pages services components utils tests scripts` | Passed |
| Streamlit `AppTest` page sweep | Passed for Home, Buses, Finance, More, Record Cashing, Record Expense, Accounts, Business Presets, Backups, Reports and Reminders |
| `.venv\Scripts\python.exe scripts\verify_migrations.py` | Passed. Applied migrations `001` through `025` to a disposable database and dropped it |
| Disposable cashing smoke test | Passed. Created a temporary database, migrated through `023`, inserted one temporary route and bus, recorded a K1,800 cashing collection, verified collection/remittance totals, then dropped the database |
| Direct cashing disposable smoke test | Passed against `smartfleet_demo`; inserted, edited and deleted one future-dated test collection and verified no smoke rows remained |
| Disposable expense smoke test | Passed. Created a temporary database, migrated through `023`, inserted a temporary route and bus, recorded one general expense and one bus expense, verified expense and ledger totals, then dropped the database |
| Disposable edit/delete smoke test | Passed. Created a temporary database, migrated through `024`, verified opening balance update, expense edit/delete and cashing edit/delete, then dropped the database |
| Backup service check | Passed. Created and verified `smartfleet_20261012_233219.dump` before applying migration `025` to the live database |

Note: the AppTest process printed a Windows temporary-folder cleanup warning after all page checks passed. The page checks themselves succeeded.

### Tests intentionally not executed

- `tests/test_route_service.py` is now read-only. Earlier versions wrote a testing route to the development database.
- `migrations/smartfleet_integrity_tests_corrected.sql` was not run against the live database. It is a database integrity test suite and should be run only in a disposable database or transaction-controlled test environment.

## Planned

Immediate planned work after the initial app foundation:

1. Add bus edit, deactivate/reactivate and route-change workflows.
2. Expand driver employment and bus assignment management beyond initial setup.
3. Expand Record Cashing with optional import from spreadsheet-style notes.
4. Expand Record Expense with owner-personal expenses and multi-bus allocation.
5. Implement maintenance scheduling and reminders.
6. Add isolated database integration tests for data-changing workflows.
7. Add browser/mobile verification for bottom navigation and narrow viewport behavior.

## Blocked or unresolved

| Area | Blocker |
| --- | --- |
| Isolated database integration suite | Routine data-changing tests need a dedicated test database. |
| Legacy pages folder | `pages/` exists but is empty. The app now uses explicit `st.navigation`, which causes Streamlit to ignore the legacy folder. |
| Bus document uploads | Bus document metadata and expiry dates are stored, but uploaded file persistence is not designed yet. |
| `In Garage` bus status | `buses.status` allows only `ACTIVE` and `INACTIVE`. Garage state must come from maintenance/downtime rules or an approved new operational-status model. |
| Recent Activity | No audit-log table exists. Initial activity can only be derived carefully from real domain records, not manufactured from unrelated timestamps. |
| Stored document reminders | The Reminders page can derive document expiry alerts from `bus_documents`; creating/dismissing stored reminder rows from those dates is still planned. |
| Authentication and authorization | Not implemented. Public deployment is not safe until this is designed and enforced server-side. |
| UI verification | Headless Streamlit checks passed. Browser/mobile viewport verification is still pending. |

## Known architectural risks

- Current tests cover key unit/page cases, but data-changing integration coverage still needs an isolated database.
- Services use direct connections and simple transaction scopes. A dedicated transaction helper is still planned.
- There is no repository/data-access layer beyond service-level SQL functions.
- Financial operations must be implemented as atomic multi-table transactions. Writing one table at a time from UI handlers would bypass the intended integrity model.
- Current bus listing uses an inner join to routes. That is valid because `buses.route_id` is required, but future lists may need driver and assignment joins that respect historical dates.
- Application-level warnings exist, but field-level validation and duplicate-submit protection still need to be expanded.
