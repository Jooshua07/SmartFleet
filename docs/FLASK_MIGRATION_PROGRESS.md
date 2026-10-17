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
- Implementation checkpoint: **1774908204852226db358ed88b600a710c39b7bf**, successfully pushed to origin/migration/flask. This follow-up documentation checkpoint records that immutable implementation hash. Stage 3 is not started in this Stage 2 request.

## Stage 3 - Financial recording

Status: **PASSED**. Resumed from clean migration/flask at 69d144f; the interrupted scheduled start had made no application changes. Usage at scheduled start was 0% of the five-hour window and 18% weekly.

- Added owner/CSRF-protected expense recording, paginated history, editing and confirmed deletion with vendor/reference, existing category restrictions and servicing-linked guards. Existing services and financial effects are reused inside durable commands.
- Added one cashing form with multi-select buses, Standard/Adjust buses, equal/separate amounts, worked-day adjustments, optional Sunday amounts, classifications, confirmed obligations and historical backfill. Selected-date rules and historical activation are recomputed inside the command transaction; direct historical collections use their existing editor semantics. Success clears financial inputs while retaining the cashing date.
- Added collection history/correction/deletion and obligation partial/full settlements/history. Existing Airtel-only destinations, OTHER-IN settlement treatment, obligation correction locks, allocation provenance and signed unallocated differences are retained.
- Version-controlled isolated setup extends writer grants only to recording tables in smartfleet_flask_dev/test and initializes three synthetic operating categories. No production/source access or business schema changes. Audit/command tables remain append-only to the runtime writer.
- Significant diagnosis: a concurrency test exposed that cashing included CSRF transport tokens in its intent hash. Removed transport tokens from financial intent, retaining CSRF validation and owner authentication; exact same-key retries across owner sessions then passed. Existing collection mode/receipt/unallocated values are retained on GET, avoiding a silent Standard-to-Adjusted correction. Historical labels now resolve driver assignments on the collection date; Sunday-only historical activity is eligible without inventing normal worked days.
- Initial integration slice: 16 cases passed and one concurrency case failed before the intent-hash fix; focused concurrency rerun: 1 passed. A clearing assertion incorrectly searched the whole HTML for 'selected' and matched label text; scoped it to the actual bus-select options, retaining the no-selected-bus requirement. No valid assertion was weakened.
- Stage 3 browser journeys: **3 passed in 65.43s**, at 375x667,390x844,1366x900. Actual multiple-bus/equal-amount recording, clearing, expense/reference entry and confirmed deletion exercised. Screenshot inspected. Focused financial authorization/CSRF tests: **13 passed in 10.03s**.
- Legacy Streamlit regressions with workspace TEMP/TMP and read-only PGOPTIONS: **97 passed in 45.618s**, excluding the live connection test. Dependency audit: no known vulnerabilities. Package consistency and Ruff pass.
- Full combined acceptance: **156 passed in 510.29s**, running tests/web and tests/integration with workspace TEMP/TMP and Edge. Subsequently added authorization cases passed separately (**13 passed**); final signed-difference, commit-failure and audit-insertion-failure cases passed separately (**4 passed,21 deselected in 24.80s**). Deselected cases were already covered by the combined run and are not counted as new passes. These are separate runs, not a claimed single 173-case run.
- Ruff check/format, package consistency, dependency audit, whitespace checks and generated-secret review passed. All new browser journeys passed; legacy 97-case regression passed. Commit-time and audit-insertion failures left zero financial, command and audit rows. Same receipt replayed after a new Python process produced one ledger receipt only.
- Stage 3 is eligible for its reviewed checkpoint/push. Exact implementation SHA will be recorded in Stage 4's progress entry after the checkpoint exists. Stage 4 implementation has not begun before this acceptance gate.

## Remaining After Stage 3

4. Dashboard, finance, periods and reconciling Bus Accounts.
5. Payroll, business loans and owner money.
6. Servicing, reminders, reports/exports, backups, help and remaining parity.
7. Full verification, CI and deployment preparation; no production activation.

Do not advance past a failing or unavailable mandatory gate.

## Stage 4 - Dashboard, Finance and Bus Accounts

Stage 3 implementation checkpoint: **3ba7031e46de8f18b8023278c3144f108aa67959**, committed and successfully pushed before Stage 4 began.

### Implemented

- Home's baseline-to-today Total Revenue, Total Expenses and Business Balance cards, quick recording links, fleet counts, servicing alerts/reminders, recent activity, performance timeline and bus comparison. Home reporting controls remain in the scrolling body; header and four main navigation destinations remain fixed.
- Fixed Finance General/Collections/Expenses/Balances tabs, paginated histories and correction links. Business Balance Now is above and independent of the selected-period Money Received/Money Paid Out section. Opening/closing balances remain in reusable report services for the later Reports workflow.
- Calendar one-month/three-month selectors and Custom all-time/six-month/date ranges; malformed/reversed/overlong ranges reject safely. Explicit future custom reporting does not alter balances labelled current. All sections share a read-only repeatable-read transaction; no cross-request financial caching.
- Reconciled Bus Accounts summary, monthly detail, category costs and recent activity, using the existing operating-category exclusions, historical multi-bus allocations and uniquely attributable earned salaries. General/unattributed salary stays shared; financing and loan repayments are not bus operating costs. Existing Streamlit entry points remain operational.
- Actual-currency grouped bars start independently at zero; negative business balance remains visible on the timeline. Locally vendored MIT Chart.js 4.5.1 avoids a frontend framework/build/runtime or remote chart dependency. Official asset source/version/license/hash is recorded in FLASK_DEVELOPMENT.md. Numeric conversion to float is presentation-only; services/SQL retain Decimal/numeric calculations.
- Individual account balances now accept an optional as-of date; Flask uses today while legacy default behavior is preserved. Consolidated reporting retains the October zero clean slate and does not add account starting balances.
- Removed only unused Flask Home/Finance shell templates after verifying no references; no Streamlit page or production data/schema was removed or changed.

