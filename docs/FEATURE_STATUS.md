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
| Route listing | `services/route_service.py` | Implemented | Indirectly exercised by route script only; no safe automated assertion yet | Needs proper pytest test database |
| Route creation | `services/route_service.py` | Implemented | Existing script is unsafe for routine baseline | Current script writes to dev DB and may duplicate `Kitwe - Ndola` |
| Bus listing | `services/bus_service.py` | Implemented | `python -m tests.test_bus_service` passed with 0 buses | Does not include driver assignments |
| Add bus | none | Planned | none | `buses` lacks model, seating capacity and documents; create supported MVP flow or approve migration |
| Edit bus | none | Planned | none | Must preserve history and route relationships |
| Activate/deactivate bus | none | Planned | none | Use `ACTIVE`/`INACTIVE`; deactivation date/reason not currently stored |
| In Garage filter | none | Blocked | none | Requires approved definition, likely from maintenance/downtime rather than bus status |
| Routes page | none | Planned | none | Needs Streamlit shell and route service expansion |
| Drivers page | none | Planned | none | Needs driver, employment and assignment services |
| Driver registration | none | Planned | none | Must respect employment history |
| Driver assignment | none | Planned | none | Unique active permanent assignment constraints already exist |
| Record Cashing | none | Planned | none | Must map simple UI to remittance collections, remittances and ledger rules |
| Collections view | none | Planned | none | Needs cashing service and historical driver lookup |
| Expense recording | none | Planned | none | Must preserve BUS, MULTI_BUS and GENERAL scope rules and payment source links |
| Expense ledger | none | Planned | none | Needs expense service and filters |
| Finance general summaries | none | Planned | none | Revenue, collections, expenses and balances must be defined separately |
| Balances page | none | Blocked/Planned | none | Requires validated opening/closing balance rules and transfer handling |
| Home dashboard | none | Planned | none | Needs real cashing, expense, reminders and bus data |
| Recent Activity | none | Blocked/Planned | none | No audit log; can derive only from real domain records where safe |
| Maintenance records | database only | Planned | none | Service and UI not built |
| Maintenance schedules | database only | Planned | none | Service and reminders not built |
| Reminders page | database only | Planned | none | Stored reminder table exists; automatic document expiry lacks document storage |
| Document expiry | generic reminders only | Blocked/Planned | none | No document metadata table; manual reminder is possible |
| Payroll and advances | database only | Planned | none | Service/UI not built; integrity functions exist |
| Financial accounts | database seed only | Planned | none | Account UI and balance rules not built |
| Transfers and fees | database only | Planned | none | Transfer fee rules seeded; service/UI not built |
| Owner loans | database seed only | Planned | none | Service/UI not built |
| Business loans | database only | Planned | none | Service/UI not built |
| Streamlit app shell | `app.py` | Blocked/Planned | none | `app.py` is empty |
| Bottom navigation | none | Planned | none | Need browser verification of `st.bottom`/fallback approach |
| Shared UI components | none | Planned | none | Not created yet |
| Loading skeletons | none | Planned | none | `st.skeleton` exists in installed Streamlit |
| Automated pytest suite | `tests/` | Blocked | pytest command fails | `pytest` missing and data-changing tests need isolation |
| Streamlit UI tests | none | Planned | none | App not implemented |
| Authentication/authorization | none | Blocked/Planned | none | Business role decisions needed before public deployment |
| Deployment docs | none | Planned | none | Not ready until app and security decisions exist |

