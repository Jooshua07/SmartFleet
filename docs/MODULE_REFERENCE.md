# SmartFleet module reference

Last updated: 2026-10-11

This reference covers significant code functions that exist today, plus the installed PostgreSQL integrity functions that application services must respect. It should be updated after every implementation phase.

## Python modules

### `database.connection.get_connection`

- File: `database/connection.py`
- Purpose: Create a psycopg connection to the configured PostgreSQL database.
- Parameters: none.
- Returns: `psycopg.Connection`.
- Configuration: reads `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` from `.env` through `python-dotenv`.
- Database tables accessed: none directly.
- Validation: none.
- Exceptions: connection errors from psycopg if configuration or database access fails.
- Used by:
  - `services.route_service.get_all_routes`
  - `services.route_service.add_route`
  - `services.bus_service.get_all_buses`
  - current test scripts

### `services.route_service.get_all_routes`

- File: `services/route_service.py`
- Purpose: Return all routes ordered by name.
- Parameters: none.
- Returns: list-like result of dictionary rows with `id`, `name`, `description`, `active`.
- Database tables accessed: `routes`.
- Validation: none.
- Exceptions: psycopg/database exceptions.
- Used by:
  - `tests/test_route_service.py`
  - future route list UI.

### `services.route_service.add_route`

- File: `services/route_service.py`
- Purpose: Insert a route and return the created row.
- Parameters:
  - `name`: route name. Required after trimming.
  - `description`: optional route description.
- Returns: dictionary row with `id`, `name`, `description`, `active`.
- Database tables accessed: `routes`.
- Important validation:
  - strips whitespace from `name`.
  - raises `ValueError` when the trimmed name is empty.
  - database enforces unique route names.
- Exceptions:
  - `ValueError` for empty names.
  - psycopg/database exceptions for unique constraint or connection failures.
- Used by:
  - `tests/test_route_service.py`.
- Safety note:
  - Current test usage writes to the development database and is not safe as a routine baseline test.

### `services.bus_service.get_all_buses`

- File: `services/bus_service.py`
- Purpose: Return all buses with their route names.
- Parameters: none.
- Returns: list-like result of dictionary rows with `id`, `registration_number`, `route_name`, `status`, `model`, `seating_capacity`, `chassis_number`, `date_acquired`, `notes`.
- Database tables accessed:
  - `buses`
  - `routes`
- Important validation: none.
- Exceptions: psycopg/database exceptions.
- Used by:
  - `tests/test_bus_service.py`
  - future Buses page.
- Current behavior:
  - Uses an inner join. This is compatible with the current schema because every bus must have a route.
  - Does not include assigned driver information.

### `services.bus_service.get_buses_overview`

- File: `services/bus_service.py`
- Purpose: Return buses with route, date-aware active assignment, bus-detail and document-expiry context.
- Parameters:
  - `on_date`: optional date used for assignment validity.
  - `search`: optional search text.
  - `status`: optional `ACTIVE` or `INACTIVE` filter.
- Returns: list of dictionary rows.
- Database tables accessed:
  - `buses`
  - `routes`
  - `driver_assignments`
  - `driver_employments`
  - `drivers`
  - `bus_documents`
- Important validation: status filter is limited to known stored statuses.
- Exceptions: psycopg/database exceptions.
- Used by:
  - Buses page.
  - Record Cashing page.

### `services.bus_service.create_bus`

- File: `services/bus_service.py`
- Purpose: Create a bus record, optional bus document metadata and optional initial permanent assignment.
- Parameters:
  - `registration_number`
  - `route_id`
  - `status`
  - `date_acquired`
  - `notes`
  - `employment_id`
  - `model`
  - `seating_capacity`
  - `chassis_number`
  - `document_records`
- Returns: created bus row.
- Database tables accessed:
  - `buses`
  - `driver_assignments` when `employment_id` is supplied.
  - `bus_documents` when document records are supplied.
