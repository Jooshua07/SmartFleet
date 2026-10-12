# SmartFleet controlled refactoring - Step 1 audit

Date: 2026-10-12  
Branch: `codex/controlled-step1-audit`  
Database inspected: `smartfleet`

## Scope

This document completes Step 1 only: audit, protection and documentation. No Step 2 feature implementation was started.

## Protection and recovery

- Verified recovery checkpoint commit: `aa426f817219b0184b5077a4bb1dcdee84ac1a83`.
- Verified recovery tag on that commit: `smart-fleet-before-refactoring`.
- Created a separate working branch: `codex/controlled-step1-audit`.
- Preserved existing uncommitted newer changes; they were not discarded.
- Confirmed `.env` points at the real database: `DB_NAME=smartfleet`.
- Created and verified a fresh PostgreSQL custom-format backup:
  - `backups/smartfleet_20261012_230017.dump`
  - `pg_restore --list` returned 308 lines.
- Recovery procedure verified at list/inspect level only. A full restore into a disposable database remains recommended before destructive cleanup.

## Package and app baseline

- Python virtual environment is active through `.venv`.
- Streamlit: `1.65.0`.
- psycopg: `3.3.6`.
- pandas: `3.0.6`.
- altair: `6.3.0`.
- `python-dotenv` is installed.

Current app structure remains:

- `app.py` as Streamlit entry point.
- `app_pages/` for Home, Buses, Finance, More and hidden workflow pages.
- `components/` for shared layout/cards/forms.
- `services/` for database-backed workflows.
- `utils/` for validation, dates, formatting and chart/form helpers.
- `database/connection.py` for `.env`-backed psycopg connections.
- `migrations/001` through `024` plus SQL integrity tests.
- `tests/` with unittest and Streamlit AppTest coverage.

## Database inventory

Current row counts in `smartfleet`:

| Table | Rows |
| --- | ---: |
| `routes` | 2 |
| `buses` | 3 |
| `bus_documents` | 6 |
| `drivers` | 3 |
| `driver_employments` | 3 |
| `driver_assignments` | 3 |
| `financial_accounts` | 3 |
| `financial_transactions` | 0 |
| `expenses` | 0 |
| `remittance_collections` | 0 |
| `remittances` | 0 |
| `cashing_rates` | 2 |
| `cashing_schedules` | 2 |
| `transfer_fee_rules` | 15 |
| `owner_loans` | 1 |
| all other operational transaction tables | 0 |

Current cashing configuration:

- `cashing_rates`
  - `NORMAL_DAY`: K600.00, active, effective from 2026-10-07.
  - `SUNDAY`: K300.00, active, effective from 2026-10-07.
- `cashing_schedules`
  - day 4, active, current Thursday cashing day.
  - day 7, active, current Sunday cashing day.

Installed integrity functions:

- `sf_assert_collection`
- `sf_assert_ledger`
- `sf_assert_expense`
- `sf_assert_rate`
- `sf_assert_transfer`
- `sf_assert_loan_repayment`
- `sf_assert_business_loan`
- `sf_assert_owner_loan_transaction`
- `sf_assert_owner_balance`
- `sf_assert_advance`
- `sf_assert_deduction`
- `sf_assert_salary`
- `sf_assert_employment`
- `sf_assert_maintenance`
- `sf_assert_fee_rule`
- `sf_integrity_deferred`
- `sf_preserve_account_type`
- `sf_touch_updated_at`
- `sf_is_external_transfer`
- `sf_suggest_transfer_fee`

Important existing constraints and indexes:

- `buses.status` is limited to `ACTIVE` or `INACTIVE`.
- `driver_assignments` already has start/end dates and `ACTIVE`/`ENDED` status.
- `driver_employments` already has start/end dates and employment status.
- `cashing_rates` already has effective dates and active rows, but active uniqueness is currently one active rate per `rate_type`.
- `cashing_schedules` currently stores only `day_of_week`, `active`, `notes` and timestamps.
- `remittance_collections` enforces total amount and ledger-link consistency.
- `remittances` enforces non-negative days/rates/actual amount and requires an explanation when actual differs from computed normal/sunday expected amount.
- Unique `ux_cashing_financial_tx` ensures one collection points to one receipt ledger transaction.
- `financial_transactions.transaction_type` already allows `LOAN_REPAYMENT`, `DRIVER_SALARY`, `CASHING`, `EXPENSE`, `OTHER` and related finance types.
- `loan_repayments.loan_id` is currently required, so "repayment without known original loan" needs a migration or a controlled placeholder strategy.

## Files inspected

Core entry and layout:

- `app.py`
- `components/layout.py`
- `components/cards.py`

Pages:

- `app_pages/home.py`
- `app_pages/buses.py`
- `app_pages/finance.py`
- `app_pages/more.py`
- `app_pages/record_cashing.py`
- `app_pages/record_expense.py`
- `app_pages/add_bus.py`
- `app_pages/accounts.py`
- `app_pages/backups.py`
- `app_pages/reports.py`
- `app_pages/reminders.py`

Services:

- `services/cashing_service.py`
- `services/expense_service.py`
- `services/finance_service.py`
- `services/account_service.py`
- `services/bus_service.py`
- `services/driver_service.py`
- `services/dashboard_service.py`
- `services/backup_service.py`
- `services/report_service.py`
- `services/reminder_service.py`
- `services/validation_service.py`

Utilities and tests:

- `utils/cashing_form.py`
- `utils/dashboard_charts.py`
- `utils/dates.py`
- `utils/formatting.py`
- `utils/validation.py`
- `tests/test_*.py`

Database:

- `migrations/001` through `024`.
- `migrations/smartfleet_integrity_tests_corrected.sql`.
- live PostgreSQL schema metadata for tables, constraints, indexes, triggers and functions.

## Current implementation findings

### Cashing

Existing reusable functions:

- `get_active_financial_accounts()`
- `get_recent_cashing_collections()`
- `get_cashing_collection()`
- `record_direct_cashing_collection()`
- `update_direct_cashing_collection()`
- `delete_cashing_collection()`
- `build_direct_cashing_entries()`

Current behavior:

- The UI records direct per-bus amounts.
- One `remittance_collections` row is created for a collection.
- One `financial_transactions` receipt is created for the collection total.
- Multiple `remittances` rows can link bus allocations to that collection.
- Edit/delete updates or deletes the linked ledger transaction.

Gaps for Step 4:

- No automatic Sunday/Thursday coverage-period calculation.
- No locked default date with explicit backfill mode.
- No default selection of all eligible buses for a historical work period.
- No distinction between estimated standard allocation and confirmed actual allocation.
- No unallocated amount storage.
- No difference classification field.
- No confirmed outstanding obligation table.
- No repayment/settlement workflow for obligations.
- Current `remittances_variance_reason_check` assumes expected amount can be computed from normal/sunday days and rates, but it does not model unknown differences or non-debt underperformance as first-class states.

### Accounts and balances

Existing reusable functions:

- `get_accounts_for_management()`
- `update_opening_balance()`
- `get_account_balances()`
- `get_negative_balance_warnings()`

Current behavior:

- Account balances are per account: Cash, Airtel Money and Bank.
- Finance Balances lists account balances separately.
- `financial_transactions` already records direction, amount, type, account and date.

Gaps for Step 2 and Step 5:

- No consolidated Business Balance service.
- No chronological consolidated ledger service.
- Operational screens still expose active account selection.
- Underlying account rows should be preserved, but current UI does not yet support "Airtel Money as sole active collection destination".

### Business presets

Existing support:

- `cashing_rates` supports effective-dated normal and Sunday rates.
- `cashing_schedules` supports active collection weekdays.
- `driver_employments.monthly_salary` stores salary per employment.
- reminder warning windows are not centralized as presets.

Gaps:

