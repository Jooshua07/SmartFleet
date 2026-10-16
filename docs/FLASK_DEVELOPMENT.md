# Isolated Flask Development

Stage 1 is a secure, read-only foundation, not feature parity. The Streamlit application remains the complete reference. No production deployment is authorized.

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

The initial in-memory owner-session registry is deliberately single-process: restart signs all devices out, logout revokes captured cookies, and capacity is bounded. Do not run multiple Gunicorn workers with this store. A shared session backend must be designed/tested before increasing processes. Login throttling is bounded and thread-safe in this process; production must also rate-limit at the trusted reverse proxy. No client-supplied forwarded address is trusted now.

The shared database connection has a context-local settings override for Flask, with mandatory isolated DB/role validation and read-only/timeouts. Existing Streamlit calls keep their legacy environment behavior. No Flask request falls back to the Streamlit database credentials.

## Regression environments and safety

The Flask pytest target paths cover new web/integration tests. Legacy Streamlit unittest/AppTest regressions remain in their original files/environment; they are **not replaced or counted as passing by pytest defaults**. Run them separately with read-only PostgreSQL options, excluding the live connection test when not explicitly approved. Record exact counts in the progress document.

Missing local integration credentials or browser binaries fail the required gate; they are not silently skipped. Browser screenshots are private ignored files under `.local/browser`. Security/lint reports must not expose generated credentials. All future financial tests must use isolated/synthetic data and cannot use the VPS database.

This workstation can use its installed Edge engine for Playwright by setting `SMARTFLEET_BROWSER_CHANNEL=msedge`. The same tests still run against real HTTPS routes and the synthetic PostgreSQL test database. Do not weaken browser assertions if launching requires sandbox permission.

Stage 1 gates passed after upgrading the isolated development tools to pip 26.2.1 and cryptography 50.0.2. The advisory audit reported no known vulnerabilities; all 66 foundation tests passed. See the progress document for the earlier failures and exact successful runs. Prefer explicit ignored `--cache-dir .local/pip-audit-cache` and a socket timeout when rerunning the audit.
