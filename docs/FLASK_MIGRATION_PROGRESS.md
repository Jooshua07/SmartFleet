# Flask Migration Progress

Branch: migration/flask. Historical master/tag remain unchanged.

## Stage 1 - Development foundation and secure Flask application

Status: **PASSED on resumption.** The earlier network/security blockers below are historical; patched packages and all current foundation gates now pass.

- Verified original commit b19ed63; the approved migration plan was an untracked document and is preserved.
- Only Python 3.14 was initially installed. Preparing a workspace-local Python 3.12 environment; legacy .venv remains separate.
- Confirmed local PostgreSQL 18.6 via a read-only loopback connection. No VPS connection or real financial data mutation authorized or performed.
- Development/test provisioning will use separate databases/roles and synthetic data; the runtime role will be read-only for this stage.
- Temporary-directory sandbox restrictions affected the initial ensurepip attempt; retry uses ignored workspace-local temporary files.
- Python 3.12.15 is running in `.venv-flask`. The workspace-local uv interpreter download completed; a Windows minor-version-link permission error was avoided by using the installed interpreter's explicit path. The original `.venv` is unchanged.
- Provisioned only `smartfleet_flask_dev` and `smartfleet_flask_test`, with new owner/reader roles, schema-only copies and four synthetic buses each. No real business rows copied. Runtime readers are non-superuser, lack DML permissions and default to read-only.
- Implemented validated environment settings, factory/Blueprints, owner hash authentication, expiring/revocable single-process sessions, bounded/thread-safe throttling, CSRF, safe errors, security headers, fixed shell/navigation, paginated/searchable/status-filtered bus listing and protected readiness.
- Existing service changes are limited to a context-local connection override and optional parameterized pagination/filtering in get_all_buses. Streamlit pages and financial calculations remain unchanged.
- Added `.env.example`, ignore rules, AGENTS.md, separate dependency files, Ruff/pytest configuration, local provisioning/HTTPS launcher, development instructions, Jinja/CSS and pinned Lucide assets/license.
- Added factory/config/auth/session/CSRF/redirect/throttle/pagination/escaping/error tests, real PostgreSQL isolation/permissions/schema/query tests and three HTTPS Playwright viewport journeys (375x667, 390x844, 1366x900).

### Verified checks and commands

Executed with workspace-local TEMP/TMP to avoid the Windows sandbox temporary-directory restriction. Browser tests required permission to launch headless Edge outside the restricted IPC sandbox; they still used only loopback HTTPS and synthetic PostgreSQL data.

| Check | Command/result |
|---|---|
| Python | `.venv-flask/Scripts/python.exe --version`: Python 3.12.15 |
| Unit/routes/PostgreSQL | `.venv-flask/Scripts/python.exe -m pytest tests/web tests/integration/test_foundation_db.py -q`: **58 passed**, 14.74 seconds |
| Browser | Set SMARTFLEET_BROWSER_CHANNEL=msedge; `.venv-flask/Scripts/python.exe -m pytest tests/integration/test_foundation_browser.py -x -q`: **3 passed**, 70.09 seconds; screenshots visually reviewed for phone/desktop |
| Legacy regression | Legacy `.venv` unittest discovery, excluding test_connection with PGOPTIONS default_transaction_read_only=on: **97 passed**, 29.148 seconds; expected Streamlit missing-context warnings only |
| Lint/security rules | `.venv-flask/Scripts/python.exe -m ruff check .`: passed |
| Formatting | `.venv-flask/Scripts/python.exe -m ruff format --check .`: 13 files formatted, passed |
| Package consistency | `.venv-flask/Scripts/python.exe -m pip check`: no broken requirements |
| Patch hygiene | `git diff --check`: passed |
| Vulnerability audit | `pip_audit -r requirements-flask.txt` and installed-environment PyPI/OSV attempts: **UNAVAILABLE/FAILED**, no completed advisory result; never counted as passing |

These are separate successful runs: 58 web/database tests plus 3 browser cases, not a claimed single 61-test invocation. The live legacy database-connection test was deliberately excluded; it was not counted as passed.

### Diagnosed and fixed failures

