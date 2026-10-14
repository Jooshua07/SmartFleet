# SmartFleet architecture

## Step 4 reporting and servicing

`utils/reporting_periods.py` owns calendar dates. `components/reporting_period.py` owns independent widget keys. Finance shares one period across tabs; Home chart and Reports use separate keys. `finance_service.get_period_balance` carries clean-slate baseline cash forward and excludes internal transfers. `performance_service.get_business_financial_timeline` maps real dated activity to Thursday/Sunday points, with a labelled trailing endpoint when required. Payroll cost is recognized at the first of the earned month; salary cash uses its payment date.

`maintenance_service.record_servicing` atomically saves completion, cost components, one linked bus expense and one ledger payment. Zero-cost work writes maintenance only. Corrections preserve audit snapshots and reuse existing payments. The latest valid completion drives the due date; manual scheduling is audited separately. Migration 031 extends existing tables, without inventory.

`business_report_service` is read-only and reuses operating, cash and Bus Accounts source calculations. Exports use the report snapshot, including collection headers for unresolved allocations. `report_export_service` emits CSV and openpyxl workbooks. General costs remain unassigned. Read-only quality checks never create adjustments.

Last updated: 2026-10-13

## Current architecture

SmartFleet currently has a strong PostgreSQL schema and a Streamlit shell. The shell provides native page routing, shared UI helpers, real-data empty states, fleet setup writes, fleet edit/deactivation/reactivation, smart cashing, expense entry/edit/delete, Driver Money, Loans, Owner Money, Bus Accounts, backups, exports, Business Presets, a consolidated Business Balance view and a Home operating-performance chart.

```text
User browser
  -> Streamlit app (`app.py`)
  -> Page scripts and reusable UI components
  -> Services with business operations
  -> Database connection and transaction helpers
  -> PostgreSQL smartfleet database
```

Current implemented modules:

```text
app.py                         Streamlit entrypoint and router
app_pages/                     Initial page scripts
components/                    Shared UI helpers
utils/                         Date, formatting and validation helpers
database/connection.py          psycopg connection factory
services/route_service.py       route list and create helpers
services/bus_service.py         bus list/create helpers plus document metadata
services/driver_service.py      driver list/create helpers and employment lookup
services/cashing_service.py     direct cashing collection summaries and writes
services/smart_cashing_service.py expected cashing, allocations and obligations
services/bus_account_service.py recorded bus contribution and shared-cost reporting
services/preset_service.py      business settings, rates, salary and reminder presets
services/driver_money_service.py payroll, advances and recovery allocation
services/loan_service.py        business loans, repayments and owner-money helpers
services/performance_service.py operating-performance reporting definitions
tests/                          unittest and Streamlit AppTest coverage
migrations/                     canonical SQL schema history
docs/                           database reference, UI references and project docs
```

## Target architecture

The application should be built in layers:

```text
Streamlit pages
  -> call services
Services
  -> validate user intent and coordinate business transactions
Database helpers/repositories
  -> execute parameterized SQL and transaction boundaries
PostgreSQL
  -> enforce relational, financial and historical rules
```

Streamlit pages should not own financial business rules. They should collect input, show feedback and call service functions. Service functions should own workflows such as adding a bus, assigning a driver, recording cashing or recording an expense.

## Streamlit user interface

The app should use Streamlit 1.65 APIs that are present in the local environment:

- `st.navigation` and `st.Page`
- `st.container`
- `st.metric`
- `st.skeleton`
- `st.segmented_control`
- `st.pills`
- `st.bottom`
- `st.form`

Implemented page organization:

```text
app.py                         Main entrypoint and navigation
app_pages/
  home.py
  buses.py
  finance.py
  record_cashing.py
  record_expense.py
  reminders.py
  add_bus.py
components/
  layout.py
  cards.py
  forms.py
utils/
  dates.py
  formatting.py
  validation.py
```

The existing `pages/` directory is empty. Because `app.py` calls `st.navigation`, Streamlit ignores the legacy `pages/` directory.

## Service and business-logic layer

Services should:

