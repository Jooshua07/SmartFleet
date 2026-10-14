# SmartFleet module reference

## Step 4 modules

- `utils.reporting_periods.reporting_period`: calendar month-to-date, 3/6 calendar months and validated custom dates.
- `scheduled_chart_dates`: Thursday/Sunday axis dates, without creating transactions.
- `components.reporting_period.period_controls`: reusable independent state.
- `finance_service.get_period_balance/get_period_ledger/summarize_ledger`: chronological, transfer-neutral consolidated cash.
- `performance_service.get_business_financial_timeline/build_financial_timeline`: cumulative operating series and actual cash balance, with trailing endpoint.
- `dashboard_charts.build_financial_chart_data/build_financial_chart`: three lines, adaptive scale, zero reference and hover data.
- `maintenance_service`: schedules, warning thresholds, atomic paid/zero-cost completion and audited historical corrections.
- `components.servicing_form`: shared bus-specific and More entry form; `app_pages/record_servicing.py` includes history/correction.
- `business_report_service`: period report, historical status days, ledger reconciliation and quality checks.
- `report_export_service`: five CSV/Excel summaries; workbook formats dates/money and keeps user text literal.
- `scripts/smoke_step4.py`, `smoke_step4_pages.py`, `smoke_step4_ui.py`, `verify_step4_backup.py`, `verify_step4_live.py`: disposable financial scenarios, read-only UI, restore and preservation evidence.

The older business-performance helpers below remain for existing callers/tests; Home now uses the new financial timeline.

Last updated: 2026-10-13

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

### `services.bus_service.get_bus_details`

- File: `services/bus_service.py`
- Purpose: Return one bus plus status history, route history and document metadata for edit/detail workflows.
- Parameters: `bus_id`.
- Returns: dictionary with `bus`, `status_history`, `route_history` and `documents`.
- Database tables accessed:
  - `buses`
  - `routes`
  - `bus_status_history`
  - `bus_route_history`
  - `bus_documents`
- Important validation:
  - raises `ValueError` if the bus does not exist.
- Used by: Buses page edit workflow.

### `services.bus_service.update_bus`

- File: `services/bus_service.py`
- Purpose: Edit bus identity/details and optionally record an effective-dated route change.
- Parameters:
  - `bus_id`
  - `registration_number`
  - `route_id`
  - `route_effective_date`
  - `model`
  - `seating_capacity`
  - `chassis_number`
  - `date_acquired`
  - `notes`
- Returns: updated bus row.
- Database tables accessed:
  - `buses`
  - `routes`
  - `bus_route_history`
- Important validation:
  - registration number is required and uppercased.
  - route must exist.
  - route changes require an effective date.
  - seating capacity, when provided, must be a positive whole number.
- Used by: Buses page edit workflow.

### `services.bus_service.set_bus_status`

- File: `services/bus_service.py`
- Purpose: Deactivate or reactivate a bus using an effective-dated status history row.
- Parameters:
  - `bus_id`
  - `status`
  - `effective_date`
  - `reason`
- Returns: updated bus row.
- Database tables accessed:
  - `buses`
  - `bus_status_history`
- Important validation:
  - status must be `ACTIVE` or `INACTIVE`.
  - effective date is required.
  - avoids duplicate same-day same-status history rows.
- Used by: Buses page status workflow and smart cashing history calculations.

### `services.bus_service.count_active_days_from_history`

- File: `services/bus_service.py`
- Purpose: Pure helper that counts active days in an inclusive date range from status-history rows.
- Parameters: `history_rows`, `start_date`, `end_date`.
- Returns: integer active-day count.
- Important validation:
  - end date must be on or after start date.
- Used by: fleet-history tests and smart cashing expectations.

### `services.bus_service.get_bus_active_day_counts`

- File: `services/bus_service.py`
- Purpose: Return active-day counts per bus for an inclusive period using `bus_status_history`.
- Parameters:
  - `start_date`
  - `end_date`
  - optional `bus_ids`
- Returns: dictionary keyed by bus id.
- Database tables accessed:
  - `buses`
  - `bus_status_history`
