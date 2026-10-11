# SmartFleet feature status

Last updated: 2026-10-11

Status legend:

- Implemented: code exists for the feature.
- Tested: safe checks were executed and passed.
- Planned: intended but not built.
- Blocked: cannot be completed without a dependency, schema decision or business-rule decision.

| Feature | Locations | State | Tests | Dependencies and blockers |
| --- | --- | --- | --- | --- |
| PostgreSQL schema | `migrations/001` through `migrations/022`, live `smartfleet` DB | Implemented | Temporary migration recreation passed | No migration tracking table exists |
| Database technical reference | `docs/SmartFleet_Database_Schema_V1_Technical_Reference.docx`, `.pdf` | Implemented | Source document inspected | Must not be overwritten casually |
| Database connection | `database/connection.py` | Implemented | `python -m tests.test_connection` passed | Uses `.env`; no app-level secrets strategy yet |
| Route listing | `services/route_service.py`, `app_pages/buses.py` | Implemented foundation | AppTest passed | Needs proper pytest test database |
| Route creation | `services/route_service.py` | Implemented | Existing script is unsafe for routine baseline | Current script writes to dev DB and may duplicate `Kitwe - Ndola` |
| Bus listing | `services/bus_service.py`, `app_pages/buses.py` | Implemented foundation | `python -m tests.test_bus_service` and AppTest passed | Includes current assignment context when records exist |
| Add bus | `services/bus_service.py`, `app_pages/add_bus.py` | Implemented foundation | AppTest passed | Schema-supported only; model, seating capacity and documents still need approval/migration |
| Edit bus | none | Planned | none | Must preserve history and route relationships |
| Activate/deactivate bus | none | Planned | none | Use `ACTIVE`/`INACTIVE`; deactivation date/reason not currently stored |
| In Garage filter | none | Blocked | none | Requires approved definition, likely from maintenance/downtime rather than bus status |
| Routes page | `app_pages/buses.py`, `services/route_service.py` | Implemented foundation | AppTest passed | Edit/deactivate route still planned |
| Drivers page | `app_pages/buses.py`, `services/driver_service.py` | Implemented read-only foundation | AppTest passed | Driver registration/editing still planned |
| Driver registration | none | Planned | none | Must respect employment history |
| Driver assignment | none | Planned | none | Unique active permanent assignment constraints already exist |
| Record Cashing | `app_pages/record_cashing.py` | UI placeholder | AppTest passed | Write workflow still planned; must map to remittance collections, remittances and ledger rules |
| Collections view | `app_pages/finance.py`, `services/finance_service.py` | Implemented read-only foundation | AppTest passed | Detailed entry drill-down still planned |
| Expense recording | `app_pages/record_expense.py` | Placeholder | AppTest passed | Write workflow still planned |
| Expense ledger | `app_pages/finance.py`, `services/finance_service.py` | Implemented read-only foundation | AppTest passed | Search/filter/details still planned |
| Finance general summaries | `app_pages/finance.py`, `services/dashboard_service.py` | Implemented foundation | AppTest passed | Definitions must be expanded as workflows are built |
| Balances page | `app_pages/finance.py`, `services/finance_service.py` | Implemented limited foundation | AppTest passed | Uses ledger balances only; reconciliation rules still planned |
| Home dashboard | `app_pages/home.py`, `services/dashboard_service.py` | Implemented foundation | AppTest passed | Empty until real operational records exist |
| Recent Activity | `services/dashboard_service.py` | Implemented limited foundation | AppTest passed | Derived only from real cashing, expense and maintenance records |
| Maintenance records | database only | Planned | none | Service and UI not built |
| Maintenance schedules | database only | Planned | none | Service and reminders not built |
| Reminders page | `app_pages/reminders.py`, `services/reminder_service.py` | Implemented read-only foundation | AppTest passed | Automatic document expiry lacks document storage |
| Document expiry | generic reminders only | Blocked/Planned | none | No document metadata table; manual reminder is possible |
| Payroll and advances | database only | Planned | none | Service/UI not built; integrity functions exist |
| Financial accounts | `app_pages/finance.py`, `services/finance_service.py` | Implemented limited foundation | AppTest passed | Account management UI not built |
| Transfers and fees | database only | Planned | none | Transfer fee rules seeded; service/UI not built |
| Owner loans | database seed only | Planned | none | Service/UI not built |
| Business loans | database only | Planned | none | Service/UI not built |
| Streamlit app shell | `app.py`, `app_pages/`, `components/` | Implemented foundation | AppTest passed | Browser/mobile verification pending |
| Bottom navigation | `components/layout.py` | Implemented foundation | AppTest passed | Need browser verification of `st.bottom` behavior |
| Shared UI components | `components/` | Implemented foundation | compileall passed | More components needed as workflows expand |
| Loading skeletons | `app_pages/home.py` | Implemented foundation | AppTest passed | Add skeletons to more data-heavy sections later |
| Automated pytest suite | `tests/` | Blocked | pytest command fails | `pytest` missing and data-changing tests need isolation |
| Streamlit UI tests | ad hoc AppTest command | Implemented foundation | AppTest passed | Needs committed pytest/AppTest suite |
| Authentication/authorization | none | Blocked/Planned | none | Business role decisions needed before public deployment |
| Deployment docs | none | Planned | none | Not ready until app and security decisions exist |