- First full run: 24 failed / 36 passed. Root causes included CSRF expiry passed as timedelta instead of the seconds required by Flask-WTF, invalid-host error rendering without a URL adapter, and browser launch blocked by sandbox IPC.
- Corrected CSRF expiry to 1800 seconds; a focused five-case route/database rerun passed.
- Invalid Host now returns a safe plain 400 response without URL building or reflecting the host; focused regression passed.
- Corrected browser URL matching: a loose glob incorrectly matched `/login?next=/buses`. The exact destination assertion is retained.
- The next full run had 57 passed / 3 browser failures: wrong-password retry cleared the username and HTML required-field validation prevented another submission. Fixed the real form to preserve username but not password; added the regression and reran browser cases successfully.
- Ruff found two test-fixture false positives. Removed the synthetic password function default and documented the single unsafe-host literal as deliberately rejected test input; no runtime security rule was suppressed.
- Playwright wheel download timed out. Reused the identical installed 1.64.0 distribution in the isolated environment, verifying all 188 recorded package file hashes with zero mismatches; Python-3.12 dependencies were installed separately. Headless Edge was used rather than downloading another browser.

### Current blocker and exact resumption

Both supported advisory providers failed: PyPI TLS/read timeout and OSV HTTPS read timeout. A separate PowerShell HTTPS request to the PyPI metadata endpoint also timed out. Two initially stalled audit processes were specifically identified and stopped; replacement commands used an explicit ignored cache and bounded socket timeout. No vulnerabilities were ignored, no TLS verification was disabled and no successful security result was fabricated.

Rerun, once outbound access works:

```powershell
.\.venv-flask\Scripts\python.exe -m pip_audit --local --strict --cache-dir .local/pip-audit-cache --progress-spinner off --timeout 15
# Supported alternative, not an ignore/bypass:
.\.venv-flask\Scripts\python.exe -m pip_audit --local --strict -s osv --cache-dir .local/pip-audit-osv --progress-spinner off --timeout 15
```

Review/fix any reported vulnerabilities, rerun the relevant tests if dependencies/code change, review the complete diff and secret scan, then commit/push Stage 1 on migration/flask only. Record the actual commit SHA in the next checkpoint. **Current implementation commit: none; HEAD remains b19ed63.**

### Limitations and owner clarification

- This is a read-only foundation, not feature parity. Home/Finance/More are navigation shells; financial entry remains in the unchanged Streamlit reference until later stages pass.
- Sessions/throttling are single-process and bounded; restart signs devices out. Do not run multiple worker processes without a tested shared session/throttle design.
- Runtime configuration rejects production/non-loopback connections at this stage. No VPS access, production schema/data/credential/firewall change or deployment performed.
- The owner clarified: **Sunday and Thursday stay as defaults; More -> Business Presets -> Schedule must allow adding/changing collection days.** Stage 2 must implement effective-dated coverage and safe transitions/backfill without changing stored history. This clarification is preserved here; it is not a claim that the Schedule UI is already implemented.
- Private read-only preview is running at `https://127.0.0.1:5001`; `/health/live` returned HTTP 200. This is a loopback development server, not a production/phone deployment. Generated owner sign-in details remain in ignored `.local/FLASK_OWNER_LOGIN.txt`.
- Credential review compared nine generated secret values against all 202 tracked/unignored candidate files: zero leaked-value matches. Ignore checks passed for both credential files, the local login file, the Flask virtual environment and downloaded interpreter. The full tracked diff passed whitespace checks; no protected branch/tag moved.

### Resumption: loopback HTTP preview and security remediation