- Used by: `services.smart_cashing_service.get_smart_cashing_preview`.

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
  - `bus_status_history`
  - `bus_route_history`
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
- Purpose: Return period recorded revenue, recorded operating costs and pending remittance amounts.
- Parameters: `start_date`, `end_date`.
- Returns: dictionary with `revenue`, `expenses`, `pending_remittances`.
- Database tables accessed:
  - `remittances`
  - `remittance_collections`
  - `financial_transactions`
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
- Purpose: Return bus-level recorded revenue and attributed operating costs for a period by delegating to Bus Accounts calculations.
- Parameters: `start_date`, `end_date`.
- Returns: list of dictionary rows.
- Database tables accessed through `services.bus_account_service.get_bus_contribution_summary`.
- Important validation: company-wide `GENERAL` expenses are not allocated to buses.
- Used by: Home page.

### `services.bus_account_service.get_bus_contribution_summary`

- File: `services/bus_account_service.py`
- Purpose: Return Bus Accounts comparison data for a period.
- Parameters: `start_date`, `end_date`.
- Returns: dictionary with `buses` and `shared_general_costs`.
- Database tables accessed:
  - `buses`
  - `remittances`
  - `remittance_collections`
  - `expenses`
  - `expense_allocations`
- Important behavior:
  - bus revenue comes only from remittance rows attributed to that bus.
  - direct bus expenses use `expenses.scope = 'BUS'`.
  - verified allocations use `expense_allocations` for `MULTI_BUS` expenses.
  - shared `GENERAL` expenses are summed separately and are not divided across buses.
  - recorded bus contribution equals recorded bus revenue minus attributed bus operating costs.
- Used by: Bus Accounts page and Home bus-performance wrapper.

### `services.bus_account_service.get_bus_account_detail`

- File: `services/bus_account_service.py`
- Purpose: Return detail data for one bus in Bus Accounts.
- Parameters: `bus_id`, `start_date`, `end_date`.
- Returns: dictionary with `bus`, `trend`, `costs_by_category` and `recent_transactions`.
- Database tables accessed:
  - `buses`
  - `remittances`
  - `remittance_collections`
  - `expenses`
  - `expense_categories`
  - `expense_allocations`
- Used by: Bus Accounts page.

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

### `services.driver_service.get_driver`

- File: `services/driver_service.py`
- Purpose: Return one driver record for editing.
- Parameters: `driver_id`.
- Returns: driver dictionary row.
- Database tables accessed: `drivers`.
- Important validation:
  - raises `ValueError` if the driver does not exist.
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

### `services.driver_service.update_driver`

- File: `services/driver_service.py`
- Purpose: Edit driver profile/contact fields.
- Parameters:
  - `driver_id`
  - `full_name`
  - `phone`
  - `address`
  - `next_of_kin_name`
  - `next_of_kin_phone`
  - `notes`
- Returns: updated driver row.
- Database tables accessed: `drivers`.
- Important validation:
  - driver name is required.
  - driver must exist.
- Used by: Buses page Drivers tab.

### `services.cashing_service.get_active_financial_accounts`

- File: `services/cashing_service.py`
- Purpose: Return active financial accounts. This remains available for legacy/account views; new cashing entries use the Airtel Money preset destination.
- Parameters: none.
- Returns: list of account rows.
- Database tables accessed: `financial_accounts`.
- Used by: legacy helpers and future account selectors.

### `services.cashing_service.get_collection_destination_account`

- File: `services/cashing_service.py`
- Purpose: Return the active Airtel Money account configured for cashing collections.
- Parameters: none.
- Returns: dictionary row with `id`, `name`, `account_type`.
- Database tables accessed:
  - `business_settings`
  - `financial_accounts`
- Important validation:
  - raises `ValueError` if the configured collection account type has no active account.
- Used by: Record Cashing page.

### `services.cashing_service.get_cashing_rates_for_date`

- File: `services/cashing_service.py`
- Purpose: Return effective normal-day and Sunday cashing rates for a date.
- Parameters: `on_date`.
- Returns: dictionary keyed by `NORMAL_DAY` and `SUNDAY`.
- Database tables accessed: `cashing_rates`.
- Important validation:
  - raises `ValueError` if either rate is missing.

### `services.smart_cashing_service.get_collection_coverage`

