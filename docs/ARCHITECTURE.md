# SmartFleet architecture

Last updated: 2026-10-12

## Current architecture

SmartFleet currently has a strong PostgreSQL schema and a Streamlit shell. The shell provides native page routing, shared UI helpers, real-data empty states, fleet setup writes, a clean direct cashing form, expense entry/edit/delete, account management, backups, exports, Business Presets and a consolidated Business Balance view. Several advanced business write workflows remain planned.

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
services/preset_service.py      business settings, rates, salary and reminder presets
services/loan_service.py        loan repayment classification helpers
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
| `services/bus_service.py` | Initial bus create/list helpers and bus document metadata; edit/activate/deactivate still planned |
| `services/route_service.py` | Initial route create/list helpers; edit/activate/deactivate still planned |
| `services/driver_service.py` | Initial driver create/overview helpers and available employment lookup |
| `services/assignment_service.py` | Bus-driver assignment history and conflict checks |
| `services/cashing_service.py` | Direct cashing, Airtel Money collection destination, collections, remittances and ledger links |
| `services/expense_service.py` | Expense entry, allocation and ledger links |
| `services/dashboard_service.py` | Dashboard summaries, status counts, performance and activity |
| `services/finance_service.py` | Collection, expense, consolidated Business Balance, business ledger and calculated account balance reads |
| `services/reminder_service.py` | Due maintenance, document expiries, deactivated buses and stored reminders |
| `services/preset_service.py` | Reporting baseline, cashing-rate history, cashing schedule, salary and reminder presets |
| `services/loan_service.py` | Business loan repayment classification helpers |

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
2. UI lets the user enter one common amount for multiple buses or separate amounts per bus.
3. Service validates:
   - at least one bus entry is included
   - every selected bus has a positive amount
   - amounts are not negative
   - date is valid
   - the Airtel Money collection account is active
   - duplicate bus/date cashing entries do not already exist
4. Service starts one transaction.
5. Service inserts an inbound `financial_transactions` row of type CASHING.
6. Service inserts `remittance_collections` for the collection occasion.
7. Service inserts one or more `remittances` rows linked to the bus and collection.
8. PostgreSQL checks collection total and ledger integrity.
9. Transaction commits.
10. UI shows a success message and the recent cashing list reflects the new collection.
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
1. User selects expense date, category, payment account, scope, amount and description.
2. UI asks the service for active categories, active payment accounts and active buses.
3. Service validates:
   - amount is greater than zero
   - description is present
   - category and payment account are active
   - bus scope has a valid bus
4. Service starts one transaction.
5. Service inserts an outbound `financial_transactions` row of type EXPENSE.
6. Service inserts the linked `expenses` row.
7. PostgreSQL checks expense/ledger consistency.
8. Transaction commits.
9. UI shows a success message and recent expenses reflects the new record.
```

Owner-personal expenses and multi-bus allocation remain planned.

## Navigation and shared UI

Phone-first navigation target:

- Bottom navigation: Home, Buses, Finance, More.
- More quick actions: Record Cashing, Record Expense, Add Bus, Drivers, Reminders.
- Buses page internal tabs: Buses, Routes, Drivers.
- Finance page internal tabs: General, Collections, Expenses, Balances.

The current app uses hidden `st.navigation` plus a bottom action row rendered with `st.bottom`. This avoids legacy `pages/` auto-discovery and avoids fragile CSS selectors tied to Streamlit internals. Browser/mobile verification is still required before this is considered final.

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