- Confirmed current branch is migration/flask, HEAD b19ed63; prior uncommitted work is preserved. No repeated database provisioning or production access.
- Added explicit `--http` launcher mode with fixed 127.0.0.1 binding, debug/reloader disabled, and a separate `smartfleet_loopback_session` cookie. Default HTTPS/secure-cookie configuration is unchanged. HTTP is only for this private local development preview.
- Started `http://127.0.0.1:5002`; health endpoint returned 200. An independent listener check confirmed LocalAddress 127.0.0.1, LocalPort 5002. Login credentials remain in ignored `.local/FLASK_OWNER_LOGIN.txt`.
- Added two launcher cases and expanded browser journeys to both HTTP and HTTPS, checking cookie properties as well as actual login/navigation/logout at phone and desktop sizes.
- Web/database tests: **60 passed in 16.33s**. Initial run had 58 passing and two fixture setup errors caused by the restricted default temporary folder; rerunning with workspace-local TEMP/TMP resolved both without weakening assertions.
- Browser tests: **6 passed in 57.63s** with installed Edge (three viewports, both transports). Ruff check/format, pip check and git diff --check passed.
- Advisory access resumed: installed-environment pip-audit completed with failure, reporting 18 advisory entries (including duplicates) across cryptography 48.0.1 and pip 25.0.1. This is not a passed security gate. Updated the development-only cryptography requirement to >=50.0.2,<51; requested installation of patched cryptography and pip >=26.2.1,<27. The original Streamlit environment and production dependencies are unchanged.
- Security fix sources reviewed: https://cryptography.io/en/50.0.2/changelog/ and https://pip.pypa.io/en/stable/news/. Package download attempts are subject to network stalls; record the final installation/audit result below before any progression.
- Final result: normal and elevated uv downloads stalled and were stopped. A direct elevated pip installation with timeout 15/retries 0 fetched metadata but stalled on the wheel download and was also stopped. A separate PyPI metadata request timed out after 20 seconds. Version verification still shows cryptography 48.0.1 and pip 25.0.1; no patched installation or clean audit is claimed. No installer/audit/test sessions remain running. The intentional HTTP preview remains running; `/login` returned 200 after these attempts.
- Resume by installing `cryptography>=50.0.2,<51` and `pip>=26.2.1,<27` in `.venv-flask` once package downloads work, then rerun pip-audit, package consistency and the affected test/browser gates. Only after Stage 1 passes, is reviewed and committed/pushed may Stage 2 begin. No Stage 2 application/schema changes, commit or push occurred during this resumption.

## Remaining stages

### Security remediation and Stage 1 acceptance

- Installed pip 26.2.1 and cryptography 50.0.2 in the isolated Flask environment. A bounded installer timed out during installation; verified the resulting versions and completed cryptography installation offline from the official PyPI wheel, with SHA-256 verified against official metadata. No certificate checks were disabled.
- `.venv-flask/Scripts/python.exe -m pip_audit --local --strict --cache-dir .local/pip-audit-cache --progress-spinner off --timeout 15`: **No known vulnerabilities found**.
- Full pytest with workspace TEMP/TMP and SMARTFLEET_BROWSER_CHANNEL=msedge: **66 passed in 79.14s**, including six HTTP/HTTPS phone/desktop browser journeys and actual isolated PostgreSQL tests.
- Ruff check, pip check and git diff --check passed. Generated-secret scan across tracked/unignored candidates: **zero matches**. Legacy Streamlit regression remains the separately verified 97-case run above; no legacy code changed during package remediation.
- Stage 1 is eligible for checkpoint on migration/flask. The Stage 1 commit hash will be recorded in the subsequent Stage 2 progress entry, avoiding a self-referential hash.

## Stage 2 - Transaction safety and fleet management

Status: **PASSED**. Stage 1 checkpoint **66eed29** was committed and pushed to migration/flask before Stage 2 began.

### Implemented

- Versioned isolated-only migration for `web_commands` and `web_command_audit`. A durable table is necessary because browser-disabled buttons and process memory cannot prevent retries after a response loss/restart. Both command result and actor/reason/before/after evidence commit atomically with the service operation.
- Shared transaction context lets existing service `with get_connection()` blocks borrow one connection without independent commits. Nested service failures, audit failures and deferred commit failures roll back the command. Database advisory locks, UUID keys and payload hashes protect simultaneous retries; signed version tokens reject stale forms and altered submissions.
- Restricted local writer roles and explicit grants, separate from read-only request roles and schema owners. Only the two isolated local Flask databases were prepared. The 39 business tables, 20 existing integrity functions and 51 existing triggers remain; two safety tables were added. No production/VPS/source database change.
- Owner/CSRF-protected bus registration/editing, initial driver assignment, five document categories, status/route history and activation/deactivation; routes add/list; drivers create with employment/edit. Financial accounts show/edit the existing starting balances. No unsupported route-deletion or employment-lifecycle feature is claimed.
- More -> Business Presets: rates, salaries, advance limit, reminders, reporting baseline and collection schedules. Thursday/Sunday defaults remain; full-week effective-dated replacements allow added/changed collection days, check coverage/transition ambiguity, retain history and block changes affecting recorded collections.
- Existing smart-cashing service now accepts explicit schedule rules; its dated preview was verified against real isolated bus activation history. Legacy Streamlit callers keep their previous default. Stage 3 financial recording must pass the dated Flask rule set for both preview and commit.
- Phone-first fleet tabs, forms, history/details, account and preset screens. Success redirects; missing/incorrect inputs retain drafts. Reason/actor data comes from validated input/authentication, not a posted identity. All application financial writes remain unimplemented/disabled until their stages pass.