- Important validation:
  - registration number is required and uppercased.
  - status must be `ACTIVE` or `INACTIVE`.
  - seating capacity, when provided, must be a positive whole number.
  - document type must be supported.
- Exceptions:
  - `ValueError` for invalid input.
  - database exceptions for uniqueness, foreign keys or assignment constraints.
- Used by:
  - Add Bus page.

### `services.dashboard_service.get_financial_summary`

- File: `services/dashboard_service.py`
- Purpose: Return period revenue, expenses and pending remittance amounts.
- Parameters: `start_date`, `end_date`.
- Returns: dictionary with `revenue`, `expenses`, `pending_remittances`.
- Database tables accessed:
  - `remittances`
  - `remittance_collections`
  - `expenses`
- Important validation: none.
- Used by:
  - Home page.
  - Finance page.

### `services.dashboard_service.get_bus_status_counts`

- File: `services/dashboard_service.py`
- Purpose: Count active and inactive buses.
- Parameters: none.
- Returns: dictionary with `ACTIVE`, `INACTIVE`, `TOTAL`.
- Database tables accessed: `buses`.
- Used by: Home page.

### `services.dashboard_service.get_bus_performance`

- File: `services/dashboard_service.py`
- Purpose: Return bus-level revenue and bus-allocated expenses for a period.
- Parameters: `start_date`, `end_date`.
- Returns: list of dictionary rows.
- Database tables accessed:
  - `buses`
  - `remittances`
  - `remittance_collections`
  - `expenses`
  - `expense_allocations`
- Important validation: company-wide `GENERAL` expenses are not allocated to buses.
- Used by: Home page.

### `services.dashboard_service.get_recent_activity`

- File: `services/dashboard_service.py`
- Purpose: Return recent activity derived only from real domain records.
- Parameters: `limit`.
- Returns: list of dictionary rows.
- Database tables accessed:
  - `remittance_collections`
  - `expenses`
  - `maintenance`
- Used by:
  - Home page.
  - Finance page.

### `services.driver_service.get_available_driver_employments`

- File: `services/driver_service.py`
- Purpose: Return active driver employments without active permanent assignments on a date.
- Parameters: `on_date`.
- Returns: list of dictionary rows.
- Database tables accessed:
  - `drivers`
  - `driver_employments`
  - `driver_assignments`
- Used by: Add Bus page.

### `services.driver_service.get_drivers_overview`

- File: `services/driver_service.py`
- Purpose: Return driver, active employment and assigned bus summary rows.
- Parameters: none.
- Returns: list of dictionary rows.
- Database tables accessed:
  - `drivers`
  - `driver_employments`
  - `driver_assignments`
  - `buses`
- Used by: Buses page Drivers tab.

### `services.driver_service.create_driver`

- File: `services/driver_service.py`
- Purpose: Create a driver and an initial active employment record.
- Parameters:
  - `full_name`
  - `phone`
  - `address`
  - `next_of_kin_name`
  - `next_of_kin_phone`
  - `start_date`
  - `monthly_salary`
  - `notes`
- Returns: created driver row.
- Database tables accessed:
  - `drivers`
  - `driver_employments`
- Important validation:
  - driver name is required.
  - monthly salary cannot be negative.
- Used by: Buses page Drivers tab.

### `services.cashing_service.get_active_cashing_rates`

- File: `services/cashing_service.py`
- Purpose: Return active normal-day and Sunday cashing rates for a date.
- Parameters: `on_date`.
- Returns: dictionary keyed by `NORMAL_DAY` and `SUNDAY`.
- Database tables accessed: `cashing_rates`.
- Important validation:
  - raises `ValueError` when either required rate is missing.
- Used by: Record Cashing page and cashing write workflow.

### `services.cashing_service.get_active_financial_accounts`

- File: `services/cashing_service.py`
- Purpose: Return active accounts that can receive cashing.
- Parameters: none.
- Returns: list of account rows.
- Database tables accessed: `financial_accounts`.
- Used by: Record Cashing page.

