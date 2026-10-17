# Isolated Flask Development

Stages 1-2 provide the secure foundation and reference-data management, not full feature parity. The Streamlit application remains the complete reference. No production deployment is authorized.

## Environment

Use Python 3.12 in a separate `.venv-flask`; do not replace the legacy `.venv`.

```powershell
py -3.12 -m venv .venv-flask
.\.venv-flask\Scripts\python.exe -m pip install -r requirements-flask-test.txt
.\.venv-flask\Scripts\python.exe -m playwright install chromium
.\.venv-flask\Scripts\python.exe scripts/setup_flask_dev.py
```

If Python 3.12 is installed workspace-locally with uv, use that interpreter instead of py. Development tools, cached runtimes and temporary files must remain ignored. The test requirements include cryptography for local self-signed HTTPS, not for the production runtime.

Provisioning reads only schema (no real records) from the existing **loopback-only** local PostgreSQL connection, creates two new isolated databases and dedicated roles, and inserts synthetic routes/buses. It refuses remote connections, existing target roles/databases, partial setup and credential overwrites. It never resets, migrates or writes to the source database and never contacts the VPS.

Generated credentials are in ignored `.env.flask.local` and `.env.flask.test.local`. The initial generated owner login is in ignored `.local/FLASK_OWNER_LOGIN.txt`. Keep these private; do not include them in screenshots, commits, support messages or exports. `.env.example` contains placeholders only. The reader roles cannot mutate table data even if a connection tries to disable read-only mode.

## Run and verify

```powershell
.\.venv-flask\Scripts\python.exe scripts/run_flask_dev.py --port 5001
.\.venv-flask\Scripts\python.exe -m pytest tests/web tests/integration -q
.\.venv-flask\Scripts\python.exe -m ruff check .
.\.venv-flask\Scripts\python.exe -m ruff format --check .
.\.venv-flask\Scripts\python.exe -m pip_audit -r requirements-flask.txt
```

Development URL: https://127.0.0.1:5001 (local self-signed certificate). The development server binds loopback only, is not production hosting, and does not provide a phone/public URL. Browser tests use isolated loopback HTTPS with a fresh server and synthetic database; only they ignore the self-signed certificate.

For a certificate-warning-free preview on this PC, run `scripts/run_flask_dev.py --http --port 5002` with the Flask environment's Python and open http://127.0.0.1:5002. This explicit local-only mode uses a distinct HTTP session cookie; it does not alter the secure-cookie default, production configuration, database isolation or loopback binding. Do not expose this development server on the network.

Stage 1 includes owner sign-in/logout, expiring/revocable sessions, CSRF, bounded login throttling, safe errors, four navigation shells and real paginated read-only bus listing. Finance/dashboard totals and financial recording are not implemented yet. Do not interpret shell pages as completed financial functionality.

## Stage 2 management and command safety

After Stage 1 provisioning, run `.venv-flask/Scripts/python.exe scripts/setup_flask_stage2.py`. It accepts only the existing loopback `smartfleet_flask_dev` and `smartfleet_flask_test` targets and their dedicated owner credentials. It applies the versioned `migrations/flask/001_command_safety.sql` only there, adds restricted writer roles, and initializes missing synthetic configuration/history. It does not replay any legacy migration or touch the source/VPS database. Restart the preview to load generated writer settings. Private generated credentials stay in ignored local environment files.

Reads still use the read-only role; commands alone use the separate writer. Runtime writers cannot create schema, delete business records, edit/delete audit records, or write the financial ledger at this stage. Missing writer configuration fails closed on save. Home/Finance totals and cashing/expense entry remain for later stages.

Buses now links to registration, details, editing and effective-dated status/route history. Registration supports an optional available driver and five existing document categories. Drivers can be created with employment or edited; their initial permanent assignment can be made while registering a bus. Routes can be added/viewed, matching the existing Streamlit scope. This does not invent employment termination/re-employment or route-deletion workflows absent from the legacy UI. Accounts supports the existing starting-balance workflow, with reasons and audit evidence.