- Validate inputs before database writes.
- Normalize business terminology for UI and database use.
- Open one database transaction per business operation.
- Use parameterized SQL only.
- Return plain Python data structures suitable for UI rendering and tests.
- Avoid direct Streamlit imports.
- Treat PostgreSQL constraints and triggers as authoritative for final integrity.

Current and planned service modules:

| Module | Responsibility |
| --- | --- |
| `services/bus_service.py` | Bus create/list/edit helpers, bus document metadata, route history and effective-dated status history |
| `services/route_service.py` | Initial route create/list helpers; edit/activate/deactivate still planned |
| `services/driver_service.py` | Driver create/edit/overview helpers and available employment lookup |
| `services/assignment_service.py` | Bus-driver assignment history and conflict checks |
| `services/cashing_service.py` | Direct cashing, Airtel Money collection destination, collections, remittances and ledger links |
| `services/smart_cashing_service.py` | Sunday/Thursday cashing coverage, expected cashing, standard/manual allocations, obligations and obligation repayments |
| `services/expense_service.py` | Expense entry, allocation and ledger links |
| `services/bus_account_service.py` | Recorded revenue, attributed bus costs, salary attribution, shared general costs and Bus Accounts drill-downs |
| `services/dashboard_service.py` | Dashboard summaries, status counts, performance and activity |
| `services/finance_service.py` | Collection, expense, consolidated Business Balance and business ledger reads |
| `services/reminder_service.py` | Due maintenance, document expiries, deactivated buses and stored reminders |
| `services/preset_service.py` | Reporting baseline, cashing-rate history, cashing schedule, salary presets, driver advance limit and reminder presets |
| `services/driver_money_service.py` | Driver salary previews, advance cap enforcement, salary recording/cancellation and recovery allocation |
| `services/loan_service.py` | Business loan registration, repayments, owner drawings, owner loans and owner-paid lender settlement |
| `services/performance_service.py` | Central operating revenue, expense and profit/loss definitions for Home and summaries |

## PostgreSQL data-access layer

`database/connection.py` currently exposes `get_connection()`. This should remain small, but future work should add transaction helpers so multi-table financial writes are consistent.

Expected helper pattern:

```text
with transaction() as conn:
    insert financial transaction
    insert domain record
    insert allocation/detail records
    commit only after all deferred constraints pass
```

Do not hide database errors that indicate broken financial rules. Services should catch them, roll back and return a safe user-facing message while preserving the technical detail for logs.

## Database integrity and transactions

PostgreSQL is the authoritative integrity layer. The current schema enforces:

- Required relationships between buses, routes, drivers and assignments.
- Controlled status/type values.
- Positive monetary amounts.
- Valid date ranges.
- Unique active employment and permanent assignment constraints.
- Matching ledger rules for cashing, expenses, advances, payroll, loans and transfers.
- Owner-funded expenses as owner loan obligations rather than business cash movements.
- Non-overlapping active transfer-fee rules and cashing rates.
- Maintenance events linked only to matching-bus expenses.
- Automatic `updated_at` updates on supported tables.

Financial workflows must be written as atomic transactions because deferred triggers validate the final combined state at commit time.

## Typical data flow: recording cashing

The UI title must be `Record Cashing`. Internally, the flow should respect the existing remittance and collection model.

```text
1. User selects a collection date and one or more buses. The receiving account is the active Airtel Money account from Business Presets.
2. UI calculates the Sunday/Thursday coverage period and expected amount from effective-dated rates and bus status history.
3. In Standard mode, the owner enters the actual received amount once and confirms the calculated allocation.
4. In Adjust Buses mode, the owner can adjust days worked, Sunday work, per-bus allocation and difference classification.
5. Service validates:
   - at least one bus entry is included
   - amounts are not negative
   - bus allocations plus explicit unallocated amount equal the actual receipt
   - the Airtel Money collection account is active
   - duplicate bus/date cashing entries do not already exist
6. Service starts one transaction.
7. Service inserts one inbound `financial_transactions` row of type CASHING for the actual receipt.
8. Service inserts `remittance_collections` with coverage, expected total, unallocated amount and classification.
9. Service inserts one or more `remittances` rows with allocation provenance and per-bus classification.
10. Confirmed unpaid obligations are stored only when a responsible party is explicitly supplied.
11. PostgreSQL checks collection total and ledger integrity.
12. Transaction commits.
13. UI shows a success message and the recent cashing list reflects the new collection.
```

