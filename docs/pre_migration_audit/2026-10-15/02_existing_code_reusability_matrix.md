# Existing Code Reusability Matrix

Date: 2026-10-15. Snapshot: 46c7643, migration/fastapi-flet.

## Classification rules

- **KEEP:** no major rewrite; retain behavior/tests, not a guarantee of every edge case.
- **ADAPT:** reusable code/rules, but change connection/config/transaction/DTO/auth or client-state boundary.
- **REWRITE:** Streamlit/Altair presentation cannot be transplanted into Flet. Preserve user behavior and test expectations.
- **REMOVE:** omit an obsolete/unused path from the *new runtime*, after parity checks. No source deletion is authorized by this audit.

Module-level ADAPT does not mean rewriting its SQL or financial algorithms. Function classifications below inherit the module boundary unless a more specific rule is shown. Top-level classes/functions are inventoried; test-class methods and nested functions are not separately enumerated. Constants and import-time page bodies are covered by module rows.

101 Python files: 24 services, 8 utils, 2 database, 18 pages, 6 components, 27 tests, 15 scripts, app.py. Package markers are included in these counts.

## Runtime entry point

| File | Class | Reason |
|---|---|---|
| [app.py](../../../app.py) | REWRITE | Streamlit page configuration/navigation/page execution; replace with API server entry and separate Flet routing, not a single combined process. |

## services

| File | Lines | Class | Rationale |
|---|---:|---|---|
| [services/__init__.py](../../../services/__init__.py) | 0 | KEEP | Package marker only; no business behavior, preserve or recreate as needed. |
| [services/account_service.py](../../../services/account_service.py) | 79 | ADAPT | Account list/default selection/opening updates reusable; require owner permission and balance/date contract. Negative-balance warning is an empty stub. |
| [services/backup_service.py](../../../services/backup_service.py) | 113 | ADAPT | Keep PostgreSQL backup approach; adapt Windows tool paths, restricted server jobs, permissions and off-host restore verification. |
| [services/bus_account_service.py](../../../services/bus_account_service.py) | 303 | ADAPT | Reuse attribution SQL only after summary/detail salary and operating-category definitions reconcile. |
| [services/bus_service.py](../../../services/bus_service.py) | 588 | ADAPT | Reuse fleet/history/metadata SQL and validation; adapt connection/UOW, historical overlap rules and explicit DTOs. |
| [services/business_report_service.py](../../../services/business_report_service.py) | 178 | ADAPT | Reuse report composition; adapt all reads to coherent snapshot and explicit period/expected-value contracts. |
| [services/cashing_service.py](../../../services/cashing_service.py) | 528 | ADAPT | Retain historical direct-entry compatibility and ledger reconciliation; adapt commands, audit, authorization and idempotency. |
| [services/correction_service.py](../../../services/correction_service.py) | 49 | ADAPT | Reuse JSON-safe snapshots; add authenticated actor, before/after policy and transactional audit coverage. |
| [services/dashboard_service.py](../../../services/dashboard_service.py) | 101 | ADAPT | Reuse query/delegation intent; adapt DTOs and explicit measure naming; avoid API endpoints that merely mirror legacy aliases. |
| [services/driver_money_service.py](../../../services/driver_money_service.py) | 720 | ADAPT | Keep proration/recovery/cap algorithms and locks; adapt UOW/command authorization/idempotency and correction policy. |
| [services/driver_service.py](../../../services/driver_service.py) | 196 | ADAPT | Reuse driver/employment create/update queries; define full lifecycle/history and permission contracts. |
| [services/expense_service.py](../../../services/expense_service.py) | 441 | ADAPT | Keep category/scope/payment/ledger rules; adapt DTO precision, audited corrections and shared transaction ownership. |
| [services/finance_service.py](../../../services/finance_service.py) | 226 | ADAPT | Reuse ledger query/summarization; reconcile similarly named balance scopes and transfer/opening semantics before exposing endpoints. |
| [services/financial_rules.py](../../../services/financial_rules.py) | 10 | KEEP | Pure shared operating/financing definitions; SQL predicate assumes documented query aliases and stays backend-side. |
| [services/loan_service.py](../../../services/loan_service.py) | 1005 | ADAPT | Keep debt/source/owner-money rules and locks; adapt commands/audit/idempotency; unknown principal/loan identity stays nullable. |
| [services/maintenance_service.py](../../../services/maintenance_service.py) | 164 | ADAPT | Reuse costs/scheduling/coordinated expense workflow; adapt UOW, permissions and command deduplication. |
| [services/performance_service.py](../../../services/performance_service.py) | 171 | ADAPT | Reuse pure Decimal timeline and operating queries; expose typed series; separate earned cost from cash payment. |
| [services/preset_service.py](../../../services/preset_service.py) | 519 | ADAPT | Keep effective-dated rate/salary/schedule/baseline rules; owner-only commands with transactional audit. |
| [services/reminder_service.py](../../../services/reminder_service.py) | 90 | ADAPT | Reuse read queries; adapt API DTOs/date policy. No push-notification service is implied. |
| [services/report_export_service.py](../../../services/report_export_service.py) | 101 | KEEP | Pure report table/CSV/XLSX builders and formula safety reusable; add authorized delivery, limits and device download tests. |
| [services/report_service.py](../../../services/report_service.py) | 78 | ADAPT | Reuse export SQL; legacy unfiltered balance helper is not the period report API and appears unused outside its definition. |
| [services/route_service.py](../../../services/route_service.py) | 44 | ADAPT | Reuse route list/create validation; adapt DTOs, permissions and request transaction/error boundaries. |
| [services/smart_cashing_service.py](../../../services/smart_cashing_service.py) | 842 | ADAPT | Keep coverage/expectation/allocation/obligation rules; adapt UOW, race-safe duplicate policy, command retries and corrections. |
| [services/validation_service.py](../../../services/validation_service.py) | 32 | ADAPT | Keep warning intent; adapt backend aggregation without UI state. Delegated negative-balance warning remains unimplemented. |

## utils

| File | Lines | Class | Rationale |
|---|---:|---|---|
| [utils/__init__.py](../../../utils/__init__.py) | 2 | KEEP | Package marker only; no business behavior, preserve or recreate as needed. |
| [utils/cashing_form.py](../../../utils/cashing_form.py) | 67 | ADAPT | Pure bus labels and direct-entry builder reusable; reset/version helper is tied to existing widget-key lifecycle. |
| [utils/dashboard_charts.py](../../../utils/dashboard_charts.py) | 163 | REWRITE | Altair/pandas presentation requires Flet rewrite. Keep numeric/zero-baseline/grouping test expectations, not renderer dependency. |
| [utils/dates.py](../../../utils/dates.py) | 48 | KEEP | Pure calendar/Lusaka helpers reusable; preserve their exact period semantics and verify platform timezone data. |
| [utils/formatting.py](../../../utils/formatting.py) | 27 | KEEP | Pure currency/date/status formatting reusable; keep amounts Decimal and refresh only UI-specific labels if needed. |
| [utils/help_content.py](../../../utils/help_content.py) | 191 | KEEP | Pure guide data/filter reusable; update guide text to migrated screen names and permissions. |
| [utils/reporting_periods.py](../../../utils/reporting_periods.py) | 28 | KEEP | Pure date-period/scheduled-date helpers reusable, with baseline and boundary tests. |
| [utils/validation.py](../../../utils/validation.py) | 49 | ADAPT | Text/integer validators reusable; money validators need explicit external finite/scale/range contract. |

## database

| File | Lines | Class | Rationale |
|---|---:|---|---|
| [database/__init__.py](../../../database/__init__.py) | 0 | KEEP | Package marker only; no business behavior, preserve or recreate as needed. |
| [database/connection.py](../../../database/connection.py) | 16 | ADAPT | Reuse psycopg approach; replace implicit settings/superuser with validated configuration, restricted role, timeout and injectable UOW. |

## app_pages