- No Business Presets page or service.
- No audit trail for preset changes.
- No bus-specific cashing rates.
- No schedule coverage mapping, such as Thursday covering Monday-Wednesday plus previous Sunday, and Sunday covering Thursday-Saturday.
- No separate salary preset/override model.
- No configurable reminder-preset model.

### Fleet and date-aware eligibility

Existing support:

- `buses.status` supports `ACTIVE` and `INACTIVE`.
- `driver_assignments` and `driver_employments` include start/end dates.
- `get_buses_overview(on_date=...)` is already date-aware for driver assignment display.

Gaps for Step 3 and Step 4:

- No bus status history table.
- No deactivation/reactivation service.
- No reason/effective-date history for bus deactivation.
- Historical cashing currently filters `buses.status = 'ACTIVE'`, which can be wrong for historical backfill if a bus was deactivated after the collection period.
- No bus edit or route reassignment service.
- Driver editing is not implemented.

### Loan repayments

Existing support:

- `financial_transactions.transaction_type` includes `LOAN_REPAYMENT`.
- `loan_repayments` exists and links to `business_loans` and a financial transaction.

Gap:

- `loan_repayments.loan_id` is required, so a repayment cannot currently be recorded without a known/original loan unless a placeholder loan is created or the schema is migrated.

### Expenses

Existing support:

- Expense add/edit/delete exists.
- `description`, `vendor_name`, `reference_number` and `notes` are stored.
- General and single-bus business-account expenses are supported.

Gaps:

- No explicit short title separate from longer notes.
- No title validation for maximum five words and 35 characters.
- Finance Expenses currently shows category name as the main card title, not the actual expense title.
- Owner-personal and multi-bus allocation workflows are still not exposed.

## Baseline tests executed

Safe baseline checks:

| Check | Result |
| --- | --- |
| `python -m compileall app.py app_pages services utils components database tests` | Passed |
| `python -m unittest discover -v` | Passed, 26 tests |
| Streamlit AppTest page-load sweep | Passed for Home, Buses, Finance, More, Record Cashing, Record Expense, Add Bus, Reminders, Backups, Accounts and Reports |
| PostgreSQL backup creation | Passed |
| PostgreSQL backup verification with restore-list | Passed |

Notes:

- Streamlit AppTest emitted known harmless bare-mode/temp-folder cleanup warnings after successful checks.
- No data-changing tests were run against the real database.
- The SQL integrity test file was not run against the real database.

## Affected modules for future steps

Step 2 likely affected files:

- `app_pages/finance.py`
- `app_pages/more.py`
- new `app_pages/business_presets.py` or `app_pages/management.py`
- `components/layout.py` only if navigation to Management is required.
- `services/finance_service.py`
- `services/account_service.py`
- new `services/preset_service.py`
- new `services/loan_service.py`
- `services/cashing_service.py` for centralized effective-dated rate lookup.
- migrations for presets, account-visibility/default destination and loan repayment support.
- tests for finance, presets, rates and loan repayment classification.

Step 3 likely affected files:

- `app_pages/buses.py`
- `app_pages/add_bus.py`
- `services/bus_service.py`
- `services/driver_service.py`
- possible new `services/assignment_service.py`
- migrations for bus status history.
- tests for status history, route change and driver edit.

Step 4 likely affected files:

- `app_pages/record_cashing.py`
- `services/cashing_service.py`
- `utils/cashing_form.py`
- new smart-cashing calculation helpers.
- migrations for coverage, allocation provenance, differences and obligations.
- tests for collection cycles, Sunday work, allocation totals, obligations and correction safety.

Step 5 likely affected files:

- `app_pages/finance.py`
- `app_pages/record_expense.py`
- `services/finance_service.py`
- `services/expense_service.py`
- `services/report_service.py`
- migrations for expense titles if not reusing `description` safely.

Step 6 likely affected files:

- new script or service for dry-run import.
- `services/cashing_service.py`, `services/expense_service.py`, future loan/salary services.
- docs and tests for October reconciliation.

## Proposed database changes

These are proposals only. No migrations were created in Step 1.