Legacy direct cashing helpers still exist for edit compatibility, but new cashing entries use the smart flow.

## Typical data flow: bus status changes

```text
1. User chooses Deactivate or Reactivate from the Buses page.
2. User supplies an effective date and optional reason.
3. Service closes the previous open `bus_status_history` row.
4. Service inserts the new effective-dated status row.
5. Service updates `buses.status` as the quick current status.
6. Historical cashing eligibility counts active days from the history table, not only the current status.
```

Open decision: import from historical spreadsheet-style notes is not implemented yet.

## Typical data flow: Business Balance

The Finance > Balances page intentionally separates consolidated business position from individual account balances.

```text
1. Business Presets stores a reporting baseline date.
2. Finance service reads all ledger rows on or after that date.
3. Inbound ledger rows increase Business Balance.
4. Outbound ledger rows reduce Business Balance.
5. Loan repayments, owner loan repayments and owner drawings are classified as financing payments, not operating expenses.
6. The resulting balance can be negative when recorded payouts exceed recorded inflows.
```

Account balances remain account-specific and still include each account opening balance plus ledger movement.

## Typical data flow: recording expenses

The UI title must be `Record Expense`. The first implemented flow supports business-account expenses.

```text
1. User selects expense date, operating category, scope, amount and expense title.
2. UI asks the service for active operating categories and all registered buses, including deactivated buses for historical edits.
3. Service validates:
   - amount is greater than zero
   - expense title is present, at most five words and at most 35 characters
   - category is active and is not a restricted financial category
   - bus scope has a valid bus
   - general scope is not linked to one bus
4. Service starts one transaction.
5. Service resolves the configured default business payment account, currently the active Airtel Money account from Business Presets.
6. Service inserts an outbound `financial_transactions` row of type EXPENSE.
7. Service inserts the linked `expenses` row.
8. PostgreSQL checks expense/ledger consistency.
9. Transaction commits.
10. UI shows a success message and recent expenses reflects the new record.
```

Ordinary expense recording blocks loan repayments, recoverable driver advances, driver salaries and owner drawings so they cannot be silently saved as generic operating expenses. The Record Expense page links users to the dedicated loan, driver-money and owner-money workflows instead of creating a second payment system.

## Typical data flow: driver salary and advances

```text
1. User opens More > Management > Driver Money and chooses an existing driver employment.
2. For advances, the service checks active employment dates and the configured cumulative outstanding advance limit, currently defaulting to K1,000.
3. An advance creates one `DRIVER_ADVANCE` outbound ledger movement and one `driver_advances` row. It reduces Business Balance but is not counted as operating expense.
4. For salary, the service calculates the monthly salary from driver-specific/default presets, employment dates and proration rules.
5. Outstanding advances are suggested for recovery oldest-first, limited by earned salary so net salary cannot become negative.
6. A salary creates one `driver_salaries` row. Only the remaining net salary creates a `DRIVER_SALARY` cash movement.
7. Operating payroll cost is recognized from the salary record once, using the payroll period rather than the advance payment date.
8. Bus attribution uses historical permanent assignments only when one reliable bus is known for the salary period; otherwise the cost remains shared.
```

## Typical data flow: business loans and owner money

```text
1. User opens More > Management > Loans to add known business loans or record repayments.
2. Business-funded principal repayments create a `LOAN_REPAYMENT` outbound ledger movement and reduce loan principal; principal is not an operating expense.
3. Interest/fees, when recorded separately, are treated as financing costs rather than loan principal.
4. User opens More > Management > Owner Money for owner drawings, owner loans to the business, owner-paid lender payments and business repayments to the owner.
5. Owner drawings reduce Business Balance but are not operating expenses and are not bus costs.
6. Owner loans to the business increase Business Balance and increase the amount owed to the owner, without counting as operating revenue.
7. Owner-paid external loan repayments reduce the external loan and increase the amount owed to the owner without inventing any business cash inflow or outflow.
8. Business repayments to the owner reduce Business Balance and owner-loan balance without creating another lender payment.
```

## Typical data flow: Bus Accounts