| File | Lines | Class | Rationale |
|---|---:|---|---|
| [app_pages/__init__.py](../../../app_pages/__init__.py) | 2 | KEEP | Package marker only; no business behavior, preserve or recreate as needed. |
| [app_pages/accounts.py](../../../app_pages/accounts.py) | 145 | REWRITE | Bus Accounts summary/detail selection and charts; fix query definition mismatch before port. |
| [app_pages/add_bus.py](../../../app_pages/add_bus.py) | 191 | REWRITE | Bus creation/document metadata form; retain validation and prevent duplicate submit. |
| [app_pages/backups.py](../../../app_pages/backups.py) | 42 | REWRITE | Owner-only backup UI; backend job/download authorization required. |
| [app_pages/buses.py](../../../app_pages/buses.py) | 325 | REWRITE | Buses/Routes/Drivers tabs, edit/status actions and caching become client views and API queries. |
| [app_pages/business_presets.py](../../../app_pages/business_presets.py) | 278 | REWRITE | Owner settings/effective-dated presets; preserve audit and no silent historical reclassification. |
| [app_pages/driver_money.py](../../../app_pages/driver_money.py) | 184 | REWRITE | Payroll/advance forms and cancellation review; keep algorithms server-side. |
| [app_pages/finance.py](../../../app_pages/finance.py) | 130 | REWRITE | General/Collections/Expenses/Balances views with agreed independent current balance. |
| [app_pages/help_guide.py](../../../app_pages/help_guide.py) | 30 | REWRITE | Searchable help controls; reuse pure guide data. |
| [app_pages/home.py](../../../app_pages/home.py) | 172 | REWRITE | Overview/cache/filter/chart controls; preserve broad cards and actual currency-scale charts. |
| [app_pages/loans.py](../../../app_pages/loans.py) | 147 | REWRITE | Known/unidentified lender payments and nullable loan terms; API authority required. |
| [app_pages/more.py](../../../app_pages/more.py) | 35 | REWRITE | Navigation menu becomes Flet route/menu. |
| [app_pages/owner_money.py](../../../app_pages/owner_money.py) | 150 | REWRITE | Owner funding/drawing/repayment workflow, not ordinary expense shortcuts. |
| [app_pages/record_cashing.py](../../../app_pages/record_cashing.py) | 821 | REWRITE | Single-form UI plus mixed allocation/variance/correction logic; extract domain rules, rewrite controls. |
| [app_pages/record_expense.py](../../../app_pages/record_expense.py) | 252 | REWRITE | Category groups/payment source/allocations/edit/delete forms; adapt correction policy. |
| [app_pages/record_servicing.py](../../../app_pages/record_servicing.py) | 31 | REWRITE | Thin servicing screen wrapper; shared form rewritten. |
| [app_pages/reminders.py](../../../app_pages/reminders.py) | 64 | REWRITE | Due/expiry views become client controls over reusable read queries. |
| [app_pages/reports.py](../../../app_pages/reports.py) | 130 | REWRITE | Period/report/export UI; backend snapshot and native download support needed. |

## components

| File | Lines | Class | Rationale |
|---|---:|---|---|
| [components/__init__.py](../../../components/__init__.py) | 2 | KEEP | Package marker only; no business behavior, preserve or recreate as needed. |
| [components/cards.py](../../../components/cards.py) | 17 | REWRITE | Streamlit empty/badge rendering becomes Flet controls. |
| [components/forms.py](../../../components/forms.py) | 11 | REMOVE | No call sites found by repository search. Omit these Streamlit success-state helpers from new runtime; do not delete legacy checkpoint. |
| [components/layout.py](../../../components/layout.py) | 151 | REWRITE | Streamlit CSS/fixed containers/nav reruns replaced by native responsive layout/navigation. |
| [components/reporting_period.py](../../../components/reporting_period.py) | 20 | REWRITE | Rewrite widget state/control rendering; reuse utils.reporting_periods for calculations. |
| [components/servicing_form.py](../../../components/servicing_form.py) | 48 | REWRITE | Rewrite Streamlit inputs; move remaining cost/form validation into domain layer and preserve coordinated servicing behavior. |

## tests

| File | Lines | Class | Rationale |
|---|---:|---|---|
| [tests/__init__.py](../../../tests/__init__.py) | 0 | KEEP | Package marker only; no business behavior, preserve or recreate as needed. |
| [tests/inspect_buses.py](../../../tests/inspect_buses.py) | 61 | ADAPT | Diagnostic script, not a test_ module; verify private-output/test-target safeguards. |
| [tests/test_bus_account_service.py](../../../tests/test_bus_account_service.py) | 93 | ADAPT | Retain behavioral assertions/fixtures; adapt connection seams and presentation-specific assertions; add HTTP, commit and race coverage. |
| [tests/test_bus_accounts_page.py](../../../tests/test_bus_accounts_page.py) | 84 | REWRITE | Streamlit AppTest/UI fixtures become API/Flet equivalents; keep existing tests during parity work. |
| [tests/test_bus_service.py](../../../tests/test_bus_service.py) | 19 | ADAPT | Retain behavioral assertions/fixtures; adapt connection seams and presentation-specific assertions; add HTTP, commit and race coverage. |
| [tests/test_business_performance.py](../../../tests/test_business_performance.py) | 52 | ADAPT | Retain behavioral assertions/fixtures; adapt connection seams and presentation-specific assertions; add HTTP, commit and race coverage. |
| [tests/test_cashing_form.py](../../../tests/test_cashing_form.py) | 71 | ADAPT | Retain behavioral assertions/fixtures; adapt connection seams and presentation-specific assertions; add HTTP, commit and race coverage. |
| [tests/test_cashing_service.py](../../../tests/test_cashing_service.py) | 111 | ADAPT | Retain behavioral assertions/fixtures; adapt connection seams and presentation-specific assertions; add HTTP, commit and race coverage. |
| [tests/test_connection.py](../../../tests/test_connection.py) | 27 | ADAPT | Retain behavioral assertions/fixtures; adapt connection seams and presentation-specific assertions; add HTTP, commit and race coverage. |
| [tests/test_dashboard_charts.py](../../../tests/test_dashboard_charts.py) | 38 | ADAPT | Retain behavioral assertions/fixtures; adapt connection seams and presentation-specific assertions; add HTTP, commit and race coverage. |
| [tests/test_driver_money_service.py](../../../tests/test_driver_money_service.py) | 47 | ADAPT | Retain behavioral assertions/fixtures; adapt connection seams and presentation-specific assertions; add HTTP, commit and race coverage. |
| [tests/test_expense_service.py](../../../tests/test_expense_service.py) | 206 | ADAPT | Retain behavioral assertions/fixtures; adapt connection seams and presentation-specific assertions; add HTTP, commit and race coverage. |
| [tests/test_finance_ledger_reuse.py](../../../tests/test_finance_ledger_reuse.py) | 32 | ADAPT | Retain behavioral assertions/fixtures; adapt connection seams and presentation-specific assertions; add HTTP, commit and race coverage. |
| [tests/test_financial_foundation.py](../../../tests/test_financial_foundation.py) | 211 | ADAPT | Retain behavioral assertions/fixtures; adapt connection seams and presentation-specific assertions; add HTTP, commit and race coverage. |
| [tests/test_financial_timeline.py](../../../tests/test_financial_timeline.py) | 34 | ADAPT | Retain behavioral assertions/fixtures; adapt connection seams and presentation-specific assertions; add HTTP, commit and race coverage. |
| [tests/test_fleet_history.py](../../../tests/test_fleet_history.py) | 68 | ADAPT | Retain behavioral assertions/fixtures; adapt connection seams and presentation-specific assertions; add HTTP, commit and race coverage. |
| [tests/test_help_guide.py](../../../tests/test_help_guide.py) | 31 | ADAPT | Retain behavioral assertions/fixtures; adapt connection seams and presentation-specific assertions; add HTTP, commit and race coverage. |
| [tests/test_home_page.py](../../../tests/test_home_page.py) | 54 | REWRITE | Streamlit AppTest/UI fixtures become API/Flet equivalents; keep existing tests during parity work. |
| [tests/test_money_management_pages.py](../../../tests/test_money_management_pages.py) | 226 | REWRITE | Streamlit AppTest/UI fixtures become API/Flet equivalents; keep existing tests during parity work. |
| [tests/test_record_cashing_page.py](../../../tests/test_record_cashing_page.py) | 333 | REWRITE | Streamlit AppTest/UI fixtures become API/Flet equivalents; keep existing tests during parity work. |
| [tests/test_record_expense_page.py](../../../tests/test_record_expense_page.py) | 95 | REWRITE | Streamlit AppTest/UI fixtures become API/Flet equivalents; keep existing tests during parity work. |
| [tests/test_report_exports.py](../../../tests/test_report_exports.py) | 29 | ADAPT | Retain behavioral assertions/fixtures; adapt connection seams and presentation-specific assertions; add HTTP, commit and race coverage. |
| [tests/test_reporting_periods.py](../../../tests/test_reporting_periods.py) | 30 | ADAPT | Retain behavioral assertions/fixtures; adapt connection seams and presentation-specific assertions; add HTTP, commit and race coverage. |
| [tests/test_route_service.py](../../../tests/test_route_service.py) | 18 | ADAPT | Retain behavioral assertions/fixtures; adapt connection seams and presentation-specific assertions; add HTTP, commit and race coverage. |
| [tests/test_servicing.py](../../../tests/test_servicing.py) | 21 | ADAPT | Retain behavioral assertions/fixtures; adapt connection seams and presentation-specific assertions; add HTTP, commit and race coverage. |
| [tests/test_servicing_page.py](../../../tests/test_servicing_page.py) | 37 | REWRITE | Streamlit AppTest/UI fixtures become API/Flet equivalents; keep existing tests during parity work. |
| [tests/test_smart_cashing_service.py](../../../tests/test_smart_cashing_service.py) | 116 | ADAPT | Retain behavioral assertions/fixtures; adapt connection seams and presentation-specific assertions; add HTTP, commit and race coverage. |

## scripts

