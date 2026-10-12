# SmartFleet feature status

Last updated: 2026-10-12

Status legend:

- Implemented: code exists for the feature.
- Tested: safe checks were executed and passed.
- Planned: intended but not built.
- Blocked: cannot be completed without a dependency, schema decision or business-rule decision.

| Feature | Locations | State | Tests | Dependencies and blockers |
| --- | --- | --- | --- | --- |
| PostgreSQL schema | `migrations/001` through `migrations/024`, live `smartfleet` DB | Implemented | Temporary migration recreation passed through `024` | No migration tracking table exists |
| Database technical reference | `docs/SmartFleet_Database_Schema_V1_Technical_Reference.docx`, `.pdf` | Implemented | Source document inspected | Must not be overwritten casually |
| Database connection | `database/connection.py` | Implemented | `python -m tests.test_connection` passed | Uses `.env`; no app-level secrets strategy yet |
| Route listing | `services/route_service.py`, `app_pages/buses.py` | Implemented foundation | AppTest passed | Needs proper pytest test database |
| Route creation | `services/route_service.py` | Implemented | Existing app form works through Buses > Routes | Needs isolated write tests before routine baseline use |
| Bus listing | `services/bus_service.py`, `app_pages/buses.py` | Implemented foundation | `python -m tests.test_bus_service` and AppTest passed | Includes current assignment, model, seating and next document expiry context when records exist |
| Add bus | `services/bus_service.py`, `app_pages/add_bus.py`, `migrations/023_add_bus_details_and_documents.sql` | Implemented foundation | AppTest passed | File uploads are not implemented; expiry metadata is stored |
| Edit bus | none | Planned | none | Must preserve history and route relationships |
| Activate/deactivate bus | none | Planned | none | Use `ACTIVE`/`INACTIVE`; deactivation date/reason not currently stored |
| In Garage filter | none | Blocked | none | Requires approved definition, likely from maintenance/downtime rather than bus status |
| Routes page | `app_pages/buses.py`, `services/route_service.py` | Implemented foundation | AppTest passed | Edit/deactivate route still planned |
| Drivers page | `app_pages/buses.py`, `services/driver_service.py` | Implemented foundation | AppTest passed | Driver editing still planned |
| Driver registration | `app_pages/buses.py`, `services/driver_service.py` | Implemented foundation | AppTest passed | Creates an initial active employment record |
| Driver assignment | `app_pages/add_bus.py`, `services/bus_service.py` | Implemented foundation | AppTest passed | Initial assignment is supported during Add Bus; reassignment management still planned |
| Record Cashing | `app_pages/record_cashing.py`, `services/cashing_service.py` | Implemented foundation | AppTest passed; disposable DB insert/backfill/edit/delete smoke tests passed | Supports today, single-day backfill, two-week grid backfill, edit and delete |
| Collections view | `app_pages/finance.py`, `services/finance_service.py` | Implemented read-only foundation | AppTest passed | Detailed entry drill-down still planned |
| Expense recording | `app_pages/record_expense.py`, `services/expense_service.py`, `migrations/024_add_expense_reference_fields.sql` | Implemented foundation | AppTest passed; disposable DB insert/edit/delete smoke tests passed | Supports business-account general expenses and bus expenses, paid-to, receipt/reference, edit and delete; owner-personal and multi-bus allocation still planned |
| Expense ledger | `app_pages/finance.py`, `services/finance_service.py` | Implemented read-only foundation | AppTest passed | Search/filter/details still planned |
| Finance general summaries | `app_pages/finance.py`, `services/dashboard_service.py` | Implemented foundation | AppTest passed | Definitions must be expanded as workflows are built |
| Balances page | `app_pages/finance.py`, `services/finance_service.py` | Implemented limited foundation | AppTest passed | Uses ledger balances only; reconciliation rules still planned |
| Home dashboard | `app_pages/home.py`, `services/dashboard_service.py` | Implemented foundation | AppTest passed | Empty until real operational records exist |
| Recent Activity | `services/dashboard_service.py` | Implemented limited foundation | AppTest passed | Derived only from real cashing, expense and maintenance records |
| Maintenance records | database only | Planned | none | Service and UI not built |
| Maintenance schedules | database only | Planned | none | Service and reminders not built |
| Reminders page | `app_pages/reminders.py`, `services/reminder_service.py` | Implemented read-only foundation | AppTest passed | Stored reminder completion/dismissal still planned |
| Document expiry | `bus_documents`, `services/reminder_service.py`, `app_pages/reminders.py` | Implemented foundation | AppTest passed | Derived expiry list exists; stored reminder generation and file uploads still planned |
| Payroll and advances | database only | Planned | none | Service/UI not built; integrity functions exist |
| Financial accounts | `app_pages/finance.py`, `app_pages/accounts.py`, `services/finance_service.py`, `services/account_service.py` | Implemented foundation | AppTest passed; disposable DB opening-balance update passed | Opening balance management exists; reconciliation rules still planned |
| In-app backups | `app_pages/backups.py`, `services/backup_service.py` | Implemented foundation | Backup service created and verified a custom-format dump | Restore flow is manual |
| Reports/export | `app_pages/reports.py`, `services/report_service.py` | Implemented foundation | AppTest passed | CSV exports for collections, expenses and balances |
| Data validation warnings | `app_pages/home.py`, `app_pages/more.py`, `services/validation_service.py` | Implemented foundation | AppTest passed | Initial setup and backup warnings only |
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