Bus Accounts is not a Cash/Airtel/Bank account manager. It is a recorded bus-performance view.

```text
1. User chooses 1 Month, 3 Months or a custom date range.
2. `services.bus_account_service.get_bus_contribution_summary` reads registered buses, per-bus remittances, direct bus expenses and supported expense allocations.
3. Shared/general business expenses are summed separately and are not divided across buses.
4. Recorded Bus Contribution is calculated as:
   bus-attributed recorded cashing
   minus direct bus-specific operating costs
   minus verified bus-allocated operating costs.
5. Finance/owner drawings/loan principal and recoverable advances are excluded from bus contribution.
6. Driver salary cost is attributed to a bus only when historical assignment data supports it; otherwise it is shown as shared cost.
7. Individual bus detail uses `get_bus_account_detail` for trend, category and recent bus-related transactions.
```

If a cashing amount is estimated or manually adjusted rather than confirmed actual, Bus Accounts keeps it visible as recorded revenue but labels the page with the appropriate caveat. Unallocated collection differences are not invented as bus revenue.

## Navigation and shared UI

Phone-first navigation target:

- Bottom navigation: Home, Buses, Finance, More.
- More quick actions: Record Cashing, Record Expense, Add Bus, Drivers, Reminders.
- Buses page internal tabs: Buses, Routes, Drivers.
- Finance page internal tabs: General, Collections, Expenses, Balances.
- More > Management links to Bus Accounts, Driver Money, Loans and Owner Money.

## Typical data flow: Home business performance

```text
1. Home reads the reporting baseline date, currently 1 October 2026.
2. `services.performance_service` sums gross operating receipts from cashing collections without double-counting remittance rows.
3. Operating expenses include ordinary operating expenses, bus-specific expenses, salary expense recognized through payroll and eligible financing costs.
4. Loan principal, owner drawings, owner loans, owner repayments and driver-advance disbursements are excluded from operating expenses.
5. The chart accumulates recorded revenue and operating costs and shows actual consolidated Business Balance, including financing cash movements.
6. Month, 3 Months and 6 Months controls use independent keys and calendar periods. A measured-width chart region scrolls horizontally on phones.
```

The current app uses hidden `st.navigation` plus a bottom action row rendered with `st.bottom`. Step 4 verified the changed screens at mobile and desktop sizes. The chart scroll region uses scoped CSS and requires browser regression checks when Streamlit is upgraded.

## Configuration and environment

Current configuration uses `.env` and `python-dotenv`. This is acceptable for local development.

Deployment should move toward:

- Environment variables supplied by the host.
- `st.secrets` only where suitable for Streamlit-hosted settings.
- No committed credentials.
- Least-privilege database credentials.
- `.streamlit/secrets.toml` ignored if introduced.

## Application state

Use `st.session_state` only for user-specific UI state:

- Selected navigation item.
- Wizard step and draft Add Bus data.
- Form submission lock tokens.
- Active filters.
- Date range selectors.

Do not store shared database connections, global mutable caches or cross-user business state in `st.session_state`.

Use `st.cache_data` for read-only query results that can tolerate a short time-to-live, and clear or bypass caches after writes that affect the same view.

## Authentication and authorization

No authentication or authorization exists today. The system is not ready for public use.

Before deployment, define:

- Who can view finances.
- Who can add or deactivate buses.
- Who can record cashing and expenses.
- Who can edit historical records.
- Who can manage schema-level settings such as cashing rates and fee rules.

Authorization must be enforced server-side in services or database roles, not only by hiding UI controls.

## Error handling

Planned behavior:

- Validation errors should be shown next to the relevant form fields.
- Database integrity failures should show safe business-language messages.
- Technical details should not be displayed to end users in production.
- Failed financial submissions must roll back fully.
- Duplicate submits should be prevented with forms, disabled buttons while running, and idempotency checks where appropriate.

## Future deployment architecture

Minimum deployment shape:

```text
Hosted Streamlit app
  -> managed PostgreSQL
  -> environment-provided secrets
  -> migration command/process
  -> backups and restore testing
  -> logs and basic monitoring
```

The database reference notes that the schema is usable if a future API and frontend replace Streamlit. That is a future architecture option, not the current implementation.
