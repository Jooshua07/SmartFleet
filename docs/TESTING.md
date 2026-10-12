# SmartFleet testing guide

Last updated: 2026-10-12

## Current testing state

The repository has pytest-style files and ad hoc scripts, but it does not yet have a reliable automated test suite.

Current blockers:

- `pytest` is not installed in `.venv`.
- `pytest` is not listed in `requirements.txt`.
- Running test files by path fails because project modules are not importable from the `tests/` directory.
- `tests/test_route_service.py` is read-only after cleanup, but route creation still needs an isolated write test.

## Baseline commands executed during audit

| Command | Result |
| --- | --- |
| `.venv\Scripts\python.exe -m pytest tests\test_connection.py tests\test_bus_service.py` | Failed: `No module named pytest` |
| `.venv\Scripts\python.exe tests\test_connection.py` | Failed: `ModuleNotFoundError: No module named 'database'` |
| `.venv\Scripts\python.exe tests\test_bus_service.py` | Failed: `ModuleNotFoundError: No module named 'services'` |
| `.venv\Scripts\python.exe -m tests.test_connection` | Passed after migration `023`. Connected and printed 29 tables |
| `.venv\Scripts\python.exe -m tests.test_bus_service` | Passed after migration `023`. Returned 0 buses |
| `.venv\Scripts\python.exe -m compileall app.py app_pages components services utils database` | Passed |
| Streamlit `AppTest` page sweep | Passed for Home, Buses, Finance, More, Add Bus, Record Cashing, Record Expense, Reminders, Backups, Accounts and Reports |
| Disposable cashing smoke test | Passed. Temporary database migrated through `023`, one test bus was created, K1,800 cashing was recorded and verified, then the database was dropped |
| Disposable cashing backfill smoke test | Passed. Temporary database migrated through `023`, two test buses were created, two collection dates were recorded from backfill rows, totals and duplicate blocking were verified, then the database was dropped |
| Temporary backfill UI `AppTest` | Passed no-crash check for Record Cashing two-week mode with a temporary route and bus |
| Disposable expense smoke test | Passed. Temporary database migrated through `023`, one general expense and one bus expense were recorded and verified against matching outbound ledger rows, then the database was dropped |
| Disposable edit/delete smoke test | Passed. Temporary database migrated through `024`, opening balance update, expense edit/delete and cashing edit/delete were verified, then the database was dropped |
| Backup service check | Passed. Created `smartfleet_20261012_001847.dump` and verified it with PostgreSQL restore-list output |

The AppTest command printed a Windows temporary-folder cleanup warning after all page checks passed. Treat this as a test-harness cleanup limitation unless it reappears as an app exception.

## Migration recreation check

A temporary database with a unique name was created. Migrations `001` through `024` were applied successfully, then the temporary database was dropped.

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
4. run pytest unit and integration tests
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

## Required fixes before reliable pytest use

1. Add `pytest` to development dependencies.
2. Decide whether `requirements.txt` should include dev dependencies or whether a separate requirements file is needed.
3. Add pytest fixtures for database settings.
4. Add a test database creation/apply-migrations helper.
5. Rewrite data-changing tests to use isolated fixtures.
6. Ensure imports work consistently when running `python -m pytest`.
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