More -> Business Presets includes cashing rates, salary presets, advance limit, reminders, reporting baseline and Schedule. Thursday/Sunday are initialized as defaults. Schedule replaces a complete weekly configuration at a new effective date, retaining closed historical rules; it never overwrites recorded collections. A supported week covers Monday-Saturday exactly once in consecutive groups, plus one optional previous-Sunday allocation. A date-level transition check rejects duplicated/missing work across the changeover. Other financial meanings, including Sunday-only normal coverage or disjoint day groups, are deliberately rejected rather than invented. Already-recorded affected periods block a change. Existing bus history determines eligible active work days.

The shared smart-cashing preview accepts explicit effective-dated `schedule_rules`. Flask's protected `/presets/schedule/coverage?date=YYYY-MM-DD` resolves those presets now; Stage 3 recording routes must use that same resolver/rule list for both preview and commit, never the legacy fixed-day fallback. Existing Streamlit callers retain their unchanged legacy default while Flask feature migration continues.

Durable command and actor-attributed before/after audit rows share the business commit. UUID keys and database advisory locks serialize retries and stale edits, with signed form versions and CSRF. Service contexts borrow the command connection without committing independently; caught nested failures still force rollback. Commit-time database errors and audit-write errors return no success and roll back everything. Successful POST redirects clear the workflow; invalid submissions retain their fields. Keys/audits are insert-only for the runtime writer. The existing `correction_audit` table and cancellation effects remain unchanged for Stage 3+ porting.

Tests restore only synthetic changes in the dedicated test database. Do not run its integration fixtures with concurrent pytest workers or another writer on that same test database. Browser artifacts remain ignored. The application is still single-process for owner sessions/throttling, and still cannot start with production configuration.

## Stage 3 recording

Run `.venv-flask/Scripts/python.exe scripts/setup_flask_stage3.py` only after Stage 2 provisioning. It verifies the two local isolated names/roles, extends explicit recording-table grants and initializes synthetic operating categories. No migration of the existing business schema is performed. Runtime writers still cannot alter schema, delete fleet records or change command/audit evidence.

Finance links to Record Cashing, Record Expense, paginated histories and unpaid obligations. New cashing uses one complete invoice with dated schedule rules, historical status/assignment and effective rates. Standard records every eligible bus's full expected amount; there is no bus selector or editable aggregate receipt. Adjusted Buses expands only explicitly selected exceptions; unselected or cleared adjustments retain standard amounts. Selected blank amounts are invalid, explicit zero is supported, and shortages require classification/explanation and responsibility for confirmed obligations. Optional Sunday work and worked-day adjustments remain available within an exception. Airtel and totals are resolved on the server. A persisted receipt follows success; Record another opens a clean Standard form. Existing signed/unallocated and DIRECT historical collections remain editable through the compatibility correction editor, without automatically expanding old entries into a new full-fleet receipt. Corrections/deletions/settlements commit actor-attributed before/after evidence atomically and preserve existing financial effects. Linked servicing/payroll/loan/owner records are not repurposed into ordinary expenses. Settlement payments remain OTHER-IN, not duplicated CASHING revenue.

Automated tests use only synthetic data in smartfleet_flask_test. The development preview initially used synthetic data; the owner-authorized snapshot below replaces only smartfleet_flask_dev with copied real records. Simultaneous legacy Streamlit writes against the same database are not supported by this isolated migration; production activation must retire the legacy writer or otherwise establish a separately reviewed shared command policy. Current command snapshots are bounded to 5,000 rows per relevant table; narrower evidence/version queries must be reviewed before a larger production workload reaches that limit. A safety limit is not a claim of unlimited scale.

The initial in-memory owner-session registry is deliberately single-process: restart signs all devices out, logout revokes captured cookies, and capacity is bounded. Do not run multiple Gunicorn workers with this store. A shared session backend must be designed/tested before increasing processes. Login throttling is bounded and thread-safe in this process; production must also rate-limit at the trusted reverse proxy. No client-supplied forwarded address is trusted now.

The shared database connection has a context-local settings override for Flask, with mandatory isolated DB/role validation and read-only/timeouts. Existing Streamlit calls keep their legacy environment behavior. No Flask request falls back to the Streamlit database credentials.

## Stage 4 dashboards and reporting

Home now shows baseline-to-today Total Revenue, Total Expenses and Business Balance, with calendar reporting controls in the scrolling body. Finance retains fixed General, Collections, Expenses and Balances tabs. On Balances, Business Balance Now remains outside the period filter; Money Received and Money Paid Out use the displayed selected dates. One month/three months are calendar periods; Custom offers all available baseline activity, six months or explicit dates. Opening/closing figures remain service/reporting concepts, not additional Balances cards.