### `services.cashing_service.get_recent_cashing_collections`

- File: `services/cashing_service.py`
- Purpose: Return recent cashing collection summaries.
- Parameters: `limit`.
- Returns: list of dictionary rows.
- Database tables accessed:
  - `remittance_collections`
  - `financial_accounts`
  - `remittances`
- Used by: Record Cashing page.

### `services.cashing_service.record_cashing_collection`

- File: `services/cashing_service.py`
- Purpose: Record one cashing collection, optional incoming ledger entry and one or more bus remittance rows in a single transaction.
- Parameters:
  - `collection_date`
  - `financial_account_id`
  - `entries`
  - `notes`
- Returns: created collection row.
- Database tables accessed:
  - `cashing_rates`
  - `financial_accounts`
  - `financial_transactions`
  - `remittance_collections`
  - `remittances`
- Important validation:
  - at least one bus entry must be included.
  - actual amounts cannot be negative.
  - day counts cannot be negative.
  - variance from expected cashing requires an explanation.
  - zero-total collections do not create zero-value ledger entries.
  - duplicate bus/date cashing entries are blocked before insert.
- Used by: Record Cashing page.

### `services.cashing_service.record_cashing_backfill`

- File: `services/cashing_service.py`
- Purpose: Record multiple cashing collection dates from the two-week backfill grid in one transaction.
- Parameters:
  - `financial_account_id`
  - `rows`
  - `notes`
- Returns: list of created collection rows.
- Database tables accessed:
  - `cashing_rates`
  - `financial_accounts`
  - `financial_transactions`
  - `remittance_collections`
  - `remittances`
- Important validation:
  - at least one row must be selected.
  - each selected bus/date pair can appear only once.
  - existing bus/date cashing records are blocked to prevent accidental duplicate backfill.
  - actual amounts, day counts and variance explanations follow the same rules as single collection recording.
- Used by: Record Cashing page two-week backfill mode.

### `services.finance_service.get_collections`

- File: `services/finance_service.py`
- Purpose: Return collection summaries for a period.
- Parameters: `start_date`, `end_date`.
- Returns: list of dictionary rows.
- Database tables accessed:
  - `remittance_collections`
  - `remittances`
- Used by: Finance page Collections tab.

### `services.finance_service.get_expenses`

- File: `services/finance_service.py`
- Purpose: Return expense ledger rows for a period.
- Parameters: `start_date`, `end_date`.
- Returns: list of dictionary rows.
- Database tables accessed:
  - `expenses`
  - `expense_categories`
  - `buses`
- Used by: Finance page Expenses tab.

### `services.finance_service.get_account_balances`

- File: `services/finance_service.py`
- Purpose: Calculate account balances from opening balances and ledger directions.
- Parameters: none.
- Returns: list of dictionary rows.
- Database tables accessed:
  - `financial_accounts`
  - `financial_transactions`
- Used by: Finance page Balances tab.

### `services.expense_service.get_active_expense_categories`

- File: `services/expense_service.py`
- Purpose: Return active expense categories for the Record Expense form.
- Parameters: none.
- Returns: list of category rows.
- Database tables accessed: `expense_categories`.
- Used by: Record Expense page.

### `services.expense_service.get_active_payment_accounts`

- File: `services/expense_service.py`
- Purpose: Return active financial accounts that can pay business expenses.
- Parameters: none.
- Returns: list of account rows.
- Database tables accessed: `financial_accounts`.
- Used by: Record Expense page.

### `services.expense_service.get_recent_expenses`

- File: `services/expense_service.py`
- Purpose: Return recent expense summaries.
- Parameters: `limit`.
- Returns: list of dictionary rows.
- Database tables accessed:
  - `expenses`
  - `expense_categories`
  - `financial_accounts`
  - `buses`
- Used by: Record Expense page.

### `services.expense_service.record_business_expense`

