# SmartFleet testing guide

Last updated: 2026-10-13

## Current testing state

The repository now has a reliable `unittest` baseline plus focused Streamlit AppTest coverage for the Record Cashing page and page-load sweeps for the main workflows.

Current blockers:

- Data-changing database tests still need an isolated test database.
- `pytest` is not installed in `.venv`; use `python -m unittest discover -v` for the current suite.
- Route creation and other write-heavy checks should remain out of the routine suite until test-database fixtures exist.

## Baseline commands executed during audit

| Command | Result |
| --- | --- |
| `.venv\Scripts\python.exe -m unittest discover -v` | Passed: 46 tests |
| `.venv\Scripts\python.exe -m pytest tests\test_connection.py tests\test_bus_service.py` | Historical failure: `No module named pytest` |
| `.venv\Scripts\python.exe tests\test_connection.py` | Failed: `ModuleNotFoundError: No module named 'database'` |
| `.venv\Scripts\python.exe tests\test_bus_service.py` | Failed: `ModuleNotFoundError: No module named 'services'` |
| `.venv\Scripts\python.exe -m tests.test_connection` | Passed. Core database tables exist |
| `.venv\Scripts\python.exe -m tests.test_bus_service` | Passed. Bus rows have expected shape |
| `.venv\Scripts\python.exe -m compileall app.py app_pages services components utils tests scripts` | Passed |
| Streamlit `AppTest` page sweep | Passed for Home, Buses, Finance, More, Record Cashing, Record Expense, Accounts, Business Presets, Backups, Reports and Reminders |
| `.venv\Scripts\python.exe scripts\verify_migrations.py` | Passed. Applied migrations `001` through `028` to a disposable database and dropped it |
| `.venv\Scripts\python.exe scripts\smoke_smart_cashing.py` | Passed. Temporary database migrated through `028`, one test bus was created, smart cashing was recorded and one matching ledger receipt was verified |
| Disposable cashing smoke test | Passed. Temporary database migrated through `023`, one test bus was created, K1,800 cashing was recorded and verified, then the database was dropped |
| Direct and smart cashing unit/AppTest coverage | Passed. One-bus, multi-bus, missing-value, form-clear, smart summary and open-obligation page-state cases are covered |
| Disposable expense smoke test | Passed. Temporary database migrated through `023`, one general expense and one bus expense were recorded and verified against matching outbound ledger rows, then the database was dropped |
| Disposable edit/delete smoke test | Passed. Temporary database migrated through `024`, opening balance update, expense edit/delete and cashing edit/delete were verified, then the database was dropped |
| Backup service check | Passed. Created `smartfleet_20261012_235450.dump` before migrations `026`/`027` and `smartfleet_20261012_235728.dump` before migration `028`; both verified with PostgreSQL restore-list output |

The AppTest command printed a Windows temporary-folder cleanup warning after all page checks passed. Treat this as a test-harness cleanup limitation unless it reappears as an app exception.

## Migration recreation check

A temporary database with a unique name was created. Migrations `001` through `028` were applied successfully with `scripts/verify_migrations.py`, then the temporary database was dropped.

Result: pass.

The SQL integrity test script was not run against the live database. It should run only in a disposable database or a transaction-controlled environment that always rolls back.

## Safe test database strategy

Use a dedicated database for tests, for example:

```text
smartfleet_test
```

Required properties:

- Recreated from numbered migrations.
- Seeded only with controlled test fixtures.
- Never points at operational data.
- Test transactions roll back after each test where practical.
- Destructive setup/teardown targets only the test database.

Recommended test flow:

```text
1. create/drop/recreate smartfleet_test
2. apply migrations 001 through latest
3. run SQL integrity tests
4. run `unittest` unit and integration tests
5. drop or preserve test database depending on developer workflow
```

## Test categories

### Unit tests

Use for:

- input validation.
- date handling.
- Kwacha formatting.
- status mapping.
- expected cashing calculations.
- expense allocation calculations.
- duplicate-submit guards where logic can be isolated.

Unit tests should not connect to PostgreSQL.

### Database integration tests

Use for:

- route CRUD.
- bus CRUD.
- driver, employment and assignment rules.
- financial transaction relationships.
- cashing and collection reconciliation.
- expenses and allocations.
- maintenance schedules.
- reminders.
- payroll and advance recovery.
- loan repayments.
- transfer fee calculations.
- constraint and trigger failures.

These tests must run against a test database.

### Workflow tests

Required workflows:

- Create a route, then add a bus.
- Register a driver and assign the driver to a bus.
- Record cashing and verify collection/remittance/ledger rows.
- Record an expense and verify scope, allocation and ledger rows.
- Schedule maintenance and verify reminders.
- Deactivate and reactivate a bus while preserving history.

### Streamlit UI tests

Use Streamlit's `st.testing.v1.AppTest` for behavior tests:

- page loads without exceptions.
- form validation messages appear.
- filter widgets update lists.
- wizard state persists across steps.
- success messages appear only after service success.

Use browser automation only for:

- actual fixed bottom navigation behavior.
- CSS/layout checks.
- mobile viewport screenshots.
- custom components, if any are introduced.

## Tests not currently safe to run routinely

| File | Reason |
| --- | --- |
| `migrations/smartfleet_integrity_tests_corrected.sql` | Intended for disposable database/rollback validation, not live-data execution |

## Required fixes before reliable database integration testing

1. Decide whether to keep `unittest`, add `pytest`, or support both.
2. Decide whether `requirements.txt` should include dev dependencies or whether a separate requirements file is needed.
3. Add test fixtures for database settings.
4. Add a test database creation/apply-migrations helper.
5. Rewrite data-changing tests to use isolated fixtures.
6. Ensure imports work consistently from the chosen test runner.
7. Separate read-only smoke tests from write/integration tests.

## Manual mobile verification checklist

When the UI exists, check these widths:

- 320px
- 375px
- 390px
- 430px
- 768px
- desktop width

Verify:

- no horizontal overflow.
- bottom navigation does not cover submit buttons.
- card text wraps cleanly.
- forms work with mobile keyboards.
- search and filters remain usable.
- charts remain readable.
- selected states are clear.
- errors and success messages are visible.

## Phase test reporting format

For each phase, record:

- date tested.
- branch/commit tested.
- database tested.
- commands executed.
- tests passed.
- tests failed.
- tests skipped and why.
- defects fixed.
- unresolved limitations.