Home's Business performance red line is labelled Total Expenses and accumulates all outgoing ledger payments within the selected chart period, including financing repayments, salary payments, drawings and fees. Internal TRANSFER rows are excluded so moving money between business accounts is not spending. This matches the Home Total Expenses definition for the same dates, without counting an expense and its linked payment twice. Existing operating-cost services, the green revenue/blue balance lines and bus cost-attribution charts are unchanged.

All sections of a report share a read-only repeatable-read PostgreSQL snapshot. Current balances exclude future ledger entries and consolidated balances retain the existing zero reporting baseline, separate from individual account starting balances. Account management also excludes future transactions from balances shown now. Explicit future custom report periods do not change the current balance.

Bus Accounts detail uses the same operating-category exclusions, exact multi-bus allocations and uniquely attributable earned driver salaries as its summary. Shared/general costs remain separate. Loan repayments, owner financing and internal transfers are not repurposed as bus operating costs. Existing attribution policy is retained rather than allocating shared costs arbitrarily.

Charts use locally vendored Chart.js 4.5.1 (MIT license in static/vendor/CHARTJS-LICENSE), not a remote runtime dependency. The official npm package asset was fetched over verified HTTPS from jsDelivr; SHA-256: 48444a82d4edcb5bec0f1965faacdde18d9c17db3063d042abada2f705c9f54a. Grouped bars use actual currency units and independent zero baselines; the business-balance line permits negative values. No Node build or server runtime is required. Chart data is numeric/JSON-escaped and the existing self-only content security policy is retained.

## Stage 5 payroll and money

After the previous isolated setup, run scripts/setup_flask_stage5.py using the Flask environment. It accepts only the exact two loopback development/test database names and existing owner/writer roles. It does not read .env source credentials, replay migrations or change business schema. Writer grants cover the existing payroll/loan tables and insert-only legacy correction evidence; web command/audit evidence remains append-only. Tests still use only smartfleet_flask_test, never the copied business preview.

More exposes Driver Money, Loans and Owner Money. Salary preview is read-only; saving recomputes in the audited transaction, applies FIFO recovery/limits, records deduction allocations and supports zero-net pay. Reversals use confirmation/reason and preserve actor-attributed before/after evidence. Loan records do not fabricate cash receipts. Owner-personal repayments reduce lender principal/increase owner liability without business cash movement. Identifying an old repayment only links it to a known loan under principal limits; it does not record cash twice.

Principal and fee records remain separate under the existing schema. Reverse principal leaves separately recorded finance charges intact; no date/text matching is used to guess fee ownership. Owner-funded fee records are displayed as personal expense funding, not offered through a reversal that the service rejects. A unified charge correction is a pending reviewed design, not a claimed completed feature.

Expense scope is a General / Bus Specific segmented control. Cashing/expense accounts are resolved to active Airtel on the server; supplied account IDs cannot redirect payments. Only cashing registrations are displayed; Adjusted Buses uses individual tap-friendly cards. Bus status filters apply immediately. More/Finance no longer expose account-management links; Bus Accounts remains distinct. Stage 6 now enables servicing, reminders, reports, backups and help when its acceptance gates pass.

## Stage 6 servicing, reports and private backups

After the earlier isolated provisioning, run `.venv-flask/Scripts/python.exe scripts/setup_flask_stage6.py`. It verifies the exact two local database/reader/writer/owner identities, grants maintenance INSERT/UPDATE and reader SELECT on sequences needed by pg_dump, and initializes only a missing Servicing category. No schema migration or original/VPS database connection occurs.

More > Record Servicing accepts completion date, labour, transport and other costs. Paid servicing requires the actual payment date and creates one linked bus expense/payment using the existing business payment account. Zero cost creates no cash payment. History corrections update the existing linkage; converting paid to zero removes its linked payment atomically. Schedules use the latest completion and preserve the existing default 35-day interval, with reasoned next-date/frequency corrections. Reminders retains read-only servicing/deactivated/document-expiry/pending groups, not an invented reminder-editing workflow.