| File | Lines | Class | Rationale |
|---|---:|---|---|
| [scripts/profile_step5_queries.py](../../../scripts/profile_step5_queries.py) | 71 | ADAPT | Retain diagnostic/integration intent; force isolated targets and approved permissions; scripts may mutate/restore and were not run in audit. |
| [scripts/seed_demo_data.py](../../../scripts/seed_demo_data.py) | 509 | ADAPT | Retain diagnostic/integration intent; force isolated targets and approved permissions; scripts may mutate/restore and were not run in audit. |
| [scripts/smoke_expense_finance.py](../../../scripts/smoke_expense_finance.py) | 114 | ADAPT | Retain diagnostic/integration intent; force isolated targets and approved permissions; scripts may mutate/restore and were not run in audit. |
| [scripts/smoke_help_ui.py](../../../scripts/smoke_help_ui.py) | 42 | REWRITE | Streamlit page smoke checks must become API/Flet/device checks; retain as legacy evidence. |
| [scripts/smoke_money_workflows.py](../../../scripts/smoke_money_workflows.py) | 175 | ADAPT | Retain diagnostic/integration intent; force isolated targets and approved permissions; scripts may mutate/restore and were not run in audit. |
| [scripts/smoke_service_reload.py](../../../scripts/smoke_service_reload.py) | 59 | REMOVE | Streamlit hot-reload regression harness is legacy-only; omit from new runtime/test architecture, retain in old checkpoint. |
| [scripts/smoke_smart_cashing.py](../../../scripts/smoke_smart_cashing.py) | 128 | ADAPT | Retain diagnostic/integration intent; force isolated targets and approved permissions; scripts may mutate/restore and were not run in audit. |
| [scripts/smoke_step4.py](../../../scripts/smoke_step4.py) | 118 | ADAPT | Retain diagnostic/integration intent; force isolated targets and approved permissions; scripts may mutate/restore and were not run in audit. |
| [scripts/smoke_step4_pages.py](../../../scripts/smoke_step4_pages.py) | 48 | REWRITE | Streamlit page smoke checks must become API/Flet/device checks; retain as legacy evidence. |
| [scripts/smoke_step4_ui.py](../../../scripts/smoke_step4_ui.py) | 55 | REWRITE | Streamlit page smoke checks must become API/Flet/device checks; retain as legacy evidence. |
| [scripts/verify_migrations.py](../../../scripts/verify_migrations.py) | 56 | ADAPT | Retain diagnostic/integration intent; force isolated targets and approved permissions; scripts may mutate/restore and were not run in audit. |
| [scripts/verify_step4_backup.py](../../../scripts/verify_step4_backup.py) | 47 | ADAPT | Retain diagnostic/integration intent; force isolated targets and approved permissions; scripts may mutate/restore and were not run in audit. |
| [scripts/verify_step4_live.py](../../../scripts/verify_step4_live.py) | 29 | ADAPT | Retain diagnostic/integration intent; force isolated targets and approved permissions; scripts may mutate/restore and were not run in audit. |
| [scripts/verify_step5_calculations.py](../../../scripts/verify_step5_calculations.py) | 38 | ADAPT | Retain diagnostic/integration intent; force isolated targets and approved permissions; scripts may mutate/restore and were not run in audit. |
| [scripts/verify_step5_records.py](../../../scripts/verify_step5_records.py) | 34 | ADAPT | Retain diagnostic/integration intent; force isolated targets and approved permissions; scripts may mutate/restore and were not run in audit. |

## Function and class inventory

References below are verified top-level definition lines at the audited checkpoint. Default rationale: the module row's rationale; function-specific exceptions are shown. UI modules may execute substantial code outside functions, so an empty definition list is not an empty screen.

### services

