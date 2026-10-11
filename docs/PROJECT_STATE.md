# SmartFleet project state

Last updated: 2026-10-11  
Audit context: local development project, Africa/Lusaka business date context.

## Purpose

SmartFleet is intended to become a phone-first fleet management system for a small bus transport business. The PostgreSQL database is the source of truth for buses, routes, drivers, cashing, collections, expenses, maintenance, payroll, accounts, transfers, loans and reminders. The Streamlit application is currently the planned user interface.

This document records the actual state found during the initial audit. It does not describe a finished system.

## Current development stage

The database foundation is substantially designed and migrated. The Python application layer is only a thin starting point. The Streamlit user interface has not yet been implemented.

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
- `services/route_service.py`
  - Lists routes.
  - Adds a route after trimming and validating the route name.
- `services/bus_service.py`
  - Lists buses with their route names.
- `tests/test_connection.py`
  - Ad hoc database connectivity check.
- `tests/test_bus_service.py`
  - Ad hoc bus retrieval check.
- `tests/test_route_service.py`
  - Ad hoc route creation script. It changes database data.
- `tests/inspect_buses.py`
  - Ad hoc schema inspection script for buses and routes.
- `migrations/`
  - Numbered SQL migrations `001` through `022`.
  - A corrected SQL integrity-test script.
- `docs/SmartFleet_Database_Schema_V1_Technical_Reference.docx`
  - Existing source-derived database reference.
- `docs/SmartFleet_Database_Schema_V1_Technical_Reference.pdf`
  - PDF version of the same reference.
- `docs/ui-references/`
  - Phone-first mockup images and a README explaining which screenshot details are conceptual only.

### Database

The live `smartfleet` database exists and contains 28 public tables:

| Area | Tables |
| --- | --- |
| Fleet and people | `routes`, `buses`, `drivers`, `driver_employments`, `driver_assignments` |
| Accounts and money movement | `financial_accounts`, `financial_transactions`, `transfers`, `transfer_fee_rules` |
| Expenses | `expense_categories`, `expenses`, `expense_allocations` |
| Cashing and collections | `cashing_schedules`, `cashing_rates`, `remittance_collections`, `remittances` |
| Owner and business loans | `owner_loans`, `owner_loan_transactions`, `business_loans`, `loan_repayments` |
| Driver finance and payroll | `driver_advances`, `driver_deductions`, `driver_salaries`, `salary_advance_recoveries`, `salary_deduction_allocations` |
| Maintenance and reminders | `maintenance`, `maintenance_schedules`, `reminders` |

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
| `routes` | 1 | `Kitwe - Ndola`, id `5`, active |
| `buses` | 0 | No registered buses |
| `drivers` | 0 | No registered drivers |
| `driver_employments` | 0 | No employment records |
| `driver_assignments` | 0 | No assignments |
| `financial_accounts` | 3 | Cash, Airtel Money, Bank |
| `expense_categories` | 9 | Maintenance, Parts, Driver Salaries, Driver Advances, Transfer Fees, Loan Repayments, Owner Drawings, Office & Administration, Other |
| `owner_loans` | 1 | Owner Loan Account |
| `cashing_rates` | 2 | NORMAL_DAY K600, SUNDAY K300 |
| `cashing_schedules` | 2 | Thursday and Sunday |
| `transfer_fee_rules` | 15 | Airtel-to-Airtel and Airtel-to-Bank fee bands |
| All operational transaction tables | 0 | No live cashing, expenses, payroll, maintenance, loan repayments or reminders |

## Tested

### Migration recreation

A uniquely named temporary PostgreSQL database was created, all numbered migrations `001` through `022` were applied successfully, and the temporary database was dropped afterward.

Result: pass.

### Safe baseline checks executed

| Command | Result |
| --- | --- |
| `.venv\Scripts\python.exe -m pytest tests\test_connection.py tests\test_bus_service.py` | Failed because `pytest` is not installed |
| `.venv\Scripts\python.exe tests\test_connection.py` | Failed because running the file by path cannot import `database` |
| `.venv\Scripts\python.exe tests\test_bus_service.py` | Failed because running the file by path cannot import `services` |
| `.venv\Scripts\python.exe -m tests.test_connection` | Passed. Connected to database and found 28 tables |
| `.venv\Scripts\python.exe -m tests.test_bus_service` | Passed. Returned an empty bus list |

### Tests intentionally not executed

- `tests/test_route_service.py` was not executed because it calls `add_route("Kitwe - Ndola")` and would write to the development database. It may also fail now because that route already exists and route names are unique.
- `migrations/smartfleet_integrity_tests_corrected.sql` was not run against the live database. It is a database integrity test suite and should be run only in a disposable database or transaction-controlled test environment.

## Planned

Immediate planned work after baseline documentation:

1. Establish the Streamlit app shell and navigation.
2. Introduce shared UI helpers for phone-first cards, badges, lists, forms, skeletons and messages.
3. Implement route and bus management.
4. Implement an Add Bus workflow that only stores fields supported by the schema unless a schema migration is approved.
5. Implement drivers, assignments and historical lookup.
6. Implement Record Cashing with the existing remittance and collection model.
7. Implement expenses, finance summaries, maintenance reminders and dashboard views from real PostgreSQL data.
8. Add pytest-based unit and integration tests using an isolated test database.
9. Add Streamlit `AppTest` coverage for UI behavior and browser/mobile checks where needed.

## Blocked or unresolved

| Area | Blocker |
| --- | --- |
| `pytest` test suite | `pytest` is not installed and is not listed in `requirements.txt`. |
| App entrypoint | `app.py` is empty. No Streamlit UI exists yet. |
| Legacy pages folder | `pages/` exists but is empty. Streamlit 1.65 supports `st.navigation`; the planned app should avoid mixing old `pages/` auto-discovery with explicit navigation. |
| Add Bus model and seating capacity | `buses` has no model or seating-capacity columns. Storing these requires an approved additive migration or removing those fields from the persisted MVP flow. |
| Add Bus documents | No document metadata or file-storage tables exist. Upload persistence needs a design decision and likely a migration. |
| `In Garage` bus status | `buses.status` allows only `ACTIVE` and `INACTIVE`. Garage state must come from maintenance/downtime rules or an approved new operational-status model. |
| Recent Activity | No audit-log table exists. Initial activity can only be derived carefully from real domain records, not manufactured from unrelated timestamps. |
| Document expiry reminders | The schema has generic `DOCUMENT_EXPIRY` reminders but no bus document table. Automatic expiry alerts need persisted document dates. |
| Authentication and authorization | Not implemented. Public deployment is not safe until this is designed and enforced server-side. |
| UI verification | No app exists to run. Mobile viewport verification is pending implementation. |

## Known architectural risks

- Current tests are ad hoc scripts, not a reliable automated suite.
- Services use direct connections but do not yet define transaction-scoped business operations.
- There is no repository/data-access layer beyond simple service functions.
- Financial operations must be implemented as atomic multi-table transactions. Writing one table at a time from UI handlers would bypass the intended integrity model.
- Current bus listing uses an inner join to routes. That is valid because `buses.route_id` is required, but future lists may need driver and assignment joins that respect historical dates.
- No application-level error handling, user-facing validation layer or duplicate-submit protection exists yet.

