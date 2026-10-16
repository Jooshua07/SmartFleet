# SmartFleet Flask Migration Audit and Implementation Plan

Date: 2026-10-16 (Africa/Lusaka)  
Status: planning for review only. No Flask implementation or deployment configuration has been created.

## 1. Scope, Checkpoint and Decision

Repository: Jooshua07/SmartFleet. Development branch: `migration/flask`, commit `b19ed63ee21a0bff8ef0f10936b041757987bef5`. Stable Streamlit baseline: `master`, commit `46c76438b53b12f7779b89d0e2e74f72c6eb0d4f`. Annotated historical tag: `streamlit-final`, pointing to that baseline.

Branch cleanup is complete. The redundant local branches `codex/audit-documentation`, `codex/controlled-step1-audit`, `codex/expense-finance-refinement` and `migration/fastapi-flet` were removed after ancestry/unique-commit checks. The three corresponding published branches were removed from GitHub; audit-documentation was local-only. Only master and migration/flask remain locally and remotely. All existing tags were retained. The controlled-step1 cashing correction functionality, payment history, locking safeguards and tests remain in the baseline history and current code.

**Recommendation: proceed with an additive, schema-preserving Flask foundation, initially read-only. Do not expose financial writes until the security, transaction, retry and reconciliation gates below pass.**

Flask with server-rendered Jinja templates is a good fit for this phone-first business application and its small VPS. Reuse the existing psycopg services and PostgreSQL protections. There is no need for a separate REST backend, native mobile build, ORM conversion or frontend framework to complete this migration.

### Evidence and verification boundaries

- Reviewed the six documents in [the historical audit directory](pre_migration_audit/2026-10-15/01_technical_audit_report.md), including the reusability matrix, database report, architecture, migration plan and environment guide. Their FastAPI/Flet proposals are historical alternatives, not the current implementation instructions.
- Verified the current source checkpoint and inspected the Streamlit navigation, service interfaces, SQL, financial workflows, forms, reports, tests and migration definitions. Inventory: 101 Python files including package markers; 23 substantive services; 17 registered screens; 31 numbered SQL migrations plus a standalone integrity-test SQL file.
- Fresh pre-interruption verification: 97 existing tests passed in 9.899 seconds. The live database connection test was intentionally excluded. Default read-only PostgreSQL options and disabled bytecode writes were used. This was not a fresh 98-test full-suite run.
- All 101 Python source files passed Python 3.12 grammar parsing. This does not establish Python 3.12 runtime or dependency compatibility; that needs a clean Ubuntu/Python 3.12 test environment.
- The previous audit's live counts and superuser finding concerned the then-configured database. They are not independent verification of the restored VPS database.
- VPS facts below are user-provided: Ubuntu 24.04, Python 3.12, PostgreSQL 18.6, database smartfleet already restored, 1 vCPU, 1 GB RAM, 25 GB storage. No SSH session, VPS configuration inspection, restore, database mutation, package installation or deployment was performed during this planning task.
- No application code was changed, no existing audit document was rewritten, and no commit or push was made. This plan is the only new repository document.

## 2. Findings Verified Against Code

### Critical before public financial entry

**Authentication and authorization are absent.** [app.py](../app.py) registers the screens without identity or role checks. Services receive IDs and financial input without an authenticated actor. Login, authorization and request protection must be implemented before remote use, not added after the write forms.

**VPS runtime privileges are unverified.** The earlier configured connection used a superuser, but the restored server may differ. Verify the VPS role with read-only inspection later. Production must use a restricted application role, not a superuser/schema-owner account. Verify sequence/function/table grants as well as login permissions. Role/network administration is separate from changing the business schema and still requires an authorized deployment step.

**Current services do not provide durable HTTP command deduplication.** `smart_cashing_service._find_existing_entries` checks before insertion; the remittance unique key is collection/bus, not bus/date across different collection headers. A disabled Submit button and redirect-after-POST do not protect a request retried after a committed response was lost. Other financial forms can also repeat otherwise valid payments.

### High integrity and parity risks

**Bus Accounts summary and detail disagree on cost definitions.** `bus_account_service.get_bus_contribution_summary:10` uses OPERATING_EXPENSE_PREDICATE and attributable salary. `get_bus_account_detail:170` builds expense-only trend/category/recent results without equivalent exclusions or salary attribution. Preserve the screen, but resolve the definition mismatch with approved fixtures before declaring Flask report parity. No live corruption is inferred from this source finding.

**Corrections are not a complete immutable audit trail.** Migration 030's correction_audit has JSONB snapshots but no actor column. Ordinary expense and cashing edit/delete paths do not consistently use it. Some payroll/loan/owner cancellations physically delete records after a snapshot. Do not silently replace these workflows or claim they are immutable reversals. Require authorization, reasons, actor attribution and atomic before/after evidence while retaining the current financial effect unless a different policy is approved.

**Transactions must cover commit-time errors.** Existing services generally own a psycopg connection context. Deferred database checks can fail when that context commits, not just at cursor.execute. An outer route transaction does not make multiple independently committing services atomic. Adapt connection ownership narrowly, preserve SQL/locks, and commit exactly once per command before showing success.

**Reports read through multiple independent connections.** `business_report_service.get_business_report:27` calls services and helper queries with separate snapshots. Under concurrent entry, report sections may observe different states. Use a shared read-only repeatable-read snapshot for a report rather than a process-wide cache or a long-lived connection.

**A restored database is not proof of identical security and integrity objects.** Compare VPS schema definitions, enabled triggers, generated columns, indexes, sequences and privileges against the baseline before permitting writes. Never rerun migrations 001-031 or their seed/backfill statements against smartfleet merely because a new web framework is being introduced.

### Corrections to assumptions in the six earlier documents

