# SmartFleet architecture

Last updated: 2026-10-11

## Current architecture

SmartFleet currently has a strong PostgreSQL schema and a minimal Python layer. The Streamlit interface has not been built yet.

```text
User browser
  -> Streamlit app (planned; app.py is currently empty)
  -> Page scripts and reusable UI components (planned)
  -> Services with business operations
  -> Database connection and transaction helpers
  -> PostgreSQL smartfleet database
```

Current implemented modules:

```text
app.py                         Empty Streamlit entrypoint
database/connection.py          psycopg connection factory
services/route_service.py       route list and create helpers
services/bus_service.py         bus list helper
tests/                          ad hoc checks and pytest-style scripts
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

Recommended page organization:

```text
app.py or streamlit_app.py      Main entrypoint and navigation
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
  navigation.py
  forms.py
  feedback.py
utils/
  dates.py
  formatting.py
  validation.py
```

The existing `pages/` directory is empty. Streamlit's current guidance favors explicit `st.navigation` with a non-legacy page folder such as `app_pages/` to avoid accidental legacy page auto-discovery. If the existing `pages/` directory is kept, it should remain intentionally unused or be renamed in a planned cleanup.

## Service and business-logic layer

Services should:

- Validate inputs before database writes.
- Normalize business terminology for UI and database use.
- Open one database transaction per business operation.
- Use parameterized SQL only.
- Return plain Python data structures suitable for UI rendering and tests.
- Avoid direct Streamlit imports.
- Treat PostgreSQL constraints and triggers as authoritative for final integrity.

Examples of future service modules:

| Module | Responsibility |
| --- | --- |
| `services/bus_service.py` | Bus create/list/edit/activate/deactivate |
| `services/route_service.py` | Route create/list/edit/activate/deactivate |
| `services/driver_service.py` | Driver and employment records |
| `services/assignment_service.py` | Bus-driver assignment history and conflict checks |
| `services/cashing_service.py` | Cashing, collections, remittances and expected amounts |
| `services/expense_service.py` | Expense entry, allocation and ledger links |
| `services/finance_service.py` | Period summaries and account balances |
| `services/reminder_service.py` | Due maintenance, deactivated buses and stored reminders |

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
1. User selects bus, amount, date and optional notes.
2. UI asks the service for the driver assigned to that bus on the selected date.
3. Service validates:
   - bus exists
   - amount is not negative
   - date is valid
   - historical assignment lookup is date-aware
   - selected account and rate assumptions are defined by business rules
4. Service starts one transaction.
5. Service inserts an inbound `financial_transactions` row of type CASHING.
6. Service inserts `remittance_collections` for the collection occasion.
7. Service inserts one or more `remittances` rows linked to the bus and collection.
8. PostgreSQL checks collection total, actual amount and variance explanation rules.
9. Transaction commits.
10. UI shows a success message and disables duplicate submission for that completed attempt.
```

Open decision: the simplified UI captures only one amount. The service must decide whether that amount is a collection total, a bus-level remittance actual amount, or another documented business event. That decision must preserve the distinction between expected cashing and money actually received.

## Navigation and shared UI

Phone-first navigation target:

- Bottom navigation: Home, Buses, Finance, More.
- More quick actions: Record Cashing, Record Expense, Add Bus, Drivers, Reminders.
- Buses page internal tabs: Buses, Routes, Drivers.
- Finance page internal tabs: General, Collections, Expenses, Balances.

Streamlit supports top/sidebar navigation natively. `st.bottom` exists in Streamlit 1.65 and may support bottom actions, but a full fixed bottom navigation must be verified in the browser and documented before relying on it. Avoid fragile CSS selectors tied to Streamlit internals.

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