- File: `services/expense_service.py`
- Purpose: Record a business-account expense and matching outbound ledger entry in one transaction.
- Parameters:
  - `expense_date`
  - `category_id`
  - `amount`
  - `description`
  - `financial_account_id`
  - `scope`
  - `bus_id`
  - `notes`
- Returns: created expense row.
- Database tables accessed:
  - `expense_categories`
  - `financial_accounts`
  - `buses`
  - `financial_transactions`
  - `expenses`
- Important validation:
  - amount must be greater than zero.
  - description is required.
  - category and payment account must be active.
  - bus scope requires a valid bus.
  - only `GENERAL` and single `BUS` scope are supported today.
- Used by: Record Expense page.

### `services.reminder_service.get_due_maintenance`

- File: `services/reminder_service.py`
- Purpose: Return active maintenance schedules due by a reference date plus day window.
- Parameters: `reference_date`, `days`.
- Returns: list of dictionary rows.
- Database tables accessed:
  - `maintenance_schedules`
  - `buses`
- Used by: Reminders page.

### `services.reminder_service.get_deactivated_buses`

- File: `services/reminder_service.py`
- Purpose: Return inactive buses for reminder display.
- Parameters: none.
- Returns: list of dictionary rows.
- Database tables accessed: `buses`.
- Used by: Reminders page.

### `services.reminder_service.get_document_expiries`

- File: `services/reminder_service.py`
- Purpose: Return bus document records expiring by a reference date plus day window.
- Parameters: `reference_date`, `days`.
- Returns: list of dictionary rows.
- Database tables accessed:
  - `bus_documents`
  - `buses`
- Used by: Reminders page.

### `services.reminder_service.get_open_reminders`

- File: `services/reminder_service.py`
- Purpose: Return pending stored reminders, optionally limited.
- Parameters: `limit`.
- Returns: list of dictionary rows.
- Database tables accessed: `reminders`.
- Used by:
  - Home page.
  - Reminders page.

### UI and utility helpers

- `components.layout.render_app_header` renders the shared app header in `app.py`.
- `components.layout.render_bottom_navigation` renders Home, Buses, Finance and More actions in `st.bottom`.
- `components.layout.quick_action` renders navigation buttons in the More page.
- `components.cards.empty_state` renders consistent empty-state callouts.
- `components.cards.status_badge` renders status badges.
- `utils.dates.today_lusaka` returns the business date in Africa/Lusaka.
- `utils.dates.period_bounds` returns Week or Month reporting ranges.
- `utils.formatting.format_kwacha` and `format_whole_kwacha` format Zambian Kwacha values.
- `utils.formatting.format_date` formats dates for UI display.
- `utils.validation.clean_required_text`, `clean_optional_text`, `parse_optional_positive_int`, `parse_positive_amount` and `parse_non_negative_amount` validate common inputs.

## Test and inspection scripts

### `tests.test_connection.test_database_connection`

- File: `tests/test_connection.py`
- Purpose: Query public base tables and print their names.
- Parameters: none.
- Returns: none.
- Database tables accessed: `information_schema.tables`.
- Important validation: none.
- Exceptions: database connection/query failures.
- Notes:
  - Has no assertion beyond not raising an exception.
  - Works when run as `python -m tests.test_connection`.
  - Fails when run by path unless the project root is added to `PYTHONPATH`.

### `tests.test_bus_service.test_get_all_buses`

- File: `tests/test_bus_service.py`
- Purpose: Call `get_all_buses`, assert the result is a list and print rows.
- Parameters: none.
- Returns: none.
- Database tables accessed through service:
  - `buses`
  - `routes`
- Important validation:
  - Asserts returned object is a list.
- Exceptions: service/database exceptions.
- Notes:
  - Works when run as `python -m tests.test_bus_service`.
  - Fails when run by path unless the project root is added to `PYTHONPATH`.

### `tests.test_route_service.test_route_service`

- File: `tests/test_route_service.py`
- Purpose: List current routes without changing database data.
- Parameters: none.
- Returns: none.
- Database tables accessed through service:
  - `routes`