| Earlier implication | Current source verification | Migration consequence |
|---|---|---|
| Expense entry supports shared/multi-bus allocation | `expense_service.record_business_expense:164` accepts GENERAL or BUS only; record_expense.py offers those two scopes. Schema/reporting can represent MULTI_BUS historical data. | Preserve all historical display/exports, but do not claim a shared-allocation entry form is already completed. Adding one is separate approved scope. |
| Expense entry offers owner-personal funding | Ordinary expense entry creates BUSINESS_ACCOUNT payments; owner-personal cases exist elsewhere in finance/loan logic and schema. | Preserve actual supported workflows without inventing an owner-personal expense selector. |
| Servicing entry can use owner-personal funds | `maintenance_service.record_servicing:92` selects the default business account when cost is positive. | Port its current payment workflow. Additional payment sources need approval and tests. |
| Cashing dropdown currently includes driver names | `_registration_options` in record_cashing.py uses registration only. utils.cashing_form has a driver-label helper, but that is not proof the current smart form uses it. | Preserve current capability; registration plus driver is a proposed usability improvement, not an already-delivered feature. |
| All preset schedule changes affect smart cashing | `get_collection_coverage:42` hardcodes Thursday/Sunday windows; no read of cashing_schedule_rules occurs in that service. | Schedule preset editing and actual coverage are not fully connected. Decide intended behavior before changing calculations. |
| Cashing destination is freely configurable | Smart collection and obligation payments explicitly require an active AIRTEL_MONEY account. | Do not broaden accepted destinations during the port. |
| All one/three-month selectors mean calendar periods | Finance/Reports use reporting_periods; Bus Accounts uses rolling subtract_months. Home has both an outer rolling selector and separate chart controls. | Document and test each current scope. Unification is a business/UX decision, not an incidental refactor. |
| Home's outer selector filters its cards/chart | `_load_home_data` ignores start/end and loads baseline totals; the chart has its own selector. | Keep the agreed broad cards. Propose removing or repurposing the ineffective outer selector only after review. |
| Starting account balances feed the consolidated reporting baseline | `get_period_balance:49` explicitly starts the reporting baseline at zero; account balances have their own opening values. | Preserve the October clean-slate policy; do not silently add account openings to consolidated reports. |
| Nullable loan schema means the Add Loan form accepts unknown principal | `add_business_loan:213` requires a positive original principal. Unidentified repayment is a separate supported workflow. | Do not invent loan principal or deposit income. Preserve unidentified repayments. |
| Creating a loan records cash received | add_business_loan inserts the loan record only. | Never fabricate a matching ledger IN entry during migration. A loan-disbursement workflow would be separate scope. |
| Backup settings already honor systemd-only environment variables | backup_service._load_database_settings reads dotenv_values from the project .env, unlike the ordinary connection's environment lookup. | Adapt backup configuration for protected VPS environment settings; no credentials in release directories. |
| Negative-account warnings are implemented | `account_service.get_negative_balance_warnings:78` returns an empty list. | Label as incomplete; do not report a false completed validation feature. |
| Document uploads and transfers are completed user workflows | Document metadata/expiry and transfer schema exist, but complete binary upload and transfer-entry workflows were not found. | Preserve existing metadata/financial history. Treat new upload/transfer UI as optional separately approved expansion. |

These findings refine the old audit; they do not authorize changing business behavior now. The earlier plan also names some generalized helper operations rather than actual functions: the current fleet update function is `bus_service.update_bus`, not update_bus_details.

## 3. Architecture Assessment

### Recommended request path

```text
Phone/desktop browser
    HTTPS
Nginx: TLS, static files, request limits, proxy headers
    local Unix socket or 127.0.0.1
Gunicorn: small, supervised WSGI service
    Flask application factory and Blueprints
    Jinja HTML + small progressive-enhancement JavaScript
    existing business services and Decimal/date helpers
    psycopg connection / command transaction
Private PostgreSQL 18.6: existing smartfleet schema and rules
```

Use ordinary HTML routes first, not REST endpoints for every table. GET requests render pages, filters and details. POST requests validate, authorize and execute commands; successful POSTs redirect to a fresh GET. Preview POSTs may calculate without writing. Only add small JSON endpoints for interactions that genuinely benefit, such as an optional cashing preview.

