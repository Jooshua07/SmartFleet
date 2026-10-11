# Adding new features to SmartFleet

Last updated: 2026-10-11

Use this guide when adding or changing SmartFleet behavior. The goal is to extend the system without breaking financial integrity or rewriting the project.

## 1. Identify the requirement

Write down:

- The business event the feature represents.
- Who uses it.
- Which records it creates or reads.
- Which existing business rules apply.
- Whether historical records must be preserved.
- Whether money, balances, assignments or dates are affected.

Do not start in the UI. Start with the business rule.

## 2. Check the existing schema

Inspect:

- Existing tables and columns.
- Foreign keys.
- Check constraints.
- Deferred triggers.
- Existing seed data.
- Existing documentation.

If the schema already represents the requirement, use it. Do not add duplicate columns or parallel tables.

## 3. Decide whether a migration is needed

A migration is needed when the feature must persist data that the schema cannot currently store.

Examples:

- Bus model and seating capacity require new schema support.
- Uploaded document metadata requires a new table or approved storage design.
- A new reminder type may need an updated check constraint.

Schema changes must be additive unless a destructive change is explicitly approved.

## 4. Write an additive SQL migration

Migration rules:

- Create the next numbered migration.
- Do not edit already-applied migrations casually.
- Use explicit constraints for required business rules.
- Add indexes only for real lookup/reporting needs.
- Seed only configuration data, not fake operations.
- Include rollback notes in comments when useful, but do not rely on destructive rollback in production.

After writing the migration:

1. Apply all migrations to a temporary database.
2. Apply the new migration to the development database only when approved and safe.
3. Update the database reference documents.

## 5. Add database and service functions

Keep persistence and business logic outside Streamlit page files.

Recommended pattern:

```text
database/connection.py       connection factory
database/transactions.py     transaction context helper
services/example_service.py  business operation
tests/                       unit and integration tests
```

Service functions should:

- Accept plain Python values.
- Validate required fields.
- Use parameterized SQL.
- Run multi-table writes in one transaction.
- Let PostgreSQL constraints enforce final integrity.
- Return plain dictionaries or dataclasses.
- Raise clear domain errors for invalid user input.

## 6. Add the Streamlit page or component

UI rules:

- Use native Streamlit widgets first.
- Use `st.form` for write operations.
- Use stable widget keys.
- Use `st.skeleton` for slow-loading sections.
- Use `st.segmented_control` or `st.pills` for small visible option sets.
- Use `st.selectbox` for longer options.
- Do not place business logic only in UI handlers.
- Do not display hardcoded sample values as real data.

## 7. Connect navigation

Add the page to the approved navigation structure:

- Primary: Home, Buses, Finance, More.
- Quick actions: Record Cashing, Record Expense, Add Bus, Drivers, Reminders.
- Internal tabs only where the screen has peer views.

Avoid duplicate navigation systems.

## 8. Add tests

Add the smallest useful coverage first:

- Unit tests for validation, formatting and calculations.
- Database integration tests for persistence and constraints.
- Workflow tests for important user journeys.
- Streamlit `AppTest` tests for UI behavior where practical.

Use an isolated test database or transaction fixtures. Never run write tests against the shared development database.

## 9. Run regression checks

At minimum:

```powershell
.venv\Scripts\python.exe -m pytest
```

Current baseline note: pytest is not installed yet. Add it to development requirements before relying on this command.

For schema work:

```text
create temporary database
apply migrations 001 through latest
run SQL integrity tests in the temporary database
drop temporary database
```

For UI work:

- Run Streamlit locally.
- Check desktop and mobile widths.
- Verify that forms do not get covered by bottom navigation.
- Verify no horizontal overflow at 320px width.

## 10. Update documentation

Update all affected docs:

- `docs/PROJECT_STATE.md`
- `docs/ARCHITECTURE.md`
- `docs/MODULE_REFERENCE.md`
- `docs/UI_UX_SPECIFICATION.md`
- `docs/TESTING.md`
- `docs/FEATURE_STATUS.md`
- Any future deployment or changelog documents.

## Concrete example: adding a new reminder type

Requirement: Add a reminder for an operating permit renewal.

### Step A - Check existing support

The `reminders` table already supports:

- `reminder_type`
- `title`
- `description`
- `due_date`
- `status`
- optional `bus_id`
- optional `maintenance_schedule_id`
- optional `business_loan_id`
- notes and completion fields

Allowed reminder types currently include:

- `MAINTENANCE`
- `LOAN_REPAYMENT`
- `DOCUMENT_EXPIRY`
- `REGULATORY`
- `OTHER`

An operating permit renewal can likely use `REGULATORY` or `DOCUMENT_EXPIRY` without a migration if the required data is only a due date and reminder text.

### Step B - Add service functions

Create or extend `services/reminder_service.py`:

- `create_reminder(...)`
- `get_due_reminders(start_date, end_date)`
- `complete_reminder(reminder_id, completed_date)`
- `dismiss_reminder(reminder_id)`

Validate:

- due date is present.
- title is not empty.
- type is one of the allowed values.
- bus id exists when supplied.
- completed reminders include a completed date.

### Step C - Add UI

On the Reminders page:

- Show regulatory reminders in the Other documented reminders section.
- Sort overdue first, then due soon.
- Use amber for due soon and red for overdue.
- Link to the bus if `bus_id` is present.

### Step D - Add tests

Add tests that:

- Create a reminder in the test database.
- Reject invalid reminder types.
- Complete a reminder with a completion date.
- Reject a completed reminder without a completion date.
- Confirm Reminders page renders the new item.

### Step E - Update docs

Update `MODULE_REFERENCE.md`, `FEATURE_STATUS.md`, `TESTING.md` and this guide if the feature changes the extension pattern.