- File: `services/smart_cashing_service.py`
- Purpose: Convert a Sunday or Thursday collection date into the period that cashing should cover.
- Parameters: `collection_date`.
- Returns: dictionary with `collection_type`, `coverage_start`, `coverage_end` and optional `previous_sunday`.
- Important validation:
  - only Sunday and Thursday collection dates are accepted.

### `services.smart_cashing_service.get_smart_cashing_preview`

- File: `services/smart_cashing_service.py`
- Purpose: Build the Record Cashing preview from coverage, effective rates and bus active-day history.
- Parameters: `collection_date`.
- Returns: dictionary containing coverage, rates, eligible buses and expected total.
- Database tables accessed:
  - `cashing_rates`
  - `bus_status_history`
  - `buses`
  - `routes`
  - `driver_assignments`
  - `driver_employments`
  - `drivers`
- Used by: Record Cashing page.

### `services.smart_cashing_service.build_standard_allocations`

- File: `services/smart_cashing_service.py`
- Purpose: Build expected per-bus allocations from the preview when the owner enters one actual received amount.
- Parameters:
  - `preview`
  - `selected_bus_ids`
  - `sunday_bus_ids`
  - `total_received`
  - optional `difference_classification`
- Returns: dictionary with `entries`, `expected_total`, `unallocated_amount` and `difference_classification`.
- Important validation:
  - at least one eligible bus must be selected.
  - actual received amount cannot be negative.
  - negative differences remain explicit unallocated shortages instead of being silently split across buses.

### `services.smart_cashing_service.record_smart_cashing_collection`

- File: `services/smart_cashing_service.py`
- Purpose: Record one smart cashing receipt, expected allocations, optional unallocated difference and confirmed unpaid obligations in one transaction.
- Parameters:
  - `collection_date`
  - `financial_account_id`
  - `total_received`
  - `entries`
  - `unallocated_amount`
  - `difference_classification`
  - `cashing_mode`
  - `notes`
- Returns: created collection row.
- Database tables accessed:
  - `financial_accounts`
  - `financial_transactions`
  - `remittance_collections`
  - `remittances`
  - `cashing_obligations`
- Important validation:
  - cashing must be paid into Airtel Money.
  - at least one bus entry is required.
  - allocations plus unallocated amount must equal the actual receipt.
  - duplicate bus/date cashing rows are blocked.
  - confirmed unpaid obligations require a responsible party.
- Used by: Record Cashing page.

### `services.smart_cashing_service.update_smart_cashing_collection`

- File: `services/smart_cashing_service.py`
- Purpose: Correct an unlocked smart cashing collection, its ledger receipt and bus allocations in one transaction.
- Parameters:
  - `collection_id`
  - `collection_date`
  - `financial_account_id`
  - `total_received`
  - `entries`
  - `unallocated_amount`
  - `difference_classification`
  - `cashing_mode`
  - `notes`
- Returns: updated collection row.
- Database tables accessed:
  - `financial_accounts`
  - `financial_transactions`
  - `remittance_collections`
  - `remittances`
  - `cashing_obligations`
  - `cashing_obligation_payments`
- Important validation:
  - direct cashing records must use the direct editor.
  - records with obligations or payments cannot be corrected in place.
  - allocations plus unallocated amount must equal the actual receipt.
  - duplicate bus/date cashing rows are blocked, excluding the collection being corrected.
  - confirmed unpaid obligations require a responsible party.
- Used by: Record Cashing page correction workflow.

### `services.smart_cashing_service.record_obligation_payment`

- File: `services/smart_cashing_service.py`
- Purpose: Record a later payment against a confirmed cashing obligation.
- Parameters:
  - `obligation_id`
  - `payment_date`
  - `amount`
  - `financial_account_id`
  - `notes`
- Returns: created obligation-payment row.
- Database tables accessed:
  - `cashing_obligations`
  - `financial_accounts`
  - `financial_transactions`
  - `cashing_obligation_payments`
- Important validation:
  - payment amount must be greater than zero.
  - voided or already-settled obligations cannot receive payments.
  - payment cannot exceed the outstanding amount.
  - payment must be paid into Airtel Money.

### `services.smart_cashing_service.list_open_cashing_obligations`

- File: `services/smart_cashing_service.py`
- Purpose: Return open or partially settled cashing obligations for the Record Cashing payment section.
- Parameters: optional `limit`.
- Returns: list of obligation rows with collection, bus, paid and outstanding context.
- Database tables accessed:
  - `cashing_obligations`
  - `cashing_obligation_payments`
  - `remittance_collections`
  - `remittances`
  - `buses`