### Verification evidence

- Initial PostgreSQL reporting cases: **8 passed in 33.08s**, covering October/November/December carry-forward, three-month aggregation, future exclusion, account-opening exclusion, loan/transfer exclusion, salary/shared/multi-bus reconciliation and read-only rendering.
- Initial Stage 4 real Edge browser journeys: **3 passed in 41.73s**, at 375x667, 390x844 and 1366x900. Asserted actual chart data, independent zero-baseline pixels, larger expense bar, negative line range, nonblank canvas, fixed header/tabs/navigation, custom dates and invariant current balance. Phone screenshot visually reviewed. Additional Bus Accounts navigation and account-as-of cases are being checked before final acceptance.
- Installed-environment dependency audit: **No known vulnerabilities found**. Package consistency passed. Generated-secret scan: **zero matches** across 241 tracked/unignored candidates against 11 private values. Ruff lint passed; a newly expanded test parametrization required formatting and was formatted without changing assertions.
- Usage during verification: 43% five-hour, 24% weekly. Full combined regression and final checkpoint are not claimed until results below are complete.

### Final acceptance

Status: **PASSED**.

- Full combined command with workspace-local TEMP/TMP and SMARTFLEET_BROWSER_CHANNEL=msedge: `.venv-flask/Scripts/python.exe -m pytest tests/web tests/integration -q`: **194 passed in 483.95s**. Includes the Stage 1-3 database/authorization/CSRF/concurrency/restart/retry/rollback gates and all existing browser journeys plus Stage 4 reporting.
- Final follow-up after adding account-as-of, future-only all-time, Bus Accounts authorization and actual summary-to-detail browser navigation: `.venv-flask/Scripts/python.exe -m pytest tests/web tests/integration/test_stage4.py tests/integration/test_stage4_browser.py -q`: **127 passed in 90.10s**. These overlap the combined run; they are not 127 additional distinct tests. All final changed behaviors were exercised. No required case was skipped, deleted, disabled or weakened.
- Legacy Streamlit unittest/AppTest regression, workspace TEMP/TMP and read-only PGOPTIONS, excluding only the unapproved live connection test: **97 passed in 26.606s**. Expected missing Streamlit context warnings only.
- Ruff check passed; Ruff format check: **32 files already formatted**. pip check: no broken requirements. Installed Python dependency audit: no known vulnerabilities. Separate OSV package/version lookup for npm/chart.js 4.5.1: **zero known advisories**; official asset SHA-256 reverified. Browser/data/pixel checks and phone/desktop screenshots passed review. The vendor advisory check is separate from pip-audit, not implied by it.
- Restarted only the verified project-owned process for port 5002 after checking its executable path and full launcher command. Listener remains **127.0.0.1:5002**. Live HTTP owner login, health and **13 protected page requests returned 200**, including Home, all four Finance sections, Bus Accounts, recording, accounts and obligations. No financial write was made by that smoke test.
- master and peeled streamlit-final remain **46c76438b53b12f7779b89d0e2e74f72c6eb0d4f**. Only migration/flask changes are eligible for the Stage 4 checkpoint. No production/VPS/source database access or change; test writes remained isolated/synthetic. Exact implementation checkpoint will be recorded after the commit exists.

### Remaining scope and limitations

- Stop after this stage. Stage 5: payroll, business loans and owner-money screens. Stage 6: servicing, reminders, reports/exports, isolated backups, help and remaining parity. Stage 7: full parity verification, CI and deployment preparation, not production activation.
- Home alerts/reminders read the existing services; their editing workflows are not claimed as migrated. Report exports and opening/closing-balance report screens remain Stage 6. No real financial history has been imported into this private preview.
- Single-process owner sessions, bounded command snapshots and production isolation restrictions documented above remain. No production-ready or full-parity claim is made. The preview link is PC-only HTTP, not a phone/public link.

### Published checkpoint

- Stage 4 implementation: **52b82118a8ccbee9791f7a2a3f4165d6be96dc27**, successfully pushed to origin/migration/flask. Stage 3 remains preserved at **3ba7031e46de8f18b8023278c3144f108aa67959**. This documentation-only follow-up records the immutable implementation hash.
- Working tree was clean and synchronized after the implementation push. Final usage check: **46% five-hour / 25% weekly**. No required test/security/tool session remains running; only the intentional loopback preview remains available. Stage 5 has not started.