| File / definition | Line | Class | Specific note |
|---|---:|---|---|
| [services/account_service.py :: get_accounts_for_management](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/account_service.py#L8) | 8 | ADAPT | Inherits module rationale above. |
| [services/account_service.py :: update_opening_balance](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/account_service.py#L38) | 38 | ADAPT | Inherits module rationale above. |
| [services/account_service.py :: get_default_business_payment_account](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/account_service.py#L57) | 57 | ADAPT | Inherits module rationale above. |
| [services/account_service.py :: get_negative_balance_warnings](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/account_service.py#L78) | 78 | ADAPT | Stub returns []; implement only after warning policy approved. |
| [services/backup_service.py :: _load_database_settings](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/backup_service.py#L25) | 25 | ADAPT | Inherits module rationale above. |
| [services/backup_service.py :: _find_tool](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/backup_service.py#L34) | 34 | ADAPT | Inherits module rationale above. |
| [services/backup_service.py :: create_database_backup](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/backup_service.py#L44) | 44 | ADAPT | Inherits module rationale above. |
| [services/backup_service.py :: verify_backup](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/backup_service.py#L80) | 80 | ADAPT | Inherits module rationale above. |
| [services/backup_service.py :: list_backups](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/backup_service.py#L93) | 93 | ADAPT | Inherits module rationale above. |
| [services/backup_service.py :: latest_backup_age_hours](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/backup_service.py#L108) | 108 | ADAPT | Inherits module rationale above. |
| [services/bus_account_service.py :: get_bus_contribution_summary](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/bus_account_service.py#L10) | 10 | ADAPT | Inherits module rationale above. |
| [services/bus_account_service.py :: get_bus_account_detail](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/bus_account_service.py#L170) | 170 | ADAPT | Inherits module rationale above. |
| [services/bus_service.py :: get_all_buses](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/bus_service.py#L18) | 18 | ADAPT | Inherits module rationale above. |
| [services/bus_service.py :: get_buses_overview](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/bus_service.py#L40) | 40 | ADAPT | Inherits module rationale above. |
| [services/bus_service.py :: get_bus_details](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/bus_service.py#L124) | 124 | ADAPT | Inherits module rationale above. |
| [services/bus_service.py :: get_bus_status_history](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/bus_service.py#L193) | 193 | ADAPT | Inherits module rationale above. |
| [services/bus_service.py :: _validate_route](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/bus_service.py#L197) | 197 | ADAPT | Inherits module rationale above. |
| [services/bus_service.py :: _close_current_status](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/bus_service.py#L211) | 211 | ADAPT | Inherits module rationale above. |
| [services/bus_service.py :: _close_current_route](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/bus_service.py#L238) | 238 | ADAPT | Inherits module rationale above. |
| [services/bus_service.py :: update_bus](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/bus_service.py#L265) | 265 | ADAPT | Inherits module rationale above. |
| [services/bus_service.py :: set_bus_status](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/bus_service.py#L335) | 335 | ADAPT | Inherits module rationale above. |
| [services/bus_service.py :: _period_days](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/bus_service.py#L383) | 383 | ADAPT | Inherits module rationale above. |
| [services/bus_service.py :: count_active_days_from_history](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/bus_service.py#L392) | 392 | ADAPT | Inherits module rationale above. |
| [services/bus_service.py :: get_bus_active_day_counts](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/bus_service.py#L410) | 410 | ADAPT | Inherits module rationale above. |
| [services/bus_service.py :: _clean_document_records](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/bus_service.py#L451) | 451 | ADAPT | Inherits module rationale above. |
| [services/bus_service.py :: create_bus](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/bus_service.py#L477) | 477 | ADAPT | Inherits module rationale above. |
| [services/business_report_service.py :: _query](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/business_report_service.py#L20) | 20 | ADAPT | Inherits module rationale above. |
| [services/business_report_service.py :: get_business_report](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/business_report_service.py#L27) | 27 | ADAPT | Inherits module rationale above. |
| [services/business_report_service.py :: get_reconciliation](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/business_report_service.py#L108) | 108 | ADAPT | Inherits module rationale above. |
| [services/business_report_service.py :: get_report_warnings](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/business_report_service.py#L124) | 124 | ADAPT | Inherits module rationale above. |
| [services/cashing_service.py :: get_active_financial_accounts](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/cashing_service.py#L14) | 14 | ADAPT | Inherits module rationale above. |
| [services/cashing_service.py :: get_collection_destination_account](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/cashing_service.py#L28) | 28 | ADAPT | Inherits module rationale above. |
| [services/cashing_service.py :: get_cashing_rates_for_date](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/cashing_service.py#L49) | 49 | ADAPT | Inherits module rationale above. |
| [services/cashing_service.py :: get_recent_cashing_collections](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/cashing_service.py#L57) | 57 | ADAPT | Inherits module rationale above. |
| [services/cashing_service.py :: get_cashing_collection](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/cashing_service.py#L105) | 105 | ADAPT | Inherits module rationale above. |
| [services/cashing_service.py :: _format_duplicate](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/cashing_service.py#L163) | 163 | ADAPT | Inherits module rationale above. |
| [services/cashing_service.py :: _find_existing_cashing_entries](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/cashing_service.py#L174) | 174 | ADAPT | Inherits module rationale above. |
| [services/cashing_service.py :: _coerce_collection_date](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/cashing_service.py#L208) | 208 | ADAPT | Inherits module rationale above. |
| [services/cashing_service.py :: _clean_direct_entry](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/cashing_service.py#L216) | 216 | ADAPT | Inherits module rationale above. |
| [services/cashing_service.py :: _clean_direct_entries](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/cashing_service.py#L238) | 238 | ADAPT | Inherits module rationale above. |
| [services/cashing_service.py :: _assert_active_account](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/cashing_service.py#L245) | 245 | ADAPT | Inherits module rationale above. |
| [services/cashing_service.py :: _insert_financial_transaction](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/cashing_service.py#L263) | 263 | ADAPT | Inherits module rationale above. |
| [services/cashing_service.py :: _update_financial_transaction](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/cashing_service.py#L295) | 295 | ADAPT | Inherits module rationale above. |
| [services/cashing_service.py :: _insert_remittance_rows](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/cashing_service.py#L325) | 325 | ADAPT | Inherits module rationale above. |
| [services/cashing_service.py :: record_direct_cashing_collection](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/cashing_service.py#L356) | 356 | ADAPT | Inherits module rationale above. |
| [services/cashing_service.py :: update_direct_cashing_collection](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/cashing_service.py#L409) | 409 | ADAPT | Inherits module rationale above. |
| [services/cashing_service.py :: delete_cashing_collection](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/cashing_service.py#L491) | 491 | ADAPT | Inherits module rationale above. |
| [services/correction_service.py :: _json_safe](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/correction_service.py#L11) | 11 | KEEP | Pure JSON-safe snapshot conversion. |
| [services/correction_service.py :: record_correction_audit](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/correction_service.py#L23) | 23 | ADAPT | Inherits module rationale above. |
| [services/dashboard_service.py :: get_financial_summary](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/dashboard_service.py#L10) | 10 | ADAPT | Inherits module rationale above. |
| [services/dashboard_service.py :: get_bus_status_counts](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/dashboard_service.py#L14) | 14 | ADAPT | Inherits module rationale above. |
| [services/dashboard_service.py :: get_bus_performance](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/dashboard_service.py#L33) | 33 | ADAPT | Inherits module rationale above. |
| [services/dashboard_service.py :: get_activity_date_bounds](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/dashboard_service.py#L45) | 45 | ADAPT | Inherits module rationale above. |
| [services/dashboard_service.py :: get_recent_activity](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/dashboard_service.py#L65) | 65 | ADAPT | Inherits module rationale above. |
| [services/driver_money_service.py :: _money](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_money_service.py#L19) | 19 | ADAPT | Inherits module rationale above. |
| [services/driver_money_service.py :: _coerce_date](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_money_service.py#L23) | 23 | ADAPT | Inherits module rationale above. |
| [services/driver_money_service.py :: _month_bounds](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_money_service.py#L31) | 31 | ADAPT | Inherits module rationale above. |
| [services/driver_money_service.py :: _overlap_days](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_money_service.py#L39) | 39 | ADAPT | Inherits module rationale above. |
| [services/driver_money_service.py :: list_driver_money_profiles](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_money_service.py#L48) | 48 | ADAPT | Inherits module rationale above. |
| [services/driver_money_service.py :: _load_employment](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_money_service.py#L75) | 75 | ADAPT | Inherits module rationale above. |
| [services/driver_money_service.py :: _get_effective_monthly_salary](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_money_service.py#L100) | 100 | ADAPT | Inherits module rationale above. |
| [services/driver_money_service.py :: _outstanding_advances_query](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_money_service.py#L120) | 120 | ADAPT | Inherits module rationale above. |
| [services/driver_money_service.py :: list_outstanding_advances](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_money_service.py#L144) | 144 | ADAPT | Inherits module rationale above. |
| [services/driver_money_service.py :: get_driver_money_detail](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_money_service.py#L151) | 151 | ADAPT | Inherits module rationale above. |
| [services/driver_money_service.py :: get_salary_preview](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_money_service.py#L204) | 204 | ADAPT | Inherits module rationale above. |
| [services/driver_money_service.py :: _allocate_recovery](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_money_service.py#L244) | 244 | ADAPT | Inherits module rationale above. |
| [services/driver_money_service.py :: _refresh_advance_status](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_money_service.py#L259) | 259 | ADAPT | Inherits module rationale above. |
| [services/driver_money_service.py :: record_driver_advance](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_money_service.py#L280) | 280 | ADAPT | Inherits module rationale above. |
| [services/driver_money_service.py :: record_driver_salary](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_money_service.py#L370) | 370 | ADAPT | Inherits module rationale above. |
| [services/driver_money_service.py :: cancel_driver_advance](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_money_service.py#L510) | 510 | ADAPT | Inherits module rationale above. |
| [services/driver_money_service.py :: cancel_driver_salary](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_money_service.py#L574) | 574 | ADAPT | Inherits module rationale above. |
| [services/driver_money_service.py :: reclassify_expense_as_driver_salary](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_money_service.py#L635) | 635 | ADAPT | Inherits module rationale above. |
| [services/driver_service.py :: get_available_driver_employments](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_service.py#L9) | 9 | ADAPT | Inherits module rationale above. |
| [services/driver_service.py :: get_drivers_overview](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_service.py#L40) | 40 | ADAPT | Inherits module rationale above. |
| [services/driver_service.py :: create_driver](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_service.py#L66) | 66 | ADAPT | Inherits module rationale above. |
| [services/driver_service.py :: get_driver](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_service.py#L128) | 128 | ADAPT | Inherits module rationale above. |
| [services/driver_service.py :: update_driver](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/driver_service.py#L159) | 159 | ADAPT | Inherits module rationale above. |
| [services/expense_service.py :: is_restricted_expense_category](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/expense_service.py#L18) | 18 | ADAPT | Inherits module rationale above. |
| [services/expense_service.py :: _clean_expense_title](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/expense_service.py#L22) | 22 | ADAPT | Inherits module rationale above. |
| [services/expense_service.py :: get_active_expense_categories](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/expense_service.py#L33) | 33 | ADAPT | Inherits module rationale above. |
| [services/expense_service.py :: get_operating_expense_categories](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/expense_service.py#L47) | 47 | ADAPT | Inherits module rationale above. |
| [services/expense_service.py :: get_active_payment_accounts](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/expense_service.py#L55) | 55 | ADAPT | Inherits module rationale above. |
| [services/expense_service.py :: get_recent_expenses](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/expense_service.py#L69) | 69 | ADAPT | Inherits module rationale above. |
| [services/expense_service.py :: get_expense](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/expense_service.py#L98) | 98 | ADAPT | Inherits module rationale above. |
| [services/expense_service.py :: _coerce_expense_date](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/expense_service.py#L132) | 132 | ADAPT | Inherits module rationale above. |
| [services/expense_service.py :: _resolve_payment_account_id](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/expense_service.py#L140) | 140 | ADAPT | Inherits module rationale above. |
| [services/expense_service.py :: _load_expense_category](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/expense_service.py#L146) | 146 | ADAPT | Inherits module rationale above. |
| [services/expense_service.py :: record_business_expense](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/expense_service.py#L164) | 164 | ADAPT | Inherits module rationale above. |
| [services/expense_service.py :: update_business_expense](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/expense_service.py#L276) | 276 | ADAPT | Inherits module rationale above. |
| [services/expense_service.py :: delete_business_expense](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/expense_service.py#L404) | 404 | ADAPT | Inherits module rationale above. |
| [services/finance_service.py :: get_period_ledger](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/finance_service.py#L11) | 11 | ADAPT | Inherits module rationale above. |
| [services/finance_service.py :: summarize_ledger](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/finance_service.py#L23) | 23 | ADAPT | Inherits module rationale above. |
| [services/finance_service.py :: get_period_balance](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/finance_service.py#L49) | 49 | ADAPT | Inherits module rationale above. |
| [services/finance_service.py :: get_collections](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/finance_service.py#L70) | 70 | ADAPT | Inherits module rationale above. |
| [services/finance_service.py :: get_expenses](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/finance_service.py#L92) | 92 | ADAPT | Inherits module rationale above. |
| [services/finance_service.py :: get_account_balances](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/finance_service.py#L116) | 116 | ADAPT | Inherits module rationale above. |
| [services/finance_service.py :: get_business_balance](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/finance_service.py#L144) | 144 | ADAPT | Inherits module rationale above. |
| [services/finance_service.py :: get_business_ledger](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/finance_service.py#L185) | 185 | ADAPT | Inherits module rationale above. |
| [services/loan_service.py :: _coerce_date](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/loan_service.py#L20) | 20 | ADAPT | Inherits module rationale above. |
| [services/loan_service.py :: _owner_loan_id](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/loan_service.py#L28) | 28 | ADAPT | Inherits module rationale above. |
| [services/loan_service.py :: _category_id](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/loan_service.py#L44) | 44 | ADAPT | Inherits module rationale above. |
| [services/loan_service.py :: list_business_loans](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/loan_service.py#L52) | 52 | ADAPT | Inherits module rationale above. |
| [services/loan_service.py :: list_loan_repayments](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/loan_service.py#L81) | 81 | ADAPT | Inherits module rationale above. |
| [services/loan_service.py :: list_owner_money_activity](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/loan_service.py#L107) | 107 | ADAPT | Inherits module rationale above. |
| [services/loan_service.py :: get_owner_money_summary](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/loan_service.py#L168) | 168 | ADAPT | Inherits module rationale above. |
| [services/loan_service.py :: add_business_loan](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/loan_service.py#L213) | 213 | ADAPT | Inherits module rationale above. |
| [services/loan_service.py :: _loan_outstanding](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/loan_service.py#L263) | 263 | ADAPT | Inherits module rationale above. |
| [services/loan_service.py :: _mark_loan_if_complete](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/loan_service.py#L289) | 289 | ADAPT | Inherits module rationale above. |
| [services/loan_service.py :: _owner_outstanding](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/loan_service.py#L310) | 310 | ADAPT | Inherits module rationale above. |
| [services/loan_service.py :: cancel_loan_repayment](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/loan_service.py#L323) | 323 | ADAPT | Inherits module rationale above. |
| [services/loan_service.py :: record_loan_repayment](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/loan_service.py#L390) | 390 | ADAPT | Inherits module rationale above. |
| [services/loan_service.py :: record_unidentified_business_loan_repayment](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/loan_service.py#L607) | 607 | ADAPT | Inherits module rationale above. |
| [services/loan_service.py :: record_owner_loan_to_business](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/loan_service.py#L627) | 627 | ADAPT | Inherits module rationale above. |
| [services/loan_service.py :: record_owner_drawing](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/loan_service.py#L681) | 681 | ADAPT | Inherits module rationale above. |
| [services/loan_service.py :: record_business_repayment_to_owner](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/loan_service.py#L741) | 741 | ADAPT | Inherits module rationale above. |
| [services/loan_service.py :: cancel_owner_loan_transaction](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/loan_service.py#L811) | 811 | ADAPT | Inherits module rationale above. |
| [services/loan_service.py :: cancel_owner_drawing](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/loan_service.py#L873) | 873 | ADAPT | Inherits module rationale above. |
| [services/loan_service.py :: reclassify_expense_as_loan_repayment](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/loan_service.py#L923) | 923 | ADAPT | Inherits module rationale above. |
| [services/maintenance_service.py :: servicing_warning](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/maintenance_service.py#L11) | 11 | ADAPT | Inherits module rationale above. |
| [services/maintenance_service.py :: servicing_costs](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/maintenance_service.py#L24) | 24 | ADAPT | Inherits module rationale above. |
| [services/maintenance_service.py :: get_servicing_schedules](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/maintenance_service.py#L34) | 34 | ADAPT | Inherits module rationale above. |
| [services/maintenance_service.py :: get_servicing_history](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/maintenance_service.py#L45) | 45 | ADAPT | Inherits module rationale above. |
| [services/maintenance_service.py :: _refresh_schedule](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/maintenance_service.py#L58) | 58 | ADAPT | Inherits module rationale above. |
| [services/maintenance_service.py :: set_servicing_schedule](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/maintenance_service.py#L74) | 74 | ADAPT | Inherits module rationale above. |
| [services/maintenance_service.py :: record_servicing](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/maintenance_service.py#L92) | 92 | ADAPT | Inherits module rationale above. |
| [services/performance_service.py :: build_financial_timeline](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/performance_service.py#L15) | 15 | KEEP | Pure timeline algorithm; preserve Decimal and behavioral tests. |
| [services/performance_service.py :: get_business_financial_timeline](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/performance_service.py#L46) | 46 | ADAPT | Inherits module rationale above. |
| [services/performance_service.py :: _load_operating_activity](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/performance_service.py#L56) | 56 | ADAPT | Inherits module rationale above. |
| [services/performance_service.py :: get_operating_summary](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/performance_service.py#L87) | 87 | ADAPT | Inherits module rationale above. |
| [services/performance_service.py :: _daily_points](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/performance_service.py#L109) | 109 | ADAPT | Inherits module rationale above. |
| [services/performance_service.py :: _monday_start](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/performance_service.py#L124) | 124 | ADAPT | Inherits module rationale above. |
| [services/performance_service.py :: _rollup_weekly](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/performance_service.py#L129) | 129 | ADAPT | Inherits module rationale above. |
| [services/performance_service.py :: get_business_performance_series](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/performance_service.py#L151) | 151 | ADAPT | Inherits module rationale above. |
| [services/preset_service.py :: _coerce_date](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/preset_service.py#L15) | 15 | ADAPT | Inherits module rationale above. |
| [services/preset_service.py :: _record_audit](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/preset_service.py#L21) | 21 | ADAPT | Inherits module rationale above. |
| [services/preset_service.py :: get_business_settings](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/preset_service.py#L53) | 53 | ADAPT | Inherits module rationale above. |
| [services/preset_service.py :: get_business_setting](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/preset_service.py#L66) | 66 | ADAPT | Inherits module rationale above. |
| [services/preset_service.py :: get_reporting_baseline_date](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/preset_service.py#L81) | 81 | ADAPT | Inherits module rationale above. |
| [services/preset_service.py :: set_reporting_baseline_date](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/preset_service.py#L86) | 86 | ADAPT | Inherits module rationale above. |
| [services/preset_service.py :: get_driver_advance_limit](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/preset_service.py#L123) | 123 | ADAPT | Inherits module rationale above. |
| [services/preset_service.py :: set_driver_advance_limit](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/preset_service.py#L128) | 128 | ADAPT | Inherits module rationale above. |
| [services/preset_service.py :: get_default_collection_account_type](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/preset_service.py#L168) | 168 | ADAPT | Inherits module rationale above. |
| [services/preset_service.py :: list_cashing_rates](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/preset_service.py#L175) | 175 | ADAPT | Inherits module rationale above. |
| [services/preset_service.py :: get_effective_cashing_rates](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/preset_service.py#L188) | 188 | ADAPT | Inherits module rationale above. |
| [services/preset_service.py :: set_cashing_rate](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/preset_service.py#L207) | 207 | ADAPT | Inherits module rationale above. |
| [services/preset_service.py :: list_cashing_schedule_rules](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/preset_service.py#L267) | 267 | ADAPT | Inherits module rationale above. |
| [services/preset_service.py :: set_cashing_schedule_rule](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/preset_service.py#L281) | 281 | ADAPT | Inherits module rationale above. |
| [services/preset_service.py :: list_driver_salary_presets](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/preset_service.py#L362) | 362 | ADAPT | Inherits module rationale above. |
| [services/preset_service.py :: set_driver_salary_preset](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/preset_service.py#L384) | 384 | ADAPT | Inherits module rationale above. |
| [services/preset_service.py :: list_reminder_presets](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/preset_service.py#L455) | 455 | ADAPT | Inherits module rationale above. |
| [services/preset_service.py :: set_reminder_preset](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/preset_service.py#L468) | 468 | ADAPT | Inherits module rationale above. |
| [services/reminder_service.py :: get_due_maintenance](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/reminder_service.py#L8) | 8 | ADAPT | Inherits module rationale above. |
| [services/reminder_service.py :: get_deactivated_buses](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/reminder_service.py#L32) | 32 | ADAPT | Inherits module rationale above. |
| [services/reminder_service.py :: get_document_expiries](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/reminder_service.py#L46) | 46 | ADAPT | Inherits module rationale above. |
| [services/reminder_service.py :: get_open_reminders](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/reminder_service.py#L69) | 69 | ADAPT | Inherits module rationale above. |
| [services/report_export_service.py :: report_export_tables](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/report_export_service.py#L8) | 8 | KEEP | Inherits module rationale above. |
| [services/report_export_service.py :: _safe_cell](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/report_export_service.py#L62) | 62 | KEEP | Inherits module rationale above. |
| [services/report_export_service.py :: csv_export](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/report_export_service.py#L68) | 68 | KEEP | Inherits module rationale above. |
| [services/report_export_service.py :: excel_export](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/report_export_service.py#L77) | 77 | KEEP | Inherits module rationale above. |
| [services/report_service.py :: get_expense_export](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/report_service.py#L9) | 9 | ADAPT | Inherits module rationale above. |
| [services/report_service.py :: get_collection_export](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/report_service.py#L37) | 37 | ADAPT | Inherits module rationale above. |
| [services/report_service.py :: get_balance_export](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/report_service.py#L68) | 68 | REMOVE | No call sites found; legacy non-period balance export candidate to omit from new API, retain until parity audit. |
| [services/route_service.py :: get_all_routes](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/route_service.py#L5) | 5 | ADAPT | Inherits module rationale above. |
| [services/route_service.py :: get_active_routes](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/route_service.py#L17) | 17 | ADAPT | Inherits module rationale above. |
| [services/route_service.py :: add_route](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/route_service.py#L30) | 30 | ADAPT | Inherits module rationale above. |
| [services/smart_cashing_service.py :: _coerce_date](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/smart_cashing_service.py#L22) | 22 | ADAPT | Inherits module rationale above. |
| [services/smart_cashing_service.py :: _money](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/smart_cashing_service.py#L30) | 30 | ADAPT | Inherits module rationale above. |
| [services/smart_cashing_service.py :: get_collection_coverage](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/smart_cashing_service.py#L42) | 42 | ADAPT | Inherits module rationale above. |
| [services/smart_cashing_service.py :: _load_bus_rows](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/smart_cashing_service.py#L62) | 62 | ADAPT | Inherits module rationale above. |
| [services/smart_cashing_service.py :: get_smart_cashing_preview](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/smart_cashing_service.py#L96) | 96 | ADAPT | Inherits module rationale above. |
| [services/smart_cashing_service.py :: build_standard_allocations](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/smart_cashing_service.py#L128) | 128 | ADAPT | Inherits module rationale above. |
| [services/smart_cashing_service.py :: _clean_smart_entry](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/smart_cashing_service.py#L187) | 187 | ADAPT | Inherits module rationale above. |
| [services/smart_cashing_service.py :: _entry_expected](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/smart_cashing_service.py#L221) | 221 | ADAPT | Inherits module rationale above. |
| [services/smart_cashing_service.py :: _assert_airtel_account](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/smart_cashing_service.py#L228) | 228 | ADAPT | Inherits module rationale above. |
| [services/smart_cashing_service.py :: _find_existing_entries](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/smart_cashing_service.py#L243) | 243 | ADAPT | Inherits module rationale above. |
| [services/smart_cashing_service.py :: _assert_collection_can_be_corrected](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/smart_cashing_service.py#L271) | 271 | ADAPT | Inherits module rationale above. |
| [services/smart_cashing_service.py :: _insert_smart_rows](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/smart_cashing_service.py#L290) | 290 | ADAPT | Inherits module rationale above. |
| [services/smart_cashing_service.py :: record_smart_cashing_collection](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/smart_cashing_service.py#L378) | 378 | ADAPT | Inherits module rationale above. |
| [services/smart_cashing_service.py :: update_smart_cashing_collection](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/smart_cashing_service.py#L485) | 485 | ADAPT | Inherits module rationale above. |
| [services/smart_cashing_service.py :: record_obligation_payment](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/smart_cashing_service.py#L638) | 638 | ADAPT | Inherits module rationale above. |
| [services/smart_cashing_service.py :: list_open_cashing_obligations](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/smart_cashing_service.py#L746) | 746 | ADAPT | Inherits module rationale above. |
| [services/smart_cashing_service.py :: get_cashing_obligations_for_collection](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/smart_cashing_service.py#L787) | 787 | ADAPT | Inherits module rationale above. |
| [services/smart_cashing_service.py :: list_cashing_obligation_payments](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/smart_cashing_service.py#L823) | 823 | ADAPT | Inherits module rationale above. |
| [services/validation_service.py :: get_data_validation_warnings](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/services/validation_service.py#L6) | 6 | ADAPT | Inherits module rationale above. |

### utils

| File / definition | Line | Class | Specific note |
|---|---:|---|---|
| [utils/cashing_form.py :: bus_option_label](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/cashing_form.py#L11) | 11 | KEEP | Pure label helper. |
| [utils/cashing_form.py :: _amount](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/cashing_form.py#L16) | 16 | ADAPT | Decimal quantization reusable; external finite/scale policy required. |
| [utils/cashing_form.py :: build_direct_cashing_entries](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/cashing_form.py#L28) | 28 | KEEP | Pure direct-entry construction; retain tests and server validation. |
| [utils/cashing_form.py :: clear_cashing_form_state](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/cashing_form.py#L65) | 65 | ADAPT | Widget-version reset does not reset a native Flet controller; replace lifecycle adapter. |
| [utils/dashboard_charts.py :: _to_float](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/dashboard_charts.py#L9) | 9 | REWRITE | Inherits module rationale above. |
| [utils/dashboard_charts.py :: build_bus_performance_chart_data](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/dashboard_charts.py#L17) | 17 | REWRITE | Inherits module rationale above. |
| [utils/dashboard_charts.py :: build_bus_performance_chart](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/dashboard_charts.py#L37) | 37 | REWRITE | Inherits module rationale above. |
| [utils/dashboard_charts.py :: build_business_performance_chart_data](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/dashboard_charts.py#L68) | 68 | REWRITE | Inherits module rationale above. |
| [utils/dashboard_charts.py :: build_financial_chart_data](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/dashboard_charts.py#L99) | 99 | REWRITE | Inherits module rationale above. |
| [utils/dashboard_charts.py :: build_financial_chart](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/dashboard_charts.py#L109) | 109 | REWRITE | Inherits module rationale above. |
| [utils/dashboard_charts.py :: build_business_performance_chart](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/dashboard_charts.py#L126) | 126 | REWRITE | Inherits module rationale above. |
| [utils/dates.py :: today_lusaka](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/dates.py#L8) | 8 | KEEP | Inherits module rationale above. |
| [utils/dates.py :: week_bounds](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/dates.py#L12) | 12 | KEEP | Inherits module rationale above. |
| [utils/dates.py :: month_bounds](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/dates.py#L18) | 18 | KEEP | Inherits module rationale above. |
| [utils/dates.py :: period_bounds](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/dates.py#L28) | 28 | KEEP | Inherits module rationale above. |
| [utils/dates.py :: subtract_months](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/dates.py#L34) | 34 | KEEP | Inherits module rationale above. |
| [utils/dates.py :: _is_leap_year](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/dates.py#L46) | 46 | KEEP | Inherits module rationale above. |
| [utils/formatting.py :: format_kwacha](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/formatting.py#L5) | 5 | KEEP | Inherits module rationale above. |
| [utils/formatting.py :: format_whole_kwacha](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/formatting.py#L10) | 10 | KEEP | Inherits module rationale above. |
| [utils/formatting.py :: format_date](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/formatting.py#L15) | 15 | KEEP | Inherits module rationale above. |
| [utils/formatting.py :: bus_status_label](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/formatting.py#L21) | 21 | KEEP | Inherits module rationale above. |
| [utils/help_content.py :: Guide](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/help_content.py#L6) | 6 | KEEP | Inherits module rationale above. |
| [utils/help_content.py :: filter_guides](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/help_content.py#L186) | 186 | KEEP | Inherits module rationale above. |
| [utils/reporting_periods.py :: reporting_period](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/reporting_periods.py#L6) | 6 | KEEP | Inherits module rationale above. |
| [utils/reporting_periods.py :: scheduled_chart_dates](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/reporting_periods.py#L21) | 21 | KEEP | Inherits module rationale above. |
| [utils/validation.py :: clean_required_text](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/validation.py#L4) | 4 | KEEP | Pure text validation. |
| [utils/validation.py :: clean_optional_text](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/validation.py#L11) | 11 | KEEP | Pure optional text cleanup. |
| [utils/validation.py :: parse_optional_positive_int](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/validation.py#L16) | 16 | KEEP | Pure integer validation. |
| [utils/validation.py :: parse_positive_amount](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/validation.py#L28) | 28 | ADAPT | Inherits module rationale above. |
| [utils/validation.py :: parse_non_negative_amount](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/utils/validation.py#L40) | 40 | ADAPT | Inherits module rationale above. |

### database

| File / definition | Line | Class | Specific note |
|---|---:|---|---|
| [database/connection.py :: get_connection](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/database/connection.py#L9) | 9 | ADAPT | Inherits module rationale above. |

### app_pages

| File / definition | Line | Class | Specific note |
|---|---:|---|---|
| [app_pages/accounts.py :: _load_bus_accounts](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/accounts.py#L12) | 12 | REWRITE | Inherits module rationale above. |
| [app_pages/accounts.py :: _load_bus_detail](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/accounts.py#L17) | 17 | REWRITE | Inherits module rationale above. |
| [app_pages/accounts.py :: _selected_period_bounds](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/accounts.py#L21) | 21 | REWRITE | Inherits module rationale above. |
| [app_pages/backups.py :: _format_size](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/backups.py#L6) | 6 | REWRITE | Inherits module rationale above. |
| [app_pages/buses.py :: _load_buses](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/buses.py#L14) | 14 | REWRITE | Inherits module rationale above. |
| [app_pages/buses.py :: _load_routes](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/buses.py#L19) | 19 | REWRITE | Inherits module rationale above. |
| [app_pages/buses.py :: _load_drivers](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/buses.py#L24) | 24 | REWRITE | Inherits module rationale above. |
| [app_pages/buses.py :: _route_options](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/buses.py#L28) | 28 | REWRITE | Inherits module rationale above. |
| [app_pages/buses.py :: _render_edit_bus](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/buses.py#L32) | 32 | REWRITE | Inherits module rationale above. |
| [app_pages/buses.py :: _render_status_change](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/buses.py#L105) | 105 | REWRITE | Inherits module rationale above. |
| [app_pages/buses.py :: _render_edit_driver](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/buses.py#L130) | 130 | REWRITE | Inherits module rationale above. |
| [app_pages/business_presets.py :: _show_save_result](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/business_presets.py#L44) | 44 | REWRITE | Inherits module rationale above. |
| [app_pages/driver_money.py :: _profile_label](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/driver_money.py#L19) | 19 | REWRITE | Inherits module rationale above. |
| [app_pages/finance.py :: _load_finance_general](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/finance.py#L19) | 19 | REWRITE | Inherits module rationale above. |
| [app_pages/finance.py :: _load_collections](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/finance.py#L28) | 28 | REWRITE | Inherits module rationale above. |
| [app_pages/finance.py :: _load_expenses](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/finance.py#L33) | 33 | REWRITE | Inherits module rationale above. |
| [app_pages/finance.py :: _load_balances](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/finance.py#L38) | 38 | REWRITE | Inherits module rationale above. |
| [app_pages/home.py :: _load_home_data](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/home.py#L21) | 21 | REWRITE | Inherits module rationale above. |
| [app_pages/home.py :: _load_activity_bounds](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/home.py#L32) | 32 | REWRITE | Inherits module rationale above. |
| [app_pages/home.py :: _selected_period_bounds](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/home.py#L36) | 36 | REWRITE | Inherits module rationale above. |
| [app_pages/home.py :: _load_performance_series](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/home.py#L75) | 75 | REWRITE | Inherits module rationale above. |
| [app_pages/record_cashing.py :: _classification_label](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/record_cashing.py#L29) | 29 | REWRITE | Inherits module rationale above. |
| [app_pages/record_cashing.py :: _mode_label](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/record_cashing.py#L33) | 33 | REWRITE | Inherits module rationale above. |
| [app_pages/record_cashing.py :: _collection_classification](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/record_cashing.py#L41) | 41 | REWRITE | Inherits module rationale above. |
| [app_pages/record_cashing.py :: _registration_options](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/record_cashing.py#L54) | 54 | REWRITE | Inherits module rationale above. |
| [app_pages/record_cashing.py :: _render_smart_collection_form](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/record_cashing.py#L60) | 60 | REWRITE | Inherits module rationale above. |
| [app_pages/record_cashing.py :: _render_edit_collection](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/record_cashing.py#L294) | 294 | REWRITE | Inherits module rationale above. |
| [app_pages/record_cashing.py :: _render_smart_collection_detail](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/record_cashing.py#L376) | 376 | REWRITE | Inherits module rationale above. |
| [app_pages/record_cashing.py :: _render_smart_correction_form](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/record_cashing.py#L448) | 448 | REWRITE | Inherits module rationale above. |
| [app_pages/record_cashing.py :: _render_obligation_payment_form](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/record_cashing.py#L615) | 615 | REWRITE | Inherits module rationale above. |
| [app_pages/record_cashing.py :: _render_open_obligations](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/record_cashing.py#L660) | 660 | REWRITE | Inherits module rationale above. |
| [app_pages/record_expense.py :: _category_group](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/record_expense.py#L17) | 17 | REWRITE | Inherits module rationale above. |
| [app_pages/record_expense.py :: _category_options](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/record_expense.py#L29) | 29 | REWRITE | Inherits module rationale above. |
| [app_pages/record_expense.py :: _render_expense_form](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/record_expense.py#L33) | 33 | REWRITE | Inherits module rationale above. |
| [app_pages/reports.py :: _load_report](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/app_pages/reports.py#L15) | 15 | REWRITE | Inherits module rationale above. |

### components

| File / definition | Line | Class | Specific note |
|---|---:|---|---|
| [components/cards.py :: empty_state](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/components/cards.py#L4) | 4 | REWRITE | Inherits module rationale above. |
| [components/cards.py :: status_badge](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/components/cards.py#L9) | 9 | REWRITE | Inherits module rationale above. |
| [components/forms.py :: show_success_once](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/components/forms.py#L4) | 4 | REMOVE | Inherits module rationale above. |
| [components/forms.py :: set_success](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/components/forms.py#L9) | 9 | REMOVE | Inherits module rationale above. |
| [components/layout.py :: NavItem](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/components/layout.py#L12) | 12 | REWRITE | Inherits module rationale above. |
| [components/layout.py :: inject_app_shell_styles](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/components/layout.py#L26) | 26 | REWRITE | Inherits module rationale above. |
| [components/layout.py :: render_app_header](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/components/layout.py#L119) | 119 | REWRITE | Inherits module rationale above. |
| [components/layout.py :: fixed_page_controls](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/components/layout.py#L129) | 129 | REWRITE | Inherits module rationale above. |
| [components/layout.py :: render_bottom_navigation](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/components/layout.py#L133) | 133 | REWRITE | Inherits module rationale above. |
| [components/layout.py :: quick_action](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/components/layout.py#L149) | 149 | REWRITE | Inherits module rationale above. |
| [components/reporting_period.py :: period_controls](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/components/reporting_period.py#L8) | 8 | REWRITE | Inherits module rationale above. |
| [components/servicing_form.py :: render_servicing_form](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/components/servicing_form.py#L10) | 10 | REWRITE | Inherits module rationale above. |

### tests

| File / definition | Line | Class | Specific note |
|---|---:|---|---|
| [tests/test_bus_account_service.py :: FakeCursor](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_bus_account_service.py#L9) | 9 | ADAPT | Inherits module rationale above. |
| [tests/test_bus_account_service.py :: FakeConnection](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_bus_account_service.py#L35) | 35 | ADAPT | Inherits module rationale above. |
| [tests/test_bus_account_service.py :: BusAccountServiceTests](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_bus_account_service.py#L49) | 49 | ADAPT | Inherits module rationale above. |
| [tests/test_bus_accounts_page.py :: BusAccountsPageTests](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_bus_accounts_page.py#L66) | 66 | REWRITE | Inherits module rationale above. |
| [tests/test_bus_service.py :: BusServiceTests](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_bus_service.py#L6) | 6 | ADAPT | Inherits module rationale above. |
| [tests/test_business_performance.py :: BusinessPerformanceTests](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_business_performance.py#L9) | 9 | ADAPT | Inherits module rationale above. |
| [tests/test_cashing_form.py :: CashingFormTests](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_cashing_form.py#L12) | 12 | ADAPT | Inherits module rationale above. |
| [tests/test_cashing_service.py :: CashingServiceTests](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_cashing_service.py#L15) | 15 | ADAPT | Inherits module rationale above. |
| [tests/test_connection.py :: DatabaseConnectionTests](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_connection.py#L6) | 6 | ADAPT | Inherits module rationale above. |
| [tests/test_dashboard_charts.py :: DashboardChartTests](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_dashboard_charts.py#L7) | 7 | ADAPT | Inherits module rationale above. |
| [tests/test_driver_money_service.py :: DriverMoneyServiceTests](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_driver_money_service.py#L8) | 8 | ADAPT | Inherits module rationale above. |
| [tests/test_expense_service.py :: FakeCursor](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_expense_service.py#L14) | 14 | ADAPT | Inherits module rationale above. |
| [tests/test_expense_service.py :: FakeConnection](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_expense_service.py#L34) | 34 | ADAPT | Inherits module rationale above. |
| [tests/test_expense_service.py :: ExpenseServiceValidationTests](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_expense_service.py#L48) | 48 | ADAPT | Inherits module rationale above. |
| [tests/test_finance_ledger_reuse.py :: FinanceLedgerReuseTest](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_finance_ledger_reuse.py#L12) | 12 | ADAPT | Inherits module rationale above. |
| [tests/test_financial_foundation.py :: FakeCursor](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_financial_foundation.py#L11) | 11 | ADAPT | Inherits module rationale above. |
| [tests/test_financial_foundation.py :: FakeConnection](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_financial_foundation.py#L37) | 37 | ADAPT | Inherits module rationale above. |
| [tests/test_financial_foundation.py :: FinancialFoundationTests](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_financial_foundation.py#L51) | 51 | ADAPT | Inherits module rationale above. |
| [tests/test_financial_timeline.py :: FinancialTimelineTest](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_financial_timeline.py#L8) | 8 | ADAPT | Inherits module rationale above. |
| [tests/test_fleet_history.py :: FleetHistoryTests](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_fleet_history.py#L7) | 7 | ADAPT | Inherits module rationale above. |
| [tests/test_help_guide.py :: HelpGuideTests](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_help_guide.py#L8) | 8 | ADAPT | Inherits module rationale above. |
| [tests/test_home_page.py :: HomePageTests](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_home_page.py#L26) | 26 | REWRITE | Inherits module rationale above. |
| [tests/test_money_management_pages.py :: MoneyManagementPageTests](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_money_management_pages.py#L130) | 130 | REWRITE | Inherits module rationale above. |
| [tests/test_record_cashing_page.py :: RecordCashingPageTests](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_record_cashing_page.py#L116) | 116 | REWRITE | Inherits module rationale above. |
| [tests/test_record_expense_page.py :: RecordExpensePageTests](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_record_expense_page.py#L53) | 53 | REWRITE | Inherits module rationale above. |
| [tests/test_report_exports.py :: ReportExportsTest](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_report_exports.py#L11) | 11 | ADAPT | Inherits module rationale above. |
| [tests/test_reporting_periods.py :: ReportingPeriodsTest](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_reporting_periods.py#L9) | 9 | ADAPT | Inherits module rationale above. |
| [tests/test_route_service.py :: RouteServiceTests](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_route_service.py#L6) | 6 | ADAPT | Inherits module rationale above. |
| [tests/test_servicing.py :: ServicingTest](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_servicing.py#L7) | 7 | ADAPT | Inherits module rationale above. |
| [tests/test_servicing_page.py :: ServicingPageTest](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_servicing_page.py#L11) | 11 | REWRITE | Inherits module rationale above. |
| [tests/test_smart_cashing_service.py :: SmartCashingServiceTests](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/tests/test_smart_cashing_service.py#L40) | 40 | ADAPT | Inherits module rationale above. |

### scripts

| File / definition | Line | Class | Specific note |
|---|---:|---|---|
| [scripts/profile_step5_queries.py :: CountingCursor](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/profile_step5_queries.py#L11) | 11 | ADAPT | Inherits module rationale above. |
| [scripts/profile_step5_queries.py :: CountingConnection](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/profile_step5_queries.py#L31) | 31 | ADAPT | Inherits module rationale above. |
| [scripts/profile_step5_queries.py :: main](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/profile_step5_queries.py#L47) | 47 | ADAPT | Inherits module rationale above. |
| [scripts/seed_demo_data.py :: _last_sunday](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/seed_demo_data.py#L16) | 16 | ADAPT | Inherits module rationale above. |
| [scripts/seed_demo_data.py :: _fetch_id](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/seed_demo_data.py#L20) | 20 | ADAPT | Inherits module rationale above. |
| [scripts/seed_demo_data.py :: _insert_financial_transaction](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/seed_demo_data.py#L28) | 28 | ADAPT | Inherits module rationale above. |
| [scripts/seed_demo_data.py :: _insert_cashing_collection](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/seed_demo_data.py#L65) | 65 | ADAPT | Inherits module rationale above. |
| [scripts/seed_demo_data.py :: _insert_expense](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/seed_demo_data.py#L153) | 153 | ADAPT | Inherits module rationale above. |
| [scripts/seed_demo_data.py :: seed_demo_database](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/seed_demo_data.py#L208) | 208 | ADAPT | Inherits module rationale above. |
| [scripts/seed_demo_data.py :: main](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/seed_demo_data.py#L501) | 501 | ADAPT | Inherits module rationale above. |
| [scripts/smoke_expense_finance.py :: _connection_kwargs](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/smoke_expense_finance.py#L17) | 17 | ADAPT | Inherits module rationale above. |
| [scripts/smoke_expense_finance.py :: _category_id](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/smoke_expense_finance.py#L27) | 27 | ADAPT | Inherits module rationale above. |
| [scripts/smoke_expense_finance.py :: main](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/smoke_expense_finance.py#L37) | 37 | ADAPT | Inherits module rationale above. |
| [scripts/smoke_help_ui.py :: main](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/smoke_help_ui.py#L6) | 6 | REWRITE | Inherits module rationale above. |
| [scripts/smoke_money_workflows.py :: _connection_kwargs](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/smoke_money_workflows.py#L17) | 17 | ADAPT | Inherits module rationale above. |
| [scripts/smoke_money_workflows.py :: main](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/smoke_money_workflows.py#L27) | 27 | ADAPT | Inherits module rationale above. |
| [scripts/smoke_service_reload.py :: main](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/smoke_service_reload.py#L10) | 10 | REMOVE | Inherits module rationale above. |
| [scripts/smoke_smart_cashing.py :: _connection_kwargs](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/smoke_smart_cashing.py#L17) | 17 | ADAPT | Inherits module rationale above. |
| [scripts/smoke_smart_cashing.py :: main](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/smoke_smart_cashing.py#L27) | 27 | ADAPT | Inherits module rationale above. |
| [scripts/smoke_step4.py :: main](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/smoke_step4.py#L18) | 18 | ADAPT | Inherits module rationale above. |
| [scripts/smoke_step4_pages.py :: main](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/smoke_step4_pages.py#L14) | 14 | REWRITE | Inherits module rationale above. |
| [scripts/smoke_step4_ui.py :: main](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/smoke_step4_ui.py#L8) | 8 | REWRITE | Inherits module rationale above. |
| [scripts/verify_migrations.py :: _connection_kwargs](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/verify_migrations.py#L13) | 13 | ADAPT | Inherits module rationale above. |
| [scripts/verify_migrations.py :: main](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/verify_migrations.py#L23) | 23 | ADAPT | Inherits module rationale above. |
| [scripts/verify_step4_backup.py :: main](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/verify_step4_backup.py#L17) | 17 | ADAPT | Inherits module rationale above. |
| [scripts/verify_step4_live.py :: main](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/verify_step4_live.py#L13) | 13 | ADAPT | Inherits module rationale above. |
| [scripts/verify_step5_calculations.py :: main](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/verify_step5_calculations.py#L17) | 17 | ADAPT | Inherits module rationale above. |
| [scripts/verify_step5_records.py :: main](https://github.com/Jooshua07/SmartFleet/blob/46c76438b53b12f7779b89d0e2e74f72c6eb0d4f/scripts/verify_step5_records.py#L13) | 13 | ADAPT | Inherits module rationale above. |

## SQL, configuration, documents and assets

| Files | Class | Rationale |
|---|---|---|
| migrations/001-031_*.sql, all 31 numbered scripts | KEEP | Preserve as historical schema evidence. Baseline installed definitions; do not rerun seeds/backfills over live data. |
| migrations/smartfleet_integrity_tests_corrected.sql | ADAPT | Preserve financial rejection cases; execute only on disposable PostgreSQL with current final function definitions. |
| requirements.txt | ADAPT | Preserve legacy lock snapshot; derive separate minimal backend/client dependency sets, do not force legacy transitive pins. |
| .streamlit/config.toml | REMOVE from new runtime | Retain for old UI/parity; native Flet and FastAPI need their own configuration. |
| .gitignore | ADAPT | Preserve secret/venv/backup exclusions, add reviewed new environment/build/secret paths during implementation. |
| docs/ARCHITECTURE.md, MODULE_REFERENCE.md, FEATURE_STATUS.md, PROJECT_STATE.md | ADAPT | Useful current/history references; reconcile contracts and mark legacy-vs-target status. |
| docs/TESTING.md, ADDING_NEW_FEATURES.md | ADAPT | Extend to HTTP authorization, PostgreSQL races/commit checks and native device tests. |
| docs/CONTROLLED_REFACTOR_STEP1_AUDIT.md, NEXT_PHASE_GUIDE_AND_CLEANUP.md, STEP4_*.md, STEP5_*.md | KEEP as history | Past decisions/results are not fresh verification of every feature. |
| docs/UI_UX_SPECIFICATION.md, ui-references/* | ADAPT | Reference intended layout; actual desired current behavior takes priority over old screenshots. |
| docs/SmartFleet_Database_Schema_V1_Technical_Reference.docx and .pdf | KEEP as history | Not authoritative for later migrations 023-031; compare to live catalog, do not regenerate schema from an older document. |
| docs/MVP.txt, RAW.txt | KEEP as history | Raw/early requirements need reconciliation, not automatic implementation. |
| docs/bus book records from july to august.csv and companion XLSX | ADAPT access policy | Business data, not app assets; review repository visibility and data minimization. |
| .env (local, untracked) | ADAPT deployment handling | Server-only secrets; values intentionally not included here or in mobile build. |

## Mixed UI/business logic to separate first

1. app_pages/record_cashing.py: collection classification, expected totals, per-bus allocation, variance/obligation calculations and correction arithmetic. Convert float money operations to shared Decimal domain helpers with fixtures before porting.
2. app_pages/record_expense.py: category-group mapping and scope/payment form preparation. Keep user presentation grouping separate from authoritative expense-service restrictions.
3. components/servicing_form.py: cost/component and payment-form orchestration. Domain validates amounts and coordinated expense creation; Flet only renders/collects input.
4. app_pages/home.py and components/reporting_period.py: date-filter selection state versus reusable pure reporting_periods calculations.
5. app_pages/finance.py and reports.py: measure labels/selected-period state versus ledger/performance/report contracts.
6. page cache decorators, st.cache_data.clear, reruns and session success keys: presentation lifecycle, not a backend cache or transaction model.

## REMOVE decisions and caution

Repository search found no consumers of components.forms.show_success_once/set_success or report_service.get_balance_export. These are removal *candidates for the migrated deployment*. Do not delete them or their tests from the existing app during this audit.

Legacy build_business_performance_chart/data helpers are referenced by test_business_performance.py. They are not proven dead merely because the current Home uses newer helpers; retain their regression meaning until equivalent Flet chart tests exist. Likewise, direct cashing edit support may be required for historical records and cannot be removed just because smart cashing is the default form.

## Test coverage implications

Existing unit/mocked/Streamlit tests provide useful regression evidence, not API/mobile/security certification. Preserve behavioral fixtures; rewrite only presentation coupling. Add real isolated PostgreSQL commit/rollback tests, multi-connection races, HTTP permission/idempotency cases, and native mobile interruption/form-reset/export tests. See Document 5 for per-module acceptance cases.