- Used by: Record Cashing page.

### `services.smart_cashing_service.get_cashing_obligations_for_collection`

- File: `services/smart_cashing_service.py`
- Purpose: Return obligations linked to one cashing collection for the smart-cashing details view.
- Parameters: `collection_id`.
- Returns: list of obligation rows with bus, paid and outstanding context.
- Database tables accessed:
  - `cashing_obligations`
  - `cashing_obligation_payments`
  - `remittances`
  - `buses`
- Used by: Record Cashing page details workflow.

### `services.smart_cashing_service.list_cashing_obligation_payments`

- File: `services/smart_cashing_service.py`
- Purpose: Return payment history for one cashing obligation.
- Parameters: `obligation_id`.
- Returns: list of payment rows with date, amount, account and notes.
- Database tables accessed:
  - `cashing_obligation_payments`
  - `financial_accounts`
- Used by: Record Cashing page details workflow.

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

### `services.cashing_service.record_direct_cashing_collection`

- File: `services/cashing_service.py`
- Purpose: Record one direct cashing collection, matching incoming ledger entry and one or more bus remittance rows in a single transaction.
- Parameters:
  - `collection_date`
  - `financial_account_id`
  - `entries`
  - `notes`
- Returns: created collection row.
- Database tables accessed:
  - `financial_accounts`
  - `financial_transactions`
  - `remittance_collections`
  - `remittances`
- Important validation:
  - at least one bus entry must be included.
  - every selected bus must have a positive direct amount.
  - actual and Sunday amounts cannot be negative.
  - duplicate bus/date cashing entries are blocked before insert.
  - the account must match the configured Airtel Money collection destination.
- Used by: Record Cashing page.

### `services.cashing_service.update_direct_cashing_collection`

- File: `services/cashing_service.py`
- Purpose: Replace an existing direct cashing collection and update its linked incoming ledger entry in one transaction.
- Parameters:
  - `collection_id`
  - `collection_date`
  - `financial_account_id`
  - `entries`
  - `notes`
- Returns: updated collection row.
- Database tables accessed:
  - `financial_accounts`
  - `financial_transactions`
  - `remittance_collections`
  - `remittances`
- Important validation:
  - collection must exist.
  - at least one bus entry must remain included.
  - duplicate bus/date cashing entries are blocked, excluding the collection being edited.
  - the account must match the configured Airtel Money collection destination.
- Used by: Record Cashing page edit workflow.

### `services.cashing_service.delete_cashing_collection`

- File: `services/cashing_service.py`
- Purpose: Delete a cashing collection, its remittance rows and its linked incoming ledger entry.
- Parameters: `collection_id`.
- Returns: none.
- Database tables accessed:
  - `financial_transactions`
  - `remittance_collections`
  - `remittances`
  - `cashing_obligations`
- Important validation:
  - collection must exist.
  - collections with active cashing obligations are not deleted.
- Used by: Record Cashing page delete workflow.

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
- Used by: backend/reporting compatibility only; the visible Finance Balances page now shows consolidated Business Balance instead of individual account balance cards.

### `services.finance_service.get_business_balance`

- File: `services/finance_service.py`
- Purpose: Return consolidated Business Balance from ledger movement on or after the reporting baseline.
- Parameters: none.
- Returns: dictionary with baseline date, money in, money out, business balance, collections, operating payments, financing in and financing out.
- Database tables accessed:
  - `business_settings`
  - `financial_transactions`
- Important behavior:
  - inbound transactions increase the balance.
  - outbound transactions reduce the balance.
  - the balance can be negative.
  - loan repayments are classified as financing payments.
  - recoverable driver advances are not counted as operating payments.
- Used by: Finance page Balances tab.

### `services.finance_service.get_business_ledger`

- File: `services/finance_service.py`
- Purpose: Return recent ledger rows with signed amounts and business classifications.
- Parameters: `limit`.
- Returns: list of dictionary rows.
- Database tables accessed:
  - `business_settings`
  - `financial_transactions`
  - `financial_accounts`
- Used by: Finance page Balances tab.

### `services.preset_service`