- Important validation: none.
- Safety note:
  - Earlier versions of this script wrote test route data to the development database.

### `tests/inspect_buses.py`

- File: `tests/inspect_buses.py`
- Purpose: Inspect buses and routes column metadata, buses constraints, status checks and existing routes.
- Parameters: none.
- Returns: none.
- Database tables accessed:
  - `information_schema.columns`
  - `pg_constraint`
  - `routes`
- Important validation: none.
- Exceptions: database query failures.

## PostgreSQL integrity functions

The following functions are installed in the `public` schema and are used by constraints/triggers or service-level validation. Their definitions live in `migrations/022_smartfleet_schema_v1_hardening_corrected.sql` unless otherwise noted.

| Function | Purpose | Main tables involved |
| --- | --- | --- |
| `sf_suggest_transfer_fee(p_type text, p_amount numeric)` | Returns the configured transfer fee for a transfer type and amount | `transfer_fee_rules` |
| `sf_is_external_transfer(p_financial_tx_id integer)` | Determines whether a financial transaction is linked to an external transfer | `financial_transactions`, `transfers` |
| `sf_assert_transfer(p_id integer)` | Validates transfer ledger relationships and fee handling | `transfers`, `financial_transactions`, `transfer_fee_rules` |
| `sf_assert_expense(p_id integer)` | Validates expense payment source, owner funding and ledger links | `expenses`, `financial_transactions`, `owner_loan_transactions`, `expense_allocations` |
| `sf_assert_collection(p_id integer)` | Validates remittance collection totals and linked inbound ledger entry | `remittance_collections`, `remittances`, `financial_transactions` |
| `sf_assert_advance(p_id integer)` | Validates driver advance payment links | `driver_advances`, `financial_transactions`, `driver_employments` |
| `sf_assert_deduction(p_id integer)` | Validates driver deduction records and allocations | `driver_deductions`, `salary_deduction_allocations` |
| `sf_assert_salary(p_id integer)` | Validates salary payment, recoveries and deductions | `driver_salaries`, `financial_transactions`, `salary_advance_recoveries`, `salary_deduction_allocations` |
| `sf_assert_owner_loan_transaction(p_id integer)` | Validates owner funding and repayment links | `owner_loan_transactions`, `owner_loans`, `expenses`, `financial_transactions` |
| `sf_assert_owner_balance(p_id integer)` | Validates owner loan balance rules | `owner_loans`, `owner_loan_transactions` |
| `sf_assert_loan_repayment(p_id integer)` | Validates business loan repayment source and link consistency | `loan_repayments`, `business_loans`, `financial_transactions`, `owner_loan_transactions` |
| `sf_assert_business_loan(p_id integer)` | Validates business loan balance and status rules | `business_loans`, `loan_repayments` |
| `sf_assert_employment(p_id integer)` | Validates employment and assignment compatibility | `driver_employments`, `driver_assignments` |
| `sf_assert_maintenance(p_id integer)` | Validates maintenance dates, cost linkage and matching-bus expense links | `maintenance`, `expenses` |
| `sf_assert_ledger(p_id integer)` | Validates financial transaction ledger relationships | `financial_transactions` plus linked domain tables |
| `sf_assert_rate(p_id integer)` | Validates cashing rate overlap rules | `cashing_rates` |
| `sf_assert_fee_rule(p_id integer)` | Validates transfer fee rule overlap rules | `transfer_fee_rules` |
| `sf_integrity_deferred()` | Shared deferred constraint trigger dispatcher | Most financial and operational tables |
| `sf_preserve_account_type()` | Prevents changing a financial account type after creation | `financial_accounts` |
| `sf_touch_updated_at()` | Updates `updated_at` before row updates | most mutable tables |

## Missing modules

The following modules are planned but do not exist yet:

- `database/transactions.py`
- `database/repositories.py` or table-specific data-access modules
- `services/assignment_service.py`
- `services/maintenance_service.py`
- Streamlit browser/mobile verification tests
