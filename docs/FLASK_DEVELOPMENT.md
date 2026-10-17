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

Finance links to Record Cashing, Record Expense, paginated histories and unpaid obligations. Cashing uses one multi-bus form and dated schedule rules for preview and commit, including historical status/assignment and optional Sunday work. Standard cashing retains estimated allocations and signed unallocated differences; Adjust buses records explicit allocations, explanations/classifications and optional confirmed unpaid responsibility. Historical DIRECT collections remain editable through their existing amount-based semantics. Corrections/deletions/settlements commit their actor-attributed before/after evidence atomically and preserve existing financial effects. Linked servicing/payroll/loan/owner records are not repurposed into ordinary expenses. Settlement payments remain OTHER-IN, not duplicated CASHING revenue.

Only synthetic local data is used. Simultaneous legacy Streamlit writes against the same database are not supported by this isolated migration; production activation must retire the legacy writer or otherwise establish a separately reviewed shared command policy. Current command snapshots are bounded to 5,000 rows per relevant table; narrower evidence/version queries must be reviewed before a larger production workload reaches that limit. A safety limit is not a claim of unlimited scale.

The initial in-memory owner-session registry is deliberately single-process: restart signs all devices out, logout revokes captured cookies, and capacity is bounded. Do not run multiple Gunicorn workers with this store. A shared session backend must be designed/tested before increasing processes. Login throttling is bounded and thread-safe in this process; production must also rate-limit at the trusted reverse proxy. No client-supplied forwarded address is trusted now.

The shared database connection has a context-local settings override for Flask, with mandatory isolated DB/role validation and read-only/timeouts. Existing Streamlit calls keep their legacy environment behavior. No Flask request falls back to the Streamlit database credentials.

## Regression environments and safety

The Flask pytest target paths cover new web/integration tests. Legacy Streamlit unittest/AppTest regressions remain in their original files/environment; they are **not replaced or counted as passing by pytest defaults**. Run them separately with read-only PostgreSQL options, excluding the live connection test when not explicitly approved. Record exact counts in the progress document.

Missing local integration credentials or browser binaries fail the required gate; they are not silently skipped. Browser screenshots are private ignored files under `.local/browser`. Security/lint reports must not expose generated credentials. All future financial tests must use isolated/synthetic data and cannot use the VPS database.

This workstation can use its installed Edge engine for Playwright by setting `SMARTFLEET_BROWSER_CHANNEL=msedge`. The same tests still run against real HTTPS routes and the synthetic PostgreSQL test database. Do not weaken browser assertions if launching requires sandbox permission.

Stage 1 gates passed after upgrading the isolated development tools to pip 26.2.1 and cryptography 50.0.2. The advisory audit reported no known vulnerabilities; all 66 foundation tests passed. See the progress document for the earlier failures and exact successful runs. Prefer explicit ignored `--cache-dir .local/pip-audit-cache` and a socket timeout when rerunning the audit.