- File: `services/preset_service.py`
- Purpose: Manage Business Presets without deleting historical data.
- Main functions:
  - `get_business_settings`
  - `get_reporting_baseline_date`
  - `set_reporting_baseline_date`
  - `get_default_collection_account_type`
  - `list_cashing_rates`
  - `get_effective_cashing_rates`
  - `set_cashing_rate`
  - `list_cashing_schedule_rules`
  - `list_driver_salary_presets`
  - `set_driver_salary_preset`
  - `list_reminder_presets`
  - `set_reminder_preset`
- Database tables accessed:
  - `business_settings`
  - `business_preset_audit`
  - `cashing_rates`
  - `cashing_schedule_rules`
  - `driver_salary_presets`
  - `reminder_presets`
  - `drivers`
- Important validation:
  - rate and salary updates create new effective-dated rows and close the prior active window.
  - overlapping active effective dates are rejected before database insert.
  - preset changes are audited.
- Used by: Business Presets page, Record Cashing page and Finance page.

### `services.loan_service.record_unidentified_business_loan_repayment`

- File: `services/loan_service.py`
- Purpose: Record a business-account loan repayment even when the original loan record is not known yet.
- Parameters:
  - `repayment_date`
  - `amount`
  - `financial_account_id`
  - `paid_to`
  - `notes`
- Returns: created loan repayment row.
- Database tables accessed:
  - `financial_accounts`
  - `financial_transactions`
  - `loan_repayments`
- Important validation:
  - amount must be positive.
  - paid-to and notes are required.
  - ledger transaction type is `LOAN_REPAYMENT` and direction is `OUT`.
- Used by: compatibility callers and the dedicated Loans workflow.

### `services.driver_money_service`

- File: `services/driver_money_service.py`
- Purpose: Manage driver salary previews, salary advances, recovery allocation and payroll records without mixing them into ordinary expenses.
- Main functions:
  - `list_driver_money_profiles`
  - `get_driver_money_detail`
  - `get_salary_preview`
  - `record_driver_advance`
  - `record_driver_salary`
  - `cancel_driver_salary`
  - `reclassify_expense_as_driver_salary`
- Database tables accessed:
  - `drivers`
  - `driver_employments`
  - `driver_assignments`
  - `driver_salary_presets`
  - `driver_advances`
  - `driver_salaries`
  - `salary_advance_recoveries`
  - `salary_deduction_allocations`
  - `financial_accounts`
  - `financial_transactions`
  - `expenses`
  - `expense_allocations`
- Important validation:
  - salary periods use actual employment dates and effective salary presets.
  - outstanding advances are recovered oldest-first and cannot be recovered twice.
  - net salary cannot become negative.
  - the configurable outstanding advance limit defaults to K1,000 and applies cumulatively per employment.
  - salary operating cost is recognized from the salary record once; advance disbursements are recoverable cash movements, not extra salary expense.
- Used by: Driver Money page and controlled historical salary correction helpers.

### `services.loan_service`

- File: `services/loan_service.py`
- Purpose: Manage business loans, repayments, owner drawings, owner loans to the business, owner-paid external loan settlement and historical loan reclassification.
- Main functions:
  - `list_business_loans`
  - `add_business_loan`
  - `list_loan_repayments`
  - `record_loan_repayment`
  - `record_owner_drawing`
  - `record_owner_loan_to_business`
  - `record_business_repayment_to_owner`
  - `get_owner_money_summary`
  - `reclassify_expense_as_loan_repayment`
- Database tables accessed:
  - `business_loans`
  - `loan_repayments`
  - `owner_loans`
  - `owner_loan_transactions`
  - `financial_accounts`
  - `financial_transactions`
  - `expenses`
  - `expense_allocations`
- Important validation:
  - loan principal repayments are financing payments, not ordinary operating expenses.
  - owner-paid lender repayments do not create a business cash movement.
  - owner drawings reduce Business Balance but do not create an owner loan payable.
  - business repayments to the owner cannot exceed the outstanding owner balance.
  - known loan repayments cannot overpay recorded principal unless separate fees/interest are recorded.
- Used by: Loans page, Owner Money page, Record Expense shortcuts and historical loan correction helpers.

### `services.performance_service`

