# SmartFleet feature status

Last updated: 2026-10-14

Status legend:

- Implemented: code exists for the feature.
- Tested: safe checks were executed and passed.
- Planned: intended but not built.
- Blocked: cannot be completed without a dependency, schema decision or business-rule decision.

| Feature | Locations | State | Tests | Dependencies and blockers |
| --- | --- | --- | --- | --- |
| PostgreSQL schema | `migrations/001` through `migrations/031`, live `smartfleet` DB | Tested | Temporary migration recreation passed through `031` | No migration tracking table exists |
| Database technical reference | `docs/SmartFleet_Database_Schema_V1_Technical_Reference.docx`, `.pdf` | Implemented | Source document inspected | Must not be overwritten casually |
| Database connection | `database/connection.py` | Implemented | `python -m tests.test_connection` passed | Uses `.env`; no app-level secrets strategy yet |
| Route listing | `services/route_service.py`, `app_pages/buses.py` | Implemented foundation | AppTest passed | Needs proper pytest test database |
| Route creation | `services/route_service.py` | Implemented | Existing app form works through Buses > Routes | Needs isolated write tests before routine baseline use |
| Bus listing | `services/bus_service.py`, `app_pages/buses.py` | Implemented foundation | `python -m tests.test_bus_service` and AppTest passed | Includes current assignment, model, seating and next document expiry context when records exist |
| Add bus | `services/bus_service.py`, `app_pages/add_bus.py`, `migrations/023_add_bus_details_and_documents.sql` | Implemented foundation | AppTest passed | File uploads are not implemented; expiry metadata is stored |
| Edit bus | `app_pages/buses.py`, `services/bus_service.py`, `migrations/026_fleet_history_and_editing.sql` | Implemented foundation | Unit tests and AppTest passed | Document upload persistence is still planned |
| Activate/deactivate bus | `app_pages/buses.py`, `services/bus_service.py`, `migrations/026_fleet_history_and_editing.sql` | Implemented foundation | Unit tests cover mid-period deactivation and reactivation day counts | Uses `ACTIVE`/`INACTIVE` with effective-dated history |
| Fleet status filter | `app_pages/buses.py` | Tested | Browser checks | Active/Deactivated only; garage is an explanatory reason |
| Routes page | `app_pages/buses.py`, `services/route_service.py` | Implemented foundation | AppTest passed | Edit/deactivate route still planned |
| Drivers page | `app_pages/buses.py`, `services/driver_service.py` | Implemented foundation | AppTest passed | Driver editing exists; employment history management still planned |
| Driver registration | `app_pages/buses.py`, `services/driver_service.py` | Implemented foundation | AppTest passed | Creates an initial active employment record |
| Driver assignment | `app_pages/add_bus.py`, `services/bus_service.py` | Implemented foundation | AppTest passed | Initial assignment is supported during Add Bus; reassignment management still planned |
| Record Cashing | `app_pages/record_cashing.py`, `services/smart_cashing_service.py`, `services/cashing_service.py`, `services/preset_service.py` | Implemented smart foundation | AppTest passed; unit tests cover Sunday/Thursday coverage, K600/K300 calculations, unallocated shortages, surplus, adjust mode, smart correction paths, locked corrections, payment history and obligation-payment validation; disposable smart-cashing smoke passed | Supports expected cashing, standard allocations, Adjust Buses, Sunday toggles, unallocated differences, confirmed obligations, recent smart-cashing details, smart correction while unlocked, locked delete/correction when obligations exist, payment history and obligation payment recording |
| Collections view | `app_pages/finance.py`, `services/finance_service.py` | Implemented read-only foundation | AppTest passed | Detailed entry drill-down still planned |
| Expense recording | `app_pages/record_expense.py`, `services/expense_service.py`, `migrations/024_add_expense_reference_fields.sql` | Implemented refined foundation | AppTest passed; unit tests cover title limits, default payment account, restricted financial categories, bus/general scope changes and historical bus selection; disposable DB insert/edit/delete smoke tests passed | Supports General Business and Specific Bus expenses, expense title, paid-to, receipt/reference, notes, edit and delete; ordinary UI hides Paid From and uses the configured business payment account; loan repayments, driver advances, driver salaries and owner drawings are blocked from generic expense recording |
| Expense ledger | `app_pages/finance.py`, `services/finance_service.py` | Implemented read-only foundation | AppTest passed | Search/filter/details still planned |
| Finance general summaries | `app_pages/finance.py`, `services/dashboard_service.py` | Implemented foundation | AppTest passed | Definitions must be expanded as workflows are built |
| Balances page | `app_pages/finance.py`, `services/finance_service.py` | Implemented refined foundation | AppTest passed; unit tests cover negative Business Balance, loan repayment classification and recoverable driver-advance classification | Shows consolidated Business Balance, Money In, Money Out and chronological business ledger; individual Cash/Airtel/Bank balance cards are hidden from the visible page |
| Bus Accounts | `app_pages/accounts.py`, `services/bus_account_service.py`, `utils/dashboard_charts.py` | Implemented foundation | AppTest and unit tests passed; disposable expense/finance smoke passed | Shows recorded revenue, attributed operating costs, recorded bus contribution, shared/general costs separately, bus detail trend, costs by category and recent bus-related transactions |
| Business Presets | `app_pages/business_presets.py`, `services/preset_service.py`, `migrations/025_financial_foundation_and_presets.sql` | Implemented foundation | AppTest passed; unit tests cover effective-dated rate update behavior | Covers reporting baseline, Airtel collection destination, cashing rates, schedule rules, salary presets and reminder-warning days |
| Home dashboard | `app_pages/home.py`, `services/performance_service.py`, `utils/dashboard_charts.py` | Tested | Unit, AppTest and browser checks | Cumulative Total Revenue, Total Expenses and actual Business Balance; independent calendar controls and mobile horizontal scroll |
| Recent Activity | `services/dashboard_service.py` | Implemented limited foundation | AppTest passed | Derived only from real cashing, expense and maintenance records |
| Servicing records | `services/maintenance_service.py`, `app_pages/record_servicing.py` | Tested | Disposable PostgreSQL, form and browser checks | Cost components, completion/payment dates, one linked payment, zero-cost events, audited corrections |
| Maintenance schedules | `services/maintenance_service.py`, Buses/Home/Reminders | Tested | Threshold, backdating and PostgreSQL checks | 35 days from actual latest completion; initial 18 October for three buses |
| Reminders page | `app_pages/reminders.py`, `services/reminder_service.py` | Implemented read-only foundation | AppTest passed | Stored reminder completion/dismissal still planned |
| Document expiry | `bus_documents`, `services/reminder_service.py`, `app_pages/reminders.py` | Implemented foundation | AppTest passed | Derived expiry list exists; stored reminder generation and file uploads still planned |
| Payroll and advances | `app_pages/driver_money.py`, `services/driver_money_service.py`, `services/preset_service.py`, `app_pages/business_presets.py` | Implemented foundation | Unit tests, AppTest page tests and disposable money-workflow smoke passed | Supports salary preview, K1,000 default advance cap, configurable cap, advances, recovery allocation, salary recording and salary cancellation; broader editing/correction UI still planned |
| Financial accounts | `services/account_service.py`, `services/finance_service.py` | Implemented backend foundation | Unit tests and disposable DB opening-balance update passed historically | Account rows and opening-balance helpers remain for integrity/history; visible owner UI now emphasizes one consolidated Business Balance and Bus Accounts performance instead of separate Cash/Airtel/Bank cards |
| In-app backups | `app_pages/backups.py`, `services/backup_service.py` | Implemented foundation | Backup service created and verified a custom-format dump | Restore flow is manual |
| Reports/export | `app_pages/reports.py`, `services/business_report_service.py`, `services/report_export_service.py` | Tested | Report scenarios, Excel roundtrips, page and browser checks | One-page report, five CSV/Excel summaries, baseline reconciliation and quality warnings |
| Help & Guide | `app_pages/help_guide.py`, `utils/help_content.py` | Tested | Search/filter AppTest and desktop/mobile navigation/expansion checks | More entry; practical task guides, money explanations and supported corrections only |
| Controlled cleanup/reload | `services/financial_rules.py`, performance/finance/report services, `.streamlit/config.toml` | Tested | 98 tests, before/after calculations, preserved DB rows and disposable reload fixture | Shared rules/queries, reduced calls, polling watcher; no schema/deployment changes |
| Data validation warnings | `app_pages/home.py`, `app_pages/more.py`, `services/validation_service.py` | Implemented foundation | AppTest passed | Initial setup and backup warnings only |
| Transfers and fees | database only | Planned | none | Transfer fee rules seeded; service/UI not built |
| Owner loans | `app_pages/owner_money.py`, `services/loan_service.py`, database | Implemented foundation | AppTest page tests and disposable money-workflow smoke passed | Supports owner drawings, owner loans to business, owner-paid external loan repayments and business repayments to owner; edit/delete UI still planned |
| Business loans | `app_pages/loans.py`, `services/loan_service.py`, database | Implemented foundation | AppTest page tests and disposable money-workflow smoke passed | Supports adding loans, active/completed listing, repayment history, business-funded repayment, owner-personal repayment and unidentified repayments |
| Streamlit app shell | `app.py`, `app_pages/`, `components/` | Tested | Six changed screens at 390px/1440px and 16-page AppTest sweep | Local network operation |
| Bottom navigation | `components/layout.py` | Implemented foundation | AppTest passed | Need browser verification of `st.bottom` behavior |
| Shared UI components | `components/` | Implemented foundation | compileall passed | More components needed as workflows expand |
| Loading skeletons | `app_pages/home.py` | Implemented foundation | AppTest passed | Add skeletons to more data-heavy sections later |
| Automated tests | `tests/`, `scripts/smoke_*` | Tested | Step 4 unit, page, disposable PostgreSQL and browser coverage | Latest execution results in `docs/STEP4_IMPLEMENTATION.md` |
| Streamlit UI tests | ad hoc AppTest command | Implemented foundation | AppTest passed | Needs committed pytest/AppTest suite |
| Authentication/authorization | none | Blocked/Planned | none | Business role decisions needed before public deployment |
| Deployment docs | none | Planned | none | Not ready until app and security decisions exist |