### Verification evidence so far

- Initial Stage 2 web/foundation database run: **88 passed**. First command/workflow integration slice: **16 passed**.
- Expanded web/database/command/workflow run: **105 passed in 47.63s**, including a real fresh-Python-process retry, simultaneous same/different-key submissions, stale edits, audit reconciliation and commit-time rollback.
- Expanded targeted slice: **51 passed in 23.57s**, adding restricted-writer configuration, audit-insertion failure and historical active-day calculations.
- Stage 2 Edge phone/desktop journeys: **3 passed in 40.75s** at 375x667,390x844,1366x900, covering actual driver/bus saves, bus edits, account starting balances and schedule additions/history. Phone screenshot visually reviewed; fixed chrome does not overlap the scrollable form.
- Legacy regression rerun with workspace TEMP/TMP and read-only PGOPTIONS: **97 passed in 13.293s**; expected Streamlit missing-context warnings only. An earlier run's tests also passed but its sandbox temporary-directory cleanup warned; workspace TEMP/TMP resolved that environment issue.
- Further workflow coverage added for all preset kinds, forged posted actor, fresh blank forms, duplicate route, invalid bus details and date-level transition rejection. One test initially used a nonconsecutive weekly pattern and therefore hit the earlier correct validation rather than the intended transition assertion. Replaced only that fixture with a valid Friday/Sunday week that repeats already-covered work across a Friday changeover; the unchanged rejection assertion then passed (**1 passed in 1.51s**).
- Dependency audit rerun: **No known vulnerabilities found**. Ruff lint/format and package consistency pass. Interrupted pip-upgrade backup directories were moved from the active environment into ignored workspace storage, preserving them without deletion; package checks are warning-free.
- Local preview restarted with Stage 2 at http://127.0.0.1:5002; health returned 200. It remains loopback-only, not phone/public deployment.

### Final acceptance

- Full combined command: set workspace-local TEMP/TMP and SMARTFLEET_BROWSER_CHANNEL=msedge; `.venv-flask/Scripts/python.exe -m pytest tests/web tests/integration -q`: **132 passed in 176.34s**, including all nine phone/desktop HTTP/HTTPS browser journeys, isolated PostgreSQL writes, concurrency, real-process retry and rollback cases.
- Existing Streamlit suite: **97 passed in 13.293s** separately, excluding the live connection test and using read-only PGOPTIONS. No skipped test was counted as passed.
- Ruff check and format check: passed (22 Python files). pip check: no broken requirements. pip-audit: no known vulnerabilities. git diff --check: passed. Generated-secret scan across tracked/unignored files: zero matches, including the new writer passwords.
- Live preview owner login plus eight protected management/readiness endpoints: passed. HTTP health: 200. Local preview remains http://127.0.0.1:5002, bound only to this PC and using synthetic data.
- Verified master and streamlit-final both still point to **46c76438b53b12f7779b89d0e2e74f72c6eb0d4f**. No production activation, real financial data change or existing business schema alteration occurred.
- Implementation checkpoint hash will be recorded in the follow-up documentation checkpoint after commit; all work stays on migration/flask. Stage 3 is not started in this Stage 2 request.

## Remaining After Stage 2

3. Expenses, cashing/backfill, corrections and obligations.
4. Dashboard, finance, periods and reconciling Bus Accounts.
5. Payroll, business loans and owner money.
6. Servicing, reminders, reports/exports, backups, help and remaining parity.
7. Full verification, CI and deployment preparation; no production activation.

Do not advance past a failing or unavailable mandatory gate.