- File: `services/performance_service.py`
- Purpose: Provide one centralized operating-performance definition for Home and summary reporting.
- Main functions:
  - `get_operating_summary`
  - `get_business_performance_series`
- Database tables accessed:
  - `remittance_collections`
  - `remittances`
  - `expenses`
  - `expense_categories`
  - `driver_salaries`
  - `financial_transactions`
- Important behavior:
  - revenue is counted from gross cashing collections and is not duplicated through bus remittance rows.
  - operating expenses include ordinary operating expenses and salary expense recognized through payroll.
  - loan principal, owner drawings, owner loans, owner repayments, internal transfers and driver advance disbursements are excluded from operating expenses.
  - daily series fills missing dates with zero values.
  - weekly series uses Monday-based intervals with a partial first week beginning at the reporting baseline.
- Used by: Home page and `services.dashboard_service.get_financial_summary`.

### `services.expense_service.get_active_expense_categories`

- File: `services/expense_service.py`
- Purpose: Return all active expense categories.
- Parameters: none.
- Returns: list of category rows.
- Database tables accessed: `expense_categories`.
- Used by: service helpers and compatibility callers.

### `services.expense_service.get_operating_expense_categories`

- File: `services/expense_service.py`
- Purpose: Return active categories that are safe for ordinary expense recording.
- Parameters: none.
- Returns: list of category rows excluding driver advances, driver salaries, loan repayments and owner drawings.
- Database tables accessed: `expense_categories`.
- Used by: Record Expense page.

### `services.expense_service.get_active_payment_accounts`

- File: `services/expense_service.py`
- Purpose: Return active financial accounts that can pay business expenses.
- Parameters: none.
- Returns: list of account rows.
- Database tables accessed: `financial_accounts`.
- Used by: compatibility/future workflows; ordinary Record Expense no longer exposes a Paid From selector.

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
  - `description` (used as Expense Title)
  - optional `financial_account_id`; omitted values use the configured default business payment account.
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
  - Expense Title is required, at most five words and at most 35 characters.
  - category must be active and must not be a restricted financial category.
  - payment account must be active, selected internally from business settings when omitted.
  - bus scope requires a valid bus.
  - general scope cannot be linked to one bus.
  - only `GENERAL` and single `BUS` scope are supported today.
- Used by: Record Expense page.

### `services.expense_service.update_business_expense`

- File: `services/expense_service.py`
- Purpose: Update a business-account expense and its existing linked ledger entry without creating a duplicate payment.
- Parameters: same core fields as `record_business_expense`, plus `expense_id`.
- Database tables accessed:
  - `expenses`
  - `expense_categories`
  - `financial_accounts`
  - `buses`
  - `financial_transactions`
- Important validation:
  - only business-account expenses can be edited here.
  - existing overlong titles can be preserved unchanged, but new/changed titles must meet the current title limit.
  - switching between General Business and Specific Bus updates the expense classification while preserving one linked ledger transaction.

### `services.account_service.get_default_business_payment_account`

- File: `services/account_service.py`
- Purpose: Resolve the active internal business payment account from Business Presets.
- Parameters: none.
- Returns: account row with `id`, `name`, `account_type`.
- Database tables accessed:
  - `business_settings`
  - `financial_accounts`
- Used by: ordinary Expense service.

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
- Purpose: Query public base tables and assert the core SmartFleet tables exist.
- Parameters: none.
- Returns: none.
- Database tables accessed: `information_schema.tables`.
- Important validation:
  - asserts that `buses`, `routes` and `financial_accounts` exist.
- Exceptions: database connection/query failures.
- Notes: read-only database check.

### `tests.test_bus_service.test_get_all_buses`

- File: `tests/test_bus_service.py`
- Purpose: Call `get_all_buses` and assert returned rows have the expected shape.
- Parameters: none.
- Returns: none.
- Database tables accessed through service:
  - `buses`
  - `routes`
- Important validation:
  - asserts returned object is a list.
  - asserts each row contains `id`, `registration_number`, `route_name` and `status`.
- Exceptions: service/database exceptions.
- Notes: read-only database check.

### `tests.test_fleet_history`

- File: `tests/test_fleet_history.py`
- Purpose: Validate fleet edit/status-history behavior without live database writes.
- Important validation:
  - mid-period deactivation reduces active-day counts.
  - reactivation restores later active-day counts.
  - invalid status is rejected.
  - bus route changes require an effective date.

