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
- Returns: list-like result of dictionary rows with `id`, `registration_number`, `route_name`, `status`, `date_acquired`, `notes`.
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
- Purpose: List routes, create `Kitwe - Ndola`, then list routes again.
- Parameters: none.
- Returns: none.
- Database tables accessed through service:
  - `routes`
- Important validation: delegated to `add_route`.
- Exceptions:
  - may fail on duplicate route name because `routes.name` is unique.
- Safety note:
  - This is a data-changing script and should not run against the shared development database as a routine test.

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
- `services/driver_service.py`
- `services/assignment_service.py`
- `services/cashing_service.py`
- `services/expense_service.py`
- `services/finance_service.py`
- `services/maintenance_service.py`
- `services/reminder_service.py`
- `components/`
- `utils/formatting.py`
- `utils/dates.py`
- `utils/validation.py`
- Streamlit page modules