The Flask application factory supports test-specific settings and Blueprint registration without importing the Streamlit entry point. [Flask application factories](https://flask.palletsprojects.com/en/stable/patterns/appfactories/)

### Dependencies and resource discipline

- Production direct dependencies: Flask, psycopg with an installation suitable for Ubuntu/Python 3.12, Gunicorn, Flask-WTF for CSRF, openpyxl when reports migrate, and python-dotenv only for local configuration if useful. Jinja2/Werkzeug are provided by Flask; declare them directly only when application imports warrant it.
- Use the standard library for Decimal, dates, CSV, JSON, paths, logging and process control. Keep timezone data available for Africa/Lusaka.
- Development/CI: pytest; browser testing with Playwright and its browsers on developer/CI machines, not the 1 GB production VPS. Existing unittest tests can run under pytest without wholesale rewrites.
- Do not install the entire Streamlit requirements snapshot in the Flask production environment. Streamlit, Altair, pyarrow, pydeck and their large dependency chain are not needed to render Jinja pages. Current report_export_service already uses stdlib/openpyxl; pandas is mainly presentation here and is not required by the Flask domain layer.
- No SQLAlchemy, Alembic, Redis, Celery, Node build pipeline, Docker stack, JWT library or second API service unless a demonstrated requirement justifies it. No Flask-Login is required for a small environment-configured owner login; reconsider a user-management library if persistent multi-user management is later approved.
- Start by measuring one Gunicorn gthread worker with two threads, rather than copying a multi-process rule of thumb. This is a proposed starting configuration, not a measured capacity guarantee. Keep DB connections per operation and never share one cursor/connection across request threads. Avoid a pool initially; introduce a small bounded one only if measurement warrants it.
- Serve static files through Nginx, lazy-load chart assets and expensive reports, paginate growing lists, bound date/query/export sizes, serialize backup/report-heavy work when necessary, and avoid preloading every module or whole datasets at process startup.
- Production and development cannot each consume an assumed full server budget. Measure combined Python/PostgreSQL/Nginx/OS memory, CPU, disk and PostgreSQL connection peaks. Temporarily stop development on this host if it threatens production; do not solve this by weakening data isolation.

[Gunicorn's design guidance](https://docs.gunicorn.org/en/stable/design.html?highlight=workers) describes thread-based workers as a way to share process memory. Exact worker count, timeouts, request recycling and memory thresholds must be chosen after measurement.

### Connection and command boundary

Keep existing service modules and parameterized PostgreSQL queries. Add an optional supplied connection/transaction path only to services that need orchestration; retain compatibility for the working Streamlit tests. A supplied connection must not be closed or independently committed by a subordinate service.

Use explicit command transaction scope; do not blindly commit all requests in teardown. Read operations close promptly, and reports use a shared snapshot. Routes catch errors around the entire service/commit boundary, return safe validation/conflict messages and never expose raw SQL or secrets.

Convert form strings directly to finite Decimal values, enforce relevant NUMERIC scale/range, and recompute totals, eligibility and derived fields server-side. Client-side totals are previews only. Existing quantization/rounding behavior must be captured in tests before tightening input contracts. Charts may use presentation-only numeric conversion; accounting must not.

### Security without silently adding schema

The first protected pilot can use an environment-configured owner identity and a Werkzeug password hash, with Flask's signed session cookie. This requires no new business table. Require HTTPS, secure/HttpOnly/SameSite cookie settings, session expiry, logout, login throttling, trusted hosts, server-side permissions and CSRF on every state-changing form. The signed cookie is not encrypted: keep only minimal identity/session metadata there, never DB credentials, financial drafts or balances.

Use Flask-WTF's CSRFProtect for ordinary forms and any mutation via JavaScript. CSRF and idempotency solve different problems. [Flask-WTF CSRF protection](https://flask-wtf.readthedocs.io/en/1.2.x/csrf/)

Suggested future roles: owner/admin, recorder, viewer. Owner-only actions include configuration/opening balances, corrections/deletions, payroll/debt/owner money unless explicitly delegated, and backup downloads. Permissions are checked on each route, not merely hidden in the navigation. A managed user/role table, durable server-side sessions or a dedicated command table would require an explicit schema proposal and approval; they are not assumed available.

ProxyFix must trust only the actual Nginx proxy chain and headers it sets; do not trust arbitrary forwarded headers or expose Gunicorn directly. [Flask reverse-proxy guidance](https://flask.palletsprojects.com/en/stable/deploying/proxy_fix/)

### Durable retry safety under the no-schema-change rule

Before financial writes, approve and test a durable command mechanism. A schema-preserving candidate is to store actor, command UUID, canonical payload hash, target/result and before/after evidence in the existing correction_audit JSONB snapshot, written in the same transaction as the financial change. Its current action/reason fields can describe the operation without altering columns.

Serialize a command key using a transaction-scoped PostgreSQL advisory lock, check for an existing recorded result, perform the command, then persist the result and commit. The same command/payload returns the original result; different payload with the same key conflicts. Use separately ordered business-key/row locks where necessary to prevent two distinct commands violating the same business rule. Preserve existing employment, loan and obligation locks.

This is a proposal, not an existing guarantee: it requires service connection adaptation, a stable JSON envelope, crash/race tests and review of audit retention/access. JSON lookups without a dedicated index may not scale indefinitely. If this approach is not approved, remain read-only until an alternative durable design is approved; do not substitute process memory, a session cookie, a disabled button or a second SQLite financial database. Adding a dedicated command table/index remains an explicit future schema decision.

No legacy writer may bypass the agreed locking/deduplication protocol during Flask write rollout. Use isolated test data during development and one authorized production writer at cutover.

## 4. Proposed Flask Project Structure

All paths below are proposals; none were created as application code by this audit. Retain the existing Streamlit files on migration/flask during development and keep master/tag frozen.

```text
smartfleet_web/
  __init__.py                 create_app; settings, extensions, Blueprints
  config.py                   validated environment-specific configuration
  extensions.py               CSRF and other actually needed extensions
  auth.py                     identity/session helpers and permission decorators
  errors.py                   safe HTML errors and transaction error mapping
  commands.py                 command metadata, retry/audit coordination
  blueprints/
    auth.py                   login/logout
    home.py                   Home and More
    fleet.py                  buses, routes, drivers, metadata/history
    cashing.py                 preview, collection/detail/correction/settlement
    expenses.py                record/edit/delete and history
    finance.py                 general/collections/expenses/balances, accounts
    driver_money.py            salaries/advances and corrections
    loans.py                   lender and owner money workflows
    maintenance.py             servicing/schedules/reminders
    reports.py                 report pages and CSV/XLSX downloads
    management.py              presets, backup controls, help
  forms/                      request parsing and form-state validation by area
  templates/
    base.html                 header/main/footer and nav
    macros/                   form fields, money, period controls, tables
    auth/ home/ fleet/ cashing/ expenses/ finance/
    driver_money/ loans/ maintenance/ reports/ management/
  static/
    css/app.css               responsive shell, compact phone-first controls
    js/forms.js               progressive enhancement, not financial authority
    js/charts.js              chart configuration and accessible fallback
    vendor/                   pinned chart/icon assets, licenses retained
database/
  connection.py               adapted existing configuration/connection seam
  transactions.py             only if needed for explicit shared transaction scope
services/                    existing business services, narrowly adapted
utils/                       reusable Decimal/date/formatting/help utilities
tests/
  conftest.py                  safe test settings and app/database fixtures
  web/                        Flask route/form/permission tests
  integration/                isolated PostgreSQL commit/retry/race tests
  browser/                    phone-width workflows and screenshots
  test_*.py                   existing regression suite retained
wsgi.py                      Flask-only WSGI entry, separate from Streamlit app.py
requirements-flask.txt        minimal compatible runtime dependencies
requirements-test.txt        test-only dependencies
deploy/                      future Nginx/systemd/Gunicorn templates and runbook
.github/workflows/           future CI/deployment workflows, not configured now
```

Do not split every existing SQL function into a new repository class. Keep familiar service ownership. Build one reusable template/form pattern once there is an actual second use. Public route URLs should be business-oriented, not raw table CRUD. Distinguish `/bus-accounts` (bus profitability) from `/financial-accounts` (Cash/Airtel/Bank).

## 5. Feature Migration Matrix and Invariants

Blueprint names refer to the proposed structure. Supporting capabilities not currently exposed are identified separately rather than silently added or dropped.

| Existing feature | Reuse and verified business rules | Flask views/routes and parity requirement |
|---|---|---|
| Home | dashboard_service, performance_service, finance_service, warning/reminder queries. Baseline overview totals are not the same as period operating performance. | `GET /`; preserve broad cards, fleet status, recent activity, warnings and performance chart; resolve redundant selector explicitly. |
| Buses/search/filter/detail | bus_service.get_buses_overview/get_bus_details; routes, acquisition/model/seats/chassis/notes and servicing/document indicators. | `/buses`, `/buses/<id>`; preserve search by registration/driver/route and active/deactivated filters. |
| Add/edit bus | create_bus/update_bus; route validation, document metadata and optional initial assignment; unique registration and validated capacity. | `/buses/new`, `/buses/<id>/edit`; POST commands with all existing field restrictions. |
| Bus status/route history | set_bus_status and history helpers; effective dates, current-row closure and active-day calculation. | Authorized status command and history detail. Do not replace old dates with current state. Test interval overlap/backfill behavior. |
| Routes | route_service list/add, unique names and active-route selection. | Buses Routes tab and add form. Do not reintroduce obsolete demo routes. |
| Drivers/employment | driver_service create/update/overview; valid employment start/salary and linked permanent assignment. | Buses Drivers tab, add/edit. Full reassignment/end-employment UI is not assumed completed. |
| Smart cashing | smart_cashing_service coverage, rates, standard/adjusted allocations and classifications. Thursday covers Mon-Wed with optional prior Sunday; Sunday covers Thu-Sat. | `/cashing/new`, preview, details; one selected-bus workflow, not simultaneous independent per-bus forms. Keep Standard and Adjust Buses modes. |
| Cashing backfill | Existing backfill date selector; historical eligible days/rates and Thursday/Sunday restrictions. | Explicit date/coverage display and validation; do not turn backfill into arbitrary-day smart cashing without approval. |
| Receipt reconciliation | Header received total equals child allocations plus signed unallocated amount; standard estimated allocations may legitimately exceed actual receipt when signed difference is negative. | Preserve provenance, surplus/unknown/underperformance/reduced-workdays classifications; never force an unapproved proportional split. |
| Direct historical cashing | cashing_service direct edit/delete and details support older records. | Keep historical direct-record management even though the default new form is smart cashing. |
| Smart corrections/deletion | update_smart_cashing_collection and collection deletion safeguards; obligations/payments lock changes. | Details/correct/delete confirmation POSTs with reasons and audit; validate restrictions server-side, including forged requests. |
| Obligations and repayment history | record_obligation_payment locks outstanding amount, caps payment and requires Airtel. Settlement is OTHER/IN, not another CASHING collection. | Obligation list/detail/payment/history. Reduce debt and increase cash once without rewriting the original collection. |
| Record/edit/delete expense | expense_service, restricted category handling; GENERAL/BUS only for ordinary entry; title <=35 characters and <=5 words; paid-to/reference/notes; business-account ledger link. | `/expenses/new`, detail/edit/delete confirmation. Preserve specialized-payment exclusions and linked-servicing restrictions. |
| Shared/owner-personal historical expenses | Schema and reporting recognize these; ordinary entry service does not accept MULTI_BUS. | Preserve history/report readability and attribution; new shared/funding forms are separately approved scope. |
| Finance General | operating summary plus separate other-payment breakdown and period activity. | `/finance?tab=general`; principal/drawings/advances do not become operating costs. |
| Finance Collections/Expenses | finance_service period queries, total receipts and expense classifications. | Explicit period tabs/lists, pagination without changing totals. |
| Finance Balances | get_period_balance and summarize_ledger; clean-slate baseline zero; ignore internal transfers in consolidated cashflow. | Business Balance Now above/outside selector; filtered Money Received/Money Paid Out below. Opening/closing remain in Reports. |
| Financial account starting balances | account_service/finance_service account balances; Cash/Airtel/Bank records where configured. | `/financial-accounts`; owner-only opening edits, visibly distinct from baseline-derived business balance; preserve backend capability even though current management UI is limited. |
| Bus Accounts | bus_account_service summary/detail, confirmed vs estimated revenue, direct/allocated salary costs, general costs separate. | `/bus-accounts` and selected bus detail/trend/category/activity; fix approved summary/detail definition mismatch before acceptance. |
| Driver advances | driver_money_service; employment/date checks, outstanding cap from preset, OUT ledger, FIFO recovery. | `/driver-money`, advance form/history and reasoned cancellation; no double-counted salary expense. |
| Salaries | employment-month proration, salary presets, recovery/deduction allocations and unique monthly salary. PAID zero-net is valid without a zero ledger row. | Preview/review/payment/detail/correction; distinguish earned salary cost from cash payment and advance recovery. |
| Business loans | loan_service records loans, principal/repayment limits, nullable terms and optional monthly amount. Creating a loan does not create cash receipt. | `/loans`; list/add/repayment/history; unidentified payments retain notes and unknown facts. |
| Business/owner-paid lender repayments | Business principal is financing OUT; owner-personal settlement creates owner liability, no fictitious business cash outflow. Interest/fees are handled separately. | Payment source, principal/fees, paid-to/reference; retain cancellation path and principal cap. |
| Owner money | owner-funded business receipt, drawings, personal lender payment, repayment to owner; locked nonnegative liability. | `/owner-money`; preserve four distinct actions and linked-loan correction restrictions. |
| Historical reclassification | driver_money/loan services can reclassify compatible legacy expense/payment records. | Preserve callable rules/tests; add a protected review UI only if intended as migration scope, not automatic data rewriting. |
| Servicing and corrections | maintenance_service; labour/transport/other (stored parts), default business account, actual service/payment dates, generated total, one bus/date and expense association. | `/servicing/new`, history/correction and bus shortcut; positive cost creates one linked expense/payment; zero cost has no cash payment. |
| Maintenance schedule | 35-day default; refresh from actual latest completion while retaining configured interval; explicit schedule correction audits. | Schedule detail/correction; due dates must not drift when editing an earlier event. |
| Reminders | reminder_service due maintenance, inactive buses, document expiry, pending reminders; servicing warning thresholds 14/7/overdue. | `/reminders` and Home/Buses alerts; preserve current date/threshold behavior. Push/email alerts are not existing scope. |
| Business presets | preset_service rates, schedule rules, salary defaults/overrides, reminder thresholds, reporting baseline, advance cap and preset audit. | `/settings` sections; owner-only effective-dated changes. Do not claim saved schedule rules alter hardcoded coverage until resolved. |
| Reports/reconciliation | business_report_service/report_service; operating/cashflow/loan/owner/payroll/servicing/active-day data, historical snapshots and warnings. | `/reports` and reconciliation detail; consistent snapshot, explicit unknowns, opening/closing and recorded-vs-expected distinction. |
| CSV/XLSX exports | report_export_service table builders, formula sanitization, Decimal/date cells and empty-sheet handling. | Authorized download routes returning existing report sections with bounded memory. Export is not a DB backup. |
| Backups | backup_service custom dump/list/archive validation and age warnings. Existing archive verification lists contents, not an actual restore. | `/backups`; owner-only create/list/download; Linux paths/environment adaptation, streaming file delivery and serialized jobs; restoration drill elsewhere. |
| Help/More/setup checks | utils.help_content/filter_guides and validation_service. | `/more`, `/help`; retain quick actions, searchable guide and setup checks with accurate completed/incomplete labels. |
| Document metadata | bus_documents type/number/expiry and fleet links. | Preserve metadata entry/display/expiry; private binary upload remains separate scope. |
| Transfers | Existing tables/checks/ledger meaning; no complete dedicated entry service/page found. | Retain correct balance/report treatment of existing rows; a new transfer workflow needs approval. |

### Financial protections that must never be removed

1. All existing PKs, FKs, CHECKs, unique/partial indexes, generated columns, trigger functions and deferred constraints remain in PostgreSQL. Python checks supplement them, not replace them.
2. No endpoint or browser field independently edits ledger links, generated totals, actor identity, salary recoveries or outstanding debt without service verification.
3. Collection receipts, allocations, signed differences, obligation settlements and provenance remain distinct facts.
4. Operating performance, business cashflow, account balances and debt balances are different measures; financing is not revenue and principal is not an operating expense.
5. Salary recovery is not a second cash payment. Owner-personal settlement is not imaginary business account movement.
6. Use Decimal and the agreed rounding policy. Keep unknown principal/expectation/history separate from zero.
7. Preserve transaction locks, FK deletion order and commit-time rollback behavior. Do not disable triggers during normal entry or migration verification.
8. Backfilled records retain their actual dates, rates, eligibility and period meanings. Never seed fake data into the real database.
9. Opening balances and the reporting clean-slate date are not silently reinterpreted.
10. Failed writes leave no partial ledger/source/allocation/audit result and no false success message.

### PostgreSQL dependencies to verify on the VPS

Source migrations cover 39 tables across fleet/history, drivers/employments/assignments, accounts/ledger/transfers, expenses/allocations, collections/rates/schedules/obligations, salaries/advances/deductions/recoveries, business/owner loans, maintenance, presets/reminders and correction audit.

The earlier local live audit recorded 39 PKs, 51 FKs, 100 CHECKs, 11 UNIQUE constraints plus additional unique indexes, 51 enabled non-internal triggers, 19 deferred integrity triggers, and 20 sf_* functions. Recheck these counts and definitions on the VPS instead of assuming restoration included everything. Matching counts alone are insufficient.

Functions to preserve: sf_assert_advance, sf_assert_business_loan, sf_assert_collection, sf_assert_deduction, sf_assert_employment, sf_assert_expense, sf_assert_fee_rule, sf_assert_ledger, sf_assert_loan_repayment, sf_assert_maintenance, sf_assert_owner_balance, sf_assert_owner_loan_transaction, sf_assert_rate, sf_assert_salary, sf_assert_transfer, sf_integrity_deferred, sf_is_external_transfer, sf_preserve_account_type, sf_suggest_transfer_fee, sf_touch_updated_at.

Later function definitions in migrations 025/027 supersede earlier 022 definitions. Migration 026 has one-current-row uniqueness, not general closed-interval exclusion. Migration 030 has audit snapshots without a mandatory actor field. Migration 031 generates maintenance total from parts/labour/transport and adds servicing-specific fields/indexing. Preserve all of that without introducing an ORM or replaying historical seed data.

## 6. User Experience and Flask Differences

### App shell

Preserve primary navigation: **Home, Buses, Finance, More**. SmartFleet branding and bottom navigation remain fixed/sticky; main content scrolls between them. Reserve layout space for both so cards, buttons and focused fields are never hidden. Test phone safe areas, the on-screen keyboard and browser chrome. Avoid double page/panel scrolling and a decorative desktop dashboard redesign.

- Home: fixed SmartFleet header only; period controls stay in the body, not a large fixed reporting banner.
- Buses: fixed SmartFleet header and Buses/Routes/Drivers tab controls.
- Finance: fixed SmartFleet header and General/Collections/Expenses/Balances tabs.
- More: fixed SmartFleet header, body quick actions/management links.
- Forms/detail screens retain a clear return path and the appropriate primary navigation selection. Deep links work without pre-existing widget session state.

### Forms and browser behavior

Streamlit reruns become normal GET/POST routes. Filters and tabs use GET parameters/URLs so browser Back and bookmarking work. Editing uses explicit record IDs in authorized routes, not global widget keys. Flash feedback is short and follows confirmed commit; sensitive drafts do not live in Flask's signed cookie.

Validation errors re-render the same form with entered values and field messages. Successful recording redirects to a fresh entry form/result, with a new command identity for a genuinely new record. A network timeout retains the original command identity until the outcome is known. Refresh, Back, double tap and two open tabs must not silently repeat financial entries.

Use progressive enhancement for multi-bus inputs and previews. JavaScript may reveal amount rows/toggles, but submitted IDs, amounts, classifications, eligibility and derived values are revalidated in Python. Forms must remain usable if a preview request fails; offline writes are not promised.

### Charts and date controls

Use one locally served pinned chart library, such as Chart.js, only on screens that need it, with an accessible data-table fallback. No full frontend framework or server-side image rendering is required.

Bus comparison bars are grouped, not stacked/floating, and each starts at zero; amounts remain actual ZMW values (4000 means 4,000, not 400,000). The business timeline preserves its cumulative Thursday/Sunday points and final-period endpoint; a negative balance remains visible below zero. Avoid clipping negative balance because the revenue/cost series are nonnegative. [Chart.js bar chart reference](https://www.chartjs.org/docs/latest/charts/bar.html?h=size)

The six-month Streamlit timeline test currently enforces wide point spacing. Preserve data points and readability rather than blindly reproducing a 4,000-pixel canvas. A horizontally scrollable plot is acceptable where needed, but the full page/nav must not overflow. Period definitions and Home's duplicate filters require the explicit decisions listed below.

## 7. Testing Strategy

Use pytest for new tests and to run compatible existing unittest cases. Flask provides an app/test-client fixture pattern; use that rather than starting a live server for every route test. [Flask testing documentation](https://flask.palletsprojects.com/en/stable/testing/)

### Coverage layers

| Layer | Required evidence |
|---|---|
| Existing regression | Retain relevant current assertions, including direct cashing/history and legacy finance cases. Keep Streamlit tests runnable in a separate legacy environment until equivalent Flask coverage exists. |
| Pure domain | Parameterized Decimal, allocation, calendar, employment overlap/proration, FIFO recovery, debt cap and warning-threshold fixtures. No browser/DB required. |
| Service/SQL | Preserve parameterization and query meaning; fake cursors are useful for plumbing but not proof SQL calculates correctly. |
| PostgreSQL integration | Isolated PostgreSQL 18.6: valid/invalid commands actually commit; test deferred errors, rollback, generated values, locks, unique checks and restricted role. |
| Flask routes/forms | Auth redirects/forbidden actions, CSRF, tampered IDs, missing fields, safe messages, GET does not mutate, POST/redirect/GET, draft retention, file/export authorization. |
| Concurrency/retry | Two connections, same/different command keys, lost response after commit, double submit, stale edit, restart, simultaneous loan/owner/obligation payment and payroll recovery. |
| Browser/phone | Playwright at compact phone, larger phone and desktop widths; header/footer/tab overlap, keyboard/focus, field errors, charts, Back/refresh, downloads and slow/failing network. |
| Real user acceptance | Mother records a reviewed historical day, corrects a permitted mistake, settles an obligation, checks Finance/Bus Accounts/Reports, exports and starts a backup using an isolated approved dataset. |
| Deployment/recovery | Ubuntu/Python 3.12 clean install, DB read-only manifest, private service health, rollback, failed-release detection, and actual backup restore on a non-production database. |

### Minimum human-behavior scenarios

1. Cashing for one bus; multiple buses with equal/different allocations; remove a selected bus; blank one amount; Sunday option; wrong weekday; backfill at baseline; inactive/unknown days.
2. Standard shortage/surplus with signed unallocated difference; adjusted reason; confirmed unpaid obligation; partial and full settlement; attempt overpayment; correction blocked by existing obligations/payments.
3. Expense: general/bus, invalid category/bus/account, title length/word limit, paid-to/reference/notes, zero/negative/NaN/infinite/overscale values, edit/delete with confirmation, servicing-linked deletion rejected.
4. Submit twice, refresh success page, use browser Back, open two forms, expire login before submit, retry after response loss, restart after commit and attempt stale correction. One intended payment produces one committed result.
5. Payroll: first/last partial employment month, leap-year February, salary override, advance cap, FIFO/partial recovery, excessive deduction, duplicate monthly salary, zero-net paid salary, cancellation releases correct allocations.
6. Loans/owner money: unidentified loan with/without notes, nullable terms, principal versus fees, business versus owner source, payment above debt, concurrent repayments, linked correction, drawing not operating cost, loan creation does not invent income.
7. Servicing: paid/zero-cost, actual payment versus completion date, future date rejection, duplicate bus/date, parts/transport/labour generated total, old-event correction and next due date; 14/7/day-zero/overdue warning boundaries.
8. Finance: October clean slate, November carry-forward and December, three-/six-month/custom periods, no-activity month, transfer plus fee, owner funding, advance and loan payments, account opening versus business baseline.
9. Reporting: summary/detail/category/total reconciliation, earned salary versus payment, shared historical costs, unknown expected cashing, unallocated receipts, no-record exports, malicious formula-like text and actual XLSX/CSV dates/amounts.
10. Charts: a 4,000 expense, expense higher than revenue, zero values, negative business balance, both bar series independently zero-based, all timeline points/final endpoint and no clipped phone labels.
11. Security/backup: unauthorized direct record/export/backup URL, CSRF failure, forged host/proxy headers, stale session, missing pg tools, failed dump, private download and archive-list success distinguished from restore success.

### Test safety and known gaps

Never give CI/test runners production credentials. Existing test_connection reads the configured database; new fixtures must fail closed unless an explicitly isolated test target is selected. Read-only production verification, if separately approved, is a distinct operation and never executes fixture migrations, seed_demo_data or write smoke scripts.

Use GitHub-hosted Ubuntu runners for tests and build dependencies, not the VPS. Use an isolated PostgreSQL 18.6 service and a reviewed test schema/sanitized fixtures. Existing migration seeds/backfills contain business assumptions; do not blindly replay them as the test setup or expose real business CSV/XLSX data in artifacts.

The 97 passing tests are not a security/concurrency/report-correctness certificate. For example, Bus Accounts tests use fake results, and the servicing early/late test exercises date arithmetic rather than the full scheduling transaction. Add real calculation/DB/route cases for those paths. No new pytest suite, Flask server, browser run or VPS verification was executed in this planning task.

## 8. Phased Implementation Roadmap

Implement only after authorization, one small vertical slice at a time. Every phase includes tests and a review gate; retaining a feature in this plan is not permission to silently broaden its business meaning.

### Phase 0: Contracts and Read-Only Environment Baseline

- Features/work: confirm production/development isolation, credentials/roles, exact VPS restored schema manifest and accounting/date contracts; approve parity checklist and sensitive-data handling.
- Reuse: six historical audits, SQL migrations, existing service/test definitions and backup tooling as evidence, not commands to rerun on smartfleet.
- New files later: deployment/environment runbook, safe test fixtures/config and recorded schema manifest with no credentials/business records.
- Tests: Git refs/tag unchanged; test-target guards; read-only schema/privilege comparison; expected constraints/functions present. No production mutation.
- Acceptance: no uncertainty about which DB may receive test writes; production baseline is documented and recovery verification scheduled.
- Dependency: none. Any missing schema object is reported for explicit approval, not auto-created.

### Phase 1: Working Flask Foundation, No Financial Writes

- Features: create_app, environment validation, login/logout, error pages, CSRF, mobile shell, Home/Buses/Finance/More navigation, basic health and read-only bus list.
- Reuse: bus_service.get_all_buses/overview, formatting/date utilities and navigation labels; no imports of app.py or Streamlit page modules.
- New files: smartfleet_web factory/config/auth/errors/extensions, home/fleet Blueprints, base/auth/bus templates, app.css, wsgi.py, Flask/test requirements, tests/web fixtures.
- Tests: factory isolation, missing secrets fail safely, authentication/CSRF, read-only query, empty/list/error pages, phone navigation/layout, Python 3.12 clean dependency resolution.
- Acceptance: app starts locally and in Ubuntu test environment, phone-friendly navigation works, no page writes to PostgreSQL and no DB secrets reach HTML/cookies/logs.
- Dependency: Phase 0. A local-only unprotected prototype is not permission for public deployment.

### Phase 2: Shared Financial Command Safety

- Features: supplied-connection/UOW seam, safe validation/errors, permission policy, approved durable command/audit mechanism, stale-edit and business-key locking policy.
- Reuse: existing psycopg transaction pattern, Decimal helpers, correction_audit JSONB and existing row locks without rewriting accounting SQL.
- New files: commands.py, transaction helper only if useful, common form handling and integration/retry/permission tests. Adapt services only as each needs shared ownership.
- Tests: same key/same payload exactly once, key/payload conflict, timeout after commit, crash/restart, lock races, deferred check failure/rollback and actor audit in the same commit.
- Acceptance: no partial transaction or false success; durable deduplication survives process restart; no schema change slips in. If the schema-preserving design is not approved, financial writes remain disabled.
- Dependency: Phases 0-1. Must pass before any public financial POST.

### Phase 3: Fleet, Reference Data, Presets and Account Management

- Features: bus create/edit/status/history/doc metadata, routes, drivers, existing employment/assignment operations, settings and starting-account balances.
- Reuse: bus_service, driver_service, route_service, preset_service, account_service; keep exact existing validation and effective-date meaning.
- New files: fleet/management/finance routes/forms/templates and fleet/preset/account tests.
- Tests: duplicate registration/route, invalid capacity/IDs, history boundaries/overlap, effective salary/rates, restricted settings, opening-balance versus business baseline and untouched historical rows.
- Acceptance: all completed fleet/config operations have equivalent phone workflows; incomplete lifecycle/negative-warning/transfer/upload capabilities are not falsely presented as delivered.
- Dependency: Phase 1; Phase 2 for audited/retry-safe mutations and financial settings. Coverage/schedule changes require the decision below first.

### Phase 4: Expenses

- Features: record, history/detail, edit and confirmed delete for existing GENERAL/BUS expense workflows; category grouping and paid-to/reference/notes.
- Reuse: expense_service, category restrictions and ledger linking; no new MULTI_BUS entry or owner-personal selector by default.
- New files: expenses Blueprint/forms/templates and route/transaction/browser fixtures.
- Tests: valid general/bus expense, invalid title/category/account/bus/money, edit/delete, linked servicing restrictions, repeat/stale POST, ledger reconciliation and audit atomicity.
- Acceptance: one intended expense has one expense/payment; failures retain inputs and commit nothing; historical shared/funded data remains readable.
- Dependency: Phases 2-3.

### Phase 5: Cashing, Backfill and Obligations

- Features: Standard/Adjust Buses, coverage/date preview, multi-bus selection, Sunday workers, variance/provenance, direct historical edits, smart details/corrections/delete, obligation payment/history.
- Reuse: smart_cashing_service, cashing_service, pure cashing helpers; extract widget-mixed allocation/classification arithmetic into Decimal functions only where needed.
- New files: cashing Blueprint/forms/templates, small forms.js preview handling, domain helper if justified, integration/phone tests.
- Tests: one/multiple/missing buses/amounts, signed shortages/surplus, rate/eligibility/weekday/backfill, duplicate business key, locks, obligation cap/OTHER-IN treatment, failed-input retention and confirmed-success reset.
- Acceptance: full current cashing functionality works through one coherent form; server-derived expectations/locks are authoritative, repeat command cannot duplicate money.
- Dependency: Phases 2-3; reuse form patterns proven in Phase 4.

### Phase 6: Home, Finance and Bus Accounts

- Features: actual dashboards, period lists/balances, account display, timeline, bus contribution/trends/categories and recent activity.
- Reuse: finance_service, dashboard_service, performance_service, bus_account_service and pure date/timeline functions; approve/fix the verified report-definition mismatch, not unrelated refactors.
- New files: complete home/finance routes/templates, bus-accounts views, charts.js and pinned vendor assets.
- Tests: zero baseline/carry-forward/transfer/financing distinctions, October-November-December fixtures, summary/detail reconciliation including salary, chart actual units/grouping/negative balance and phone framing.
- Acceptance: agreed Home cards and Finance Balance Now/filtered movement design preserved; no contradictory period labels or hidden cashflow redefinition.
- Dependency: Phases 3-5 and approved reporting/period decisions. Salary fixtures are needed now even before the salary UI is ported.

### Phase 7: Driver Payroll and Advances

- Features: driver money profiles/detail, advances, salary preview/payment/recoveries/deductions and existing correction/reclassification capability.
- Reuse: driver_money_service proration/FIFO/cap/locks/status refresh and presets.
- New files: driver_money Blueprint/forms/templates and real DB allocation/race tests.
- Tests: employment boundaries, effective salary, monthly uniqueness, cap/over-recovery, zero-net salary, payment/earned-cost distinction, cancellation allocation cleanup and concurrency.
- Acceptance: payroll and advances reconcile to ledger/outstanding balances and agree with Phase 6 reporting; no replaced or weakened database rules.
- Dependency: Phases 2-3 and Phase 6 measure definitions.

### Phase 8: Loans and Owner Money

- Features: loan record/list, identified/unidentified repayments with fees and payment source, owner funding/drawing/personal settlement/repayment and existing corrections.
- Reuse: loan_service outstanding/source/cancellation/reclassification logic and locking; do not fabricate unknown facts or loan receipts.
- New files: loans Blueprint/forms/templates and principal/fee/source/audit/concurrency tests.
- Tests: unknown loan notes, optional terms, principal caps, owner liability, business cash versus personal funds, linked correction, concurrent repayment and duplicate command.
- Acceptance: lender debt, owner debt and cashflow reconcile independently; unidentified-loan association remains a separately approved workflow if requested.
- Dependency: Phases 2-3 and Phase 6 contracts.

### Phase 9: Servicing, Schedules and Reminders

- Features: current servicing entry/history/correction, manual schedule correction, due/expiry/deactivated/pending alerts and bus/Home shortcuts.
- Reuse: maintenance_service, reminder_service and servicing cost/threshold helpers; keep default business-account payment behavior.
- New files: maintenance Blueprint/forms/templates and DB/schedule/phone tests.
- Tests: positive/zero cost, actual dates, generated total, duplicate job, latest-event schedule refresh, early/late/old correction, 35-day default/custom interval and alert boundaries.
- Acceptance: exactly one linked payment/expense for paid servicing; schedule follows actual latest completion without inventing money; existing warnings remain available.
- Dependency: Phases 2-4 and existing fleet/config references.

### Phase 10: Reports, Exports, Backups, Help and Full Parity

- Features: full business/reconciliation reports and warning sections, CSV/XLSX, owner-only backup create/list/download, More/setup checks and searchable help.
- Reuse: business_report_service, report_service, report_export_service, backup_service, validation_service, help_content; adapt report snapshots and Linux environment/file handling.
- New files: reports/management templates/routes, private backup job/runbook design, export/permission/recovery/browser tests.
- Tests: all report totals, shared/unknown historical data, CSV formula safety/roundtrip dates, empty reports, private downloads/path traversal, failed backup, archive list versus actual isolated restore and resource bounds.
- Acceptance: feature checklist has no unapproved omissions; docs reflect real screens; backup work cannot exhaust the tiny server or expose raw files.
- Dependency: Phases 6-9 for report semantics; backup configuration can be prepared earlier, but not deployed now.

### Phase 11: Deployment Rehearsal, Approval and Cutover

- Features: future CI/CD, isolated development deployment, production approval, monitoring and rollback rehearsal; no functionality removal.
- Reuse: service/form/integration acceptance results and backup/reconciliation evidence.
- New files only after approval: deploy/Nginx/systemd/Gunicorn templates, .github workflows, operational acceptance checklist and release runbook.
- Tests: complete Ubuntu/Python 3.12/PostgreSQL 18.6 suite, browser journey, bounded load, exact schema fingerprint, restricted permissions, backup restoration, failed health check and code rollback.
- Acceptance: production approval on an exact tested SHA, one writer, unchanged approved schema, verified business totals, clear user handover and functioning alerts.
- Dependency: all relevant parity phases plus separate authorization to configure deployment. master stays at 46c7643; deployment does not require moving it.

## 9. VPS Deployment Strategy, Not Configuration

### Environment isolation

Production uses the already-restored smartfleet database. Do not reset, restore over, rename, seed or automatically migrate it. Development must use separate credentials and an explicitly approved separate database/dataset; it must not write to smartfleet. If this VPS cannot safely host both, run development locally/elsewhere or on demand, not with shared production write access.

Use distinct service users, environment files, sockets, domains/subdomains and cookie names/keys. No dev identity can read production secrets/backups. VPS database/network/role checks remain unverified until authorized access is provided; this plan is not a deployment instruction to execute now.

### Production process and files

- Nginx serves HTTPS/static files and proxies to private Gunicorn. Gunicorn runs as a non-root service supervised by systemd, not Flask's development server. [Flask production deployment](https://flask.palletsprojects.com/en/stable/deploying/index.html)
- Proposed paths: /srv/smartfleet/releases/<commit-sha>, a current symlink, and private shared directories outside each release. Root/service-owned environment files live outside Git with restrictive permissions. Exact paths/ownership are deployment decisions, not files created here.
- Keep secrets and business backups outside release directories. API/session keys must not change accidentally on each restart. Do not commit .env, private keys, database dumps, personal records or generated exports.
- Use isolated virtual environments with compatible, recorded Python 3.12 dependencies. Build/test on CI; do not compile large packages or run browser/Streamlit test stacks on the VPS.
- Start small and measure: one worker/two threads, bounded request/query/connection timeouts, paginated lists, lazy reports, serialized backup creation, log rotation and disk/memory alerts. Configure PostgreSQL memory/connection settings only after inspection and separately authorized operational review; no unmeasured tuning commands are proposed for immediate execution.
- Long backup work should use a narrowly authorized serialized systemd/oneshot-style operation or equivalent limited mechanism, not arbitrary shell execution from a form or a permanent Redis/Celery stack. Keep private status/results, stream downloads and test timeouts/restart recovery. No broad passwordless sudo for the web user.
- Keep only a small number of releases locally, rotate logs and plan backup/WAL/disk budgets. The 25 GB disk is not an unlimited backup store. Keep encrypted off-host backups and prove restoration elsewhere.

### Future GitHub Actions flow

1. On pull request/push, run tests on a GitHub-hosted Ubuntu runner using Python 3.12 and isolated PostgreSQL 18.6. No VPS/production secrets are available to untrusted pull requests.
2. Verify dependency resolution, unit/service/web/integration/browser tests as appropriate, secret scanning, approved schema/migration diff policy and absence of private business data in artifacts. Pin external Actions to reviewed revisions and restrict token permissions.
3. For successful pushes to migration/flask, prepare a minimal release artifact identified by the exact tested commit and checksum. Do not deploy git pull of a moving branch or include the whole historical repo/data files. Dev deployment waits on successful tests.
4. Deploy development through a restricted deployment identity to the isolated development service/data. Serialize deployments per environment; avoid canceling a release halfway through filesystem switching. Reject stale/out-of-order release promotion.
5. Run local/private readiness checks and external HTTPS smoke checks. A liveness response is not enough: verify required DB access/schema compatibility and a read-only representative page without exposing credentials/catalog details.
6. Production is a separate promotion of the same tested artifact/SHA, only after explicit approval. It is not an automatic side effect of a migration/flask push, and master does not need to change.
7. Stage release files, validate settings/import/DB read-only readiness, switch the release pointer, restart/reload the restricted service within memory limits, and verify health/user paths. If verification fails, restore the previous compatible code release, mark deployment failed and notify the owner with SHA/step/request ID, without secrets.
8. Record successful/failed deployment status and send the chosen notification. Do not report success because SSH connected or a restart command returned zero.

GitHub environments can gate jobs and secret access, but reviewer availability depends on repository visibility and GitHub plan. Verify this before designing a guaranteed approval gate. Do not assume a private/free repository has required-reviewer protection, and do not confuse a manual workflow_dispatch button with an enforced independent approval. If the available plan cannot enforce the desired production gate, retain an explicit owner-controlled VPS promotion step and withhold production deployment credentials from automatic jobs. [GitHub environment requirements](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)

### Explicit schema safeguards

- Neither app startup nor ordinary deployment runs CREATE/ALTER/DROP, seed scripts, migration replay, ORM create_all or production restore.
- Maintain an expected schema manifest/fingerprint from approved definitions; readiness reports unexpected differences and fails safely instead of repairing them.
- A future schema change requires its own reviewed SQL, rationale, compatibility/rollback review, isolated restoration rehearsal, backup check, explicit authorization and separate privileged execution. Runtime/deployment users do not silently gain that authority.
- A proposed identity/command table or performance index is a schema change even if described as infrastructure; request approval first.
- Do not use production DML as a health check. Financial reconciliation at cutover is read-only until users are authorized to record.
- Code rollback never restores yesterday's database over new entries. Preserve post-cutover transactions and reconcile before any separately approved data repair.

## 10. Risks, Unresolved Questions and Recommendations

| Priority | Issue/decision | Recommendation |
|---|---|---|
| Critical | VPS restored constraints/privileges have not been inspected here | Read-only manifest/role inspection before public writes; never infer server security from the old local audit. |
| Critical | No auth/CSRF/permissions in old app | Deliver these in the foundation. Start with approved environment-configured owner login if avoiding schema changes. |
| High | Durable retry and actor audit need storage/transaction coordination | Approve/test use of existing JSONB audit with locks or explicitly approve a different design before financial rollout. |
| High | Dev versus production isolation on 1 GB VPS | Separate credentials/data; CI and browser tests off-server; stop dev or use another environment if resource budget fails. |
| High | Bus summary/detail cost mismatch | Agree expected cost definition and fixtures, then correct the narrow mismatch during authorized reporting migration. |
| High | Correction/delete history policy | Preserve current financial effects; add actor/reason/before-after evidence, and separately approve any switch to reversal-only accounting. |
| High | Clean-slate business balance versus per-account opening balances | Keep current October-zero reporting policy unless explicitly revised. Confirm whether future-dated entries belong in Home baseline totals. |
| Medium | Home duplicate period controls and rolling/calendar inconsistency | Choose the minimum UI clarification after reviewing current examples; do not silently change financial windows. |
| Medium | Preset schedule settings not consumed by smart coverage | Decide whether to preserve fixed Thu/Sun coverage initially or authorize effective-dated schedule integration with historical tests. |
| Medium | Expected payroll/loan/servicing capabilities exceed actual forms in old planning docs | Use the verified matrix above as parity scope; enhancements are separate, not missing migrations automatically to implement. |
| Medium | Unknown loan association and principal | Keep unidentified notes/history. Agree an audited association workflow later; do not invent the 15,000 loan's facts. |
| Medium | GitHub approval/notifications and SSH deployment permissions unknown | Confirm repo visibility/plan, reviewer identity, domain, access and notification channel before configuring Actions. |
| Medium | Disk/backups/restore objectives unknown | Agree frequency, off-host destination, retention, acceptable data loss and restore time; test a non-production restore. |
| Medium | Python 3.12 dependencies unverified despite syntax pass | Resolve/test a fresh minimal Ubuntu runtime rather than copy the Python 3.14 Streamlit freeze. |
| Medium | Full managed users, uploads, transfers and lifecycle extensions need decisions | Not prerequisites for read-only foundation; never advertise them as already completed or add schema by stealth. |

Questions to settle before their corresponding implementation gates: who may record and correct; one or multiple owner accounts; allowed public access/domain; whether the VPS still runs any legacy writer; desired Home filter behavior; whether schedule presets must drive coverage immediately; loan association rules; backup/recovery targets; writable development database location; approval and notification capabilities.

**Immediate recommended authorization scope:** Phase 0 plus Phase 1 only: protected, phone-first Flask foundation and read-only bus list with tests. Do not begin all financial modules or configure deployment in the same first change. Once that foundation is reviewed, authorize command safety and feature slices in order.

This plan stops at design. No implementation, database change, commit, push or deployment authorization is implied by its creation.