### `tests.test_route_service.test_route_service`

- File: `tests/test_route_service.py`
- Purpose: List current routes and assert returned rows have the expected shape.
- Parameters: none.
- Returns: none.
- Database tables accessed through service:
  - `routes`
- Important validation:
  - asserts returned object is a list.
  - asserts each row contains `id`, `name` and `active`.
- Notes: read-only database check.

### `tests.test_cashing_form`

- File: `tests/test_cashing_form.py`
- Purpose: Validate the direct cashing form helper used by the Record Cashing page.
- Important validation:
  - one-bus entries.
  - multi-bus entries.
  - missing bus selection.
  - missing/zero amounts.
  - form state clearing.

### `tests.test_cashing_service`

- File: `tests/test_cashing_service.py`
- Purpose: Validate direct cashing service cleaning and duplicate-message helpers without writing database data.
- Important validation:
  - normal plus Sunday amount handling.
  - zero and negative amount rejection.
  - selected-row filtering.
  - date coercion.
  - Airtel Money collection destination selection.

### `tests.test_smart_cashing_service`

- File: `tests/test_smart_cashing_service.py`
- Purpose: Validate smart cashing calculations and validation without live database writes.
- Important validation:
  - Sunday collections cover Thursday through Saturday.
  - Thursday collections cover Monday through Wednesday plus an optional previous Sunday.
  - standard allocations use K600 normal-day and K300 Sunday expectations.
  - shortages stay explicit as unallocated negative amounts.
  - surplus classification is automatic.
  - unsupported shortage classification is rejected.
  - obligation payments must be positive before database work begins.
  - smart corrections require bus entries before database work begins.

### `tests.test_financial_foundation`

- File: `tests/test_financial_foundation.py`
- Purpose: Validate Step 2 financial foundation behavior without live database writes.
- Important validation:
  - Business Balance can go negative.
  - loan repayments are classified as financing payments.
  - recoverable driver advances are classified separately from operating expenses.
  - effective-dated cashing rate updates preserve the previous rate window.
  - overlapping cashing-rate effective dates are rejected.
  - unidentified loan repayments require notes.

### `tests.test_driver_money_service`

- File: `tests/test_driver_money_service.py`
- Purpose: Validate driver salary-period and advance-recovery helpers without live database writes.
- Important validation:
  - salary month bounds.
  - mid-month employment proration days.
  - FIFO recovery allocation.
  - recovery over-allocation rejection.

### `tests.test_business_performance`

- File: `tests/test_business_performance.py`
- Purpose: Validate Home business-performance aggregation helpers and chart data.
- Important validation:
  - daily zero-activity dates.
  - weekly partial first week from the reporting baseline.
  - three chart lines: Revenue, Operating Expenses and Net Profit/Loss.
  - negative net values are preserved for the chart.

### `tests.test_money_management_pages`

- File: `tests/test_money_management_pages.py`
- Purpose: Use Streamlit AppTest to exercise the Driver Money, Loans and Owner Money pages with mocked realistic records.
- Important validation:
  - Driver Money shows salary preview, outstanding advances and salary history.
  - advance mode shows one focused advance form.
  - Loans shows repayment, loan list and repayment history.
  - Add Loan accepts unknown optional terms.
  - Owner Money exposes owner drawing, owner loan, owner-paid lender payment and business repayment workflows as distinct choices.

### `scripts.verify_migrations`

- File: `scripts/verify_migrations.py`
- Purpose: Create a disposable PostgreSQL database, apply all numbered migrations and drop the database afterward.
- Parameters: none.
- Returns: console output with the number of applied migrations.
- Important validation:
  - uses `.env` connection settings.
  - targets a generated database name beginning with `smartfleet_verify_`.

### `scripts.smoke_smart_cashing`

- File: `scripts/smoke_smart_cashing.py`
- Purpose: Run a disposable end-to-end smart cashing smoke check.
- Important validation:
  - creates a temporary PostgreSQL database.
  - applies all numbered migrations.
  - inserts one route and bus.
  - records one K1,800 smart cashing collection.
  - corrects the same collection to K1,700.
  - verifies one matching inbound `CASHING` ledger receipt.
  - drops the temporary database.