Reports provides the existing business, bus, cost, payroll, advances, loan/owner and servicing views plus ledger reconciliation, warnings and protected CSV/XLSX downloads. Dates use the same calendar/baseline logic as the dashboard; reconciliation starts at the clean slate. All report sections share one repeatable-read, read-only transaction. Query time is bounded to 15 seconds, ledger history to 10,000 rows, bus-day expansion to 200,000, export tables to 50,000 aggregate rows and output to 20 MB. A shorter period or separately reviewed larger-volume reporting path is required above those limits. Exports use existing formula escaping and preserve numeric/date cells. No generated report is publicly stored.

Backups uses a new isolated-only adapter, never legacy .env source settings or the old backup directory. Completed custom archives and actor/time/database/size/SHA manifests are stored in ignored `.local/flask-backups/<isolated database>`, outside Flask static/public paths. Owners can create/list/download through authenticated routes; creation requires POST/CSRF and a signed request identity. The same completed key is reused after session/app restart. Database advisory locking serializes concurrent workers; tools have a 60-second timeout, 100 MB archive cap, 500 MB local storage ceiling with reserved headroom and free-disk checks. Partial files cannot be downloaded. No passwords appear in command arguments, manifests or responses. Private filesystem permissions are set where supported; protect the workstation account and directory ACLs too.

Archive checked means pg_restore can list the dump; it is not a claim that every archive was restored. The automated drill restores an actual synthetic archive only into the exact smartfleet_flask_test database, comparing complete table fingerprints and integrity objects. The web app intentionally has no restore endpoint and cannot restore its real-data preview, original database or VPS. Download a protected copy off this computer; automatic retention/deletion, encrypted off-host storage and recovery objectives remain an authorized Stage 7/operations decision. Missing tools, failed dumps, timeouts or capacity limits produce an error, never a completed marker. Creation remains a bounded synchronous single-database task in this isolated pilot; production needs a reviewed background/oneshot backup runner before activation.

Help is searchable by topic/words, uses Flask-specific actions and generic examples, and explains current-vs-period balances, total-expense charts, corrections, obligations and backups. More's setup warnings use only this private backup store rather than accidentally reporting an unrelated main-database backup.

## Regression environments and safety

### Current development data and access

On 17 October 2026 the owner authorized copying the complete local business dataset into smartfleet_flask_dev for recognizable development previews. All 39 business tables were reconciled by row count and full-row fingerprints, with source reads enforced read-only and destination constraints/triggers retained. A backup of the previous synthetic preview and a verification receipt are kept under ignored .local/backups. smartfleet_flask_test remains synthetic and must never be replaced with real records. No automatic refresh or bidirectional synchronization exists.

The local preview at http://127.0.0.1:5002 now shows a **copy** of the real data. Entries there are development-only, not entries in the original smartfleet database. Preserve any preview-only changes before a future refresh. The owner-requested local password is recorded in ignored .local/FLASK_OWNER_LOGIN.txt; only its strong hash is in .env.flask.local. Restarting the preview signs existing sessions out. This local password is not a production-password recommendation. HTTP remains loopback-only; no phone/public exposure was enabled.

Keep FLASK_MIGRATION_PROGRESS.md updated for every implementation, configuration, data-copy or plan change, including exact verification and limitations. Never commit real data, dumps, screenshots, plaintext passwords or database credentials.

The Flask pytest target paths cover new web/integration tests. Legacy Streamlit unittest/AppTest regressions remain in their original files/environment; they are **not replaced or counted as passing by pytest defaults**. Run them separately with read-only PostgreSQL options, excluding the live connection test when not explicitly approved. Record exact counts in the progress document.

Missing local integration credentials or browser binaries fail the required gate; they are not silently skipped. Browser screenshots are private ignored files under `.local/browser`. Security/lint reports must not expose generated credentials. All future financial tests must use isolated/synthetic data and cannot use the VPS database.

This workstation can use its installed Edge engine for Playwright by setting `SMARTFLEET_BROWSER_CHANNEL=msedge`. The same tests still run against real HTTPS routes and the synthetic PostgreSQL test database. Do not weaken browser assertions if launching requires sandbox permission.

Stage 1 gates passed after upgrading the isolated development tools to pip 26.2.1 and cryptography 50.0.2. The advisory audit reported no known vulnerabilities; all 66 foundation tests passed. See the progress document for the earlier failures and exact successful runs. Prefer explicit ignored `--cache-dir .local/pip-audit-cache` and a socket timeout when rerunning the audit.