1. Business Presets
   - Reuse `cashing_rates` for normal and Sunday rates where possible.
   - Add audit columns or an audit table for rate/preset changes.
   - Add schedule coverage configuration, because `cashing_schedules.day_of_week` alone cannot describe covered workdays.
   - Add driver salary preset/override storage if salary rules must exist outside employment rows.
   - Add reminder preset storage for configurable warning periods.

2. Consolidated Business Balance
   - Prefer service-level calculation from `financial_transactions` first.
   - Consider account visibility/default-destination fields rather than deleting Cash/Bank rows.
   - Consider a transaction classification/reporting category if operating vs financing cashflows need clearer reporting.

3. Loan repayments without original loan
   - Option A: allow nullable `loan_repayments.loan_id` plus status/notes for unidentified loan.
   - Option B: create a controlled "unidentified business loan" record, but this risks hiding uncertainty.
   - Recommended: additive migration allowing unresolved loan repayment metadata without fabricating a loan.

4. Date-aware bus status
   - Add `bus_status_history` with bus, status, effective date, reason, created metadata.
   - Keep current `buses.status` as current-state cache/display field.
   - Service must update both in one transaction.

5. Smart cashing
   - Add collection coverage fields or child table to store work-period start/end and collection type.
   - Add allocation provenance fields to `remittances` or a new allocation table: `CALCULATED_STANDARD`, `CONFIRMED_ACTUAL`, `MANUAL_ADJUSTED`.
   - Add difference classification: `REDUCED_WORKDAYS`, `UNDERPERFORMANCE`, `CONFIRMED_UNPAID_OBLIGATION`, `UNKNOWN_DIFFERENCE`, `SURPLUS`, possibly nullable when balanced.
   - Add explicit unallocated amount support.
   - Add confirmed obligation tables with responsible party type/id/name, status, originating collection/allocation, outstanding amount and repayment links.
   - Add repayment/settlement table linked to one receipt transaction to prevent double counting.

6. Expense titles
   - Either use existing `expenses.description` as the short title and enforce new rules for future edits, or add `title` and preserve existing descriptions as details.
   - Recommended: add `title` only if existing descriptions are longer operational notes.

## Data-integrity risks

- Current real database contains operational setup data: 2 routes, 3 buses, 3 drivers, 3 assignments and 6 documents. It has no financial transactions yet.
- The existing direct-cashing UI can record real money, but it does not enforce the new smart-cashing rules.
- Historical eligibility based only on current `buses.status` can misstate historical cashing if buses are deactivated/reactivated later.
- The current `remittances` model conflates expected formula details and actual amount without first-class provenance or unresolved difference state.
- Confirmed obligations cannot be represented without risking fake debts or informal notes.
- Loan repayments cannot be recorded without an existing loan under the current schema.
- Removing Cash/Bank at the database level would be risky because historical dependencies exist; UI-level hiding/defaulting is safer.
- Destructive cleanup before October must wait for a full restore-tested backup, dependency report and explicit approval.
- Current tests do not yet use an isolated database fixture for write-heavy integration tests.

## Documentation created

- `docs/CONTROLLED_REFACTOR_STEP1_AUDIT.md`

Existing docs reviewed:

- `docs/PROJECT_STATE.md`
- `docs/ARCHITECTURE.md`
- `docs/MODULE_REFERENCE.md`
- `docs/FEATURE_STATUS.md`
- `docs/TESTING.md`
- `docs/UI_UX_SPECIFICATION.md`

## Next-step readiness

Step 1 is ready for review.

Recommended Step 2 start sequence after approval:

1. Create additive migration plan for business balance, presets and unresolved loan repayment support.
2. Add service-level consolidated ledger and Business Balance calculation without deleting existing account rows.
3. Add Business Presets page under More/Management.
4. Centralize effective-dated rate lookup before changing Record Cashing behavior.
5. Hide or default collection destination to Airtel Money at the UI/service layer while preserving underlying accounts.
6. Add tests for negative balance, financing vs operating classifications, preset validation and rate effective dates.

Do not begin Step 2 until the Step 1 report is approved.