### `scripts.smoke_expense_finance`

- File: `scripts/smoke_expense_finance.py`
- Purpose: Run a disposable end-to-end expense, Bus Accounts and Finance classification smoke check.
- Important validation:
  - creates a temporary PostgreSQL database.
  - applies all numbered migrations.
  - inserts two test buses.
  - records K4,000 AIH bushes and K4,000 AIH tyres as bus-specific costs.
  - records K3,000 brake pads, K2,000 air filters and K2,535 oil filters as shared/general maintenance costs.
  - records a K15,000 loan repayment through the loan workflow.
  - verifies AIH attributed costs, AIF unaffected costs, shared general costs, Business Balance, operating payments and financing-out totals.
  - drops the temporary database.

### `scripts.smoke_money_workflows`

- File: `scripts/smoke_money_workflows.py`
- Purpose: Run a disposable end-to-end check for payroll, advances, loans, owner money and operating-performance classification.
- Important validation:
  - applies all numbered migrations.
  - creates a route, driver, employment and bus assignment.
  - records a K1,000 driver advance against a K2,500 salary.
  - verifies the advance cap blocks excess outstanding advances.
  - records salary with recovery and verifies salary cost is counted once.
  - adds a business loan, records business-funded and owner-funded repayments.
  - verifies owner-paid lender repayment does not move business cash.
  - records owner drawing and business repayment to owner.
  - verifies operating summary excludes loan principal, owner principal movements and driver advance disbursement.

### `tests.test_record_cashing_page`

- File: `tests/test_record_cashing_page.py`
- Purpose: Use Streamlit AppTest to exercise the Record Cashing page with mocked bus/account data.
- Important validation:
  - page starts with smart cashing controls.
  - Standard mode shows one actual-received input.
  - Backfill mode reveals a date selector.
  - Adjust Buses mode shows per-bus worked-day and allocation inputs.
  - recent smart collections show received, expected and difference metrics.
  - open obligations show a record-payment action.
  - users can open a smart correction form from a recent smart record.
  - smart records with obligations show correction/delete lock messaging.
  - smart detail view shows payment history under obligations.

### `tests.test_dashboard_charts`

- File: `tests/test_dashboard_charts.py`
- Purpose: Validate chart preparation for bus accounts and business performance.
- Important validation:
  - amounts remain on the correct Kwacha scale.
  - chart y-axis starts from zero.
  - business-performance data keeps Revenue, Operating Expenses and Net Profit/Loss as separate lines.
  - negative net values are preserved for chart scaling.

### `tests.test_expense_service`

- File: `tests/test_expense_service.py`
- Purpose: Validate expense service input checks that run before database writes.
- Important validation:
  - positive amount required.
  - Expense Title required.
  - title limits are enforced without destructively truncating existing long titles.
  - bus expenses require a bus.
  - general expenses cannot be linked to one bus.
  - default business payment account is used when no account is supplied.
  - restricted financial categories cannot be saved as ordinary expenses.
  - scope changes keep one existing financial payment.

### `tests.test_record_expense_page`

- File: `tests/test_record_expense_page.py`
- Purpose: Use Streamlit AppTest to exercise the Record Expense page with mocked category, bus and expense data.
- Important validation:
  - Paid From is not exposed in the everyday expense UI.
  - General Business and Specific Bus scope selector is visible.
  - Specific Bus reveals active and deactivated buses for historical edits.
  - recent expense cards use the Expense Title as the prominent text.

### `tests.test_bus_account_service`

- File: `tests/test_bus_account_service.py`
- Purpose: Validate Bus Accounts calculations without live database writes.
- Important validation:
  - shared/general costs stay separate.
  - bus-attributed costs remain assigned only to the relevant bus.

### `tests.test_bus_accounts_page`

- File: `tests/test_bus_accounts_page.py`
- Purpose: Use Streamlit AppTest to exercise the Bus Accounts page with mocked performance data.
- Important validation:
  - Bus Accounts loads comparison metrics.
  - shared costs and recorded contribution are visible.
  - individual bus detail and recent bus-related transactions render.

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
| `sf_assert_collection(p_id integer)` | Validates remittance collection totals, explicit unallocated differences and linked inbound ledger entry | `remittance_collections`, `remittances`, `financial_transactions` |
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
