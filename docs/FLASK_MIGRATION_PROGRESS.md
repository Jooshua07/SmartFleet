# Flask Migration Progress

Branch: migration/flask. Historical master/tag remain unchanged.

## Current Working Record - 17 October 2026

This is the living record of completed work, verification, decisions and next steps. Update it whenever behavior, configuration, preview data or the implementation plan changes. Earlier sections are chronological evidence, not necessarily the current preview state. The detailed architectural plan remains in [FLASK_MIGRATION_AUDIT_AND_PLAN.md](FLASK_MIGRATION_AUDIT_AND_PLAN.md); current operating instructions are in [FLASK_DEVELOPMENT.md](FLASK_DEVELOPMENT.md).

- Stages 1-6 and the approved cashing-invoice follow-up have passed acceptance. Stage 4 implementation checkpoint: 52b8211; documentation: f1df299. Stage 5/6 publication is recorded in the checkpoint sections below.
- Preview: http://127.0.0.1:5002, HTTP bound to this PC only. Following the owner's explicit request, smartfleet_flask_dev now contains an exact local copy of the real business records, not the earlier demo buses. It is a development snapshot, not the authoritative database and not a synchronization mechanism.
- Original local smartfleet and the VPS remain untouched. Automated tests continue to use only smartfleet_flask_test with synthetic fixtures. Never redirect tests to the copied preview or the original business database.
- Local preview login password was changed at the owner's request; credentials remain only in ignored local configuration/login files. Do not put the password, database dumps, business records, generated screenshots or fixture credentials into Git.
- Home Business performance red line now shows cumulative **Total Expenses**: all outgoing ledger payments within the selected chart dates, not operating costs alone. Internal account transfers are excluded consistently with the Home totals; bus operating-cost attribution remains unchanged.
- Stage 6 servicing/reminders, reports/exports, private backups/help and the approved all-bus cashing invoice are complete. Stage 7 platform verification/CI/deployment preparation remains pending; production activation and network/public preview require separate authorization. Existing finance-charge linkage limitations remain documented, not silently changed.

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

## Owner-Authorized Real-Data Preview and Local Access Update

Date: 17 October 2026. The owner requested recognizable real buses, drivers, cashing and business history in the development preview, plus a new local sign-in password and a continuously maintained working document.

- Read-only inspection identified the local smartfleet source: 3 buses, 3 drivers, 3 collections, 1 expense and 5 ledger entries. All 39 business tables were copied, including historical assignments/status, categories, settings, salaries, loans, maintenance, reminders and any existing audit/history records; absent records were not invented.
- Preflight verified matching columns and acyclic foreign keys. The source connection was loopback, repeatable-read and transaction-read-only. Neither source data/schema nor the VPS was changed. No application code or schema definition was changed for this request.
- Paused only the verified project-owned HTTP preview. Created and archive-listed the prior development database backup in ignored `.local/backups/preview-before-real-copy-20261017T052726Z.dump`. This verified archive readability, not a full restore rehearsal. An ignored receipt records row counts and SHA-256 fingerprints, without embedding the business rows in Git.
- Replaced only smartfleet_flask_dev contents inside one transaction, using foreign-key dependency order with existing triggers/constraints enabled. All 39 source/target table row counts and complete-row fingerprints matched before commit; deferred integrity checks passed. Sequence next values were preserved. Previous synthetic Flask command/audit rows were archived in the backup and removed from the refreshed preview so they cannot refer to reused business IDs.
- Post-commit read-only comparison verified both source and preview still match all 39 exported table fingerprints. The separate test database remains synthetic: 4 buses, 0 drivers and 0 ledger entries. No test was run against the original business database.
- Changed only the local development owner's password hash and ignored login note using the existing strong hash policy. Test credentials, production settings, trusted hosts, CSRF, authentication and loopback binding were not weakened. Restart invalidated earlier preview sessions.
- Verification: new-password sign-in succeeded; 12 protected HTTP page checks returned 200; phone-sized Edge browser sign-in/cards/charts and the 3 real cashing bus options passed, without horizontal overflow or JavaScript errors. Screenshot inspected. No verification step created or edited a business transaction.
- Verified the preview's October receipts, payments and balance reconcile to the copied source. Actual financial values remain in private local data/artifacts, not this published working record. Any future entry/edit made in this preview changes only its development copy; it is not automatically saved to the original business database. Recopying the original later would require preserving any preview-only work first.
- Data, backups, one-off refresh helper, screenshots and credentials remain ignored. Only progress/operating documentation is changed in tracked files; no commit or push is part of this data/configuration request. Stages 5-7 and public/phone hosting remain pending.

## Home Chart - Total Expenses Red Line

Date: 17 October 2026. Owner requested all expenses combined on the Business performance chart, rather than operating costs alone.

- Changed only the Flask timeline's red dataset to Total Expenses. It accumulates each outgoing financial ledger payment once across the selected chart dates, including repayments, salaries, drawings and fees. Internal TRANSFER movements remain excluded, matching the existing Total Expenses/Money Paid Out definition. Calculations remain Decimal until chart serialization.
- Existing operating-cost services, bus profitability attribution, green revenue/blue balance lines, cards, financial records and database schema remain unchanged. The legacy Streamlit code is untouched. Existing documentation edits for the earlier data-copy request were preserved.
- Tests using only smartfleet_flask_test: targeted reporting unit/PostgreSQL/phone-desktop browser suite **30 passed in 70.50s**. Includes Decimal fractions, all payment kinds, transfer/receipt exclusion, empty data, loan-versus-operating distinction and rendered red dataset. Separate follow-up **1 passed in 4.05s** verifies one month, three months and custom date totals while the current business balance stays unchanged.
- Ruff lint/format and git diff --check passed. No dependencies changed. Refreshed only the verified loopback HTTP preview. A read-only live preview request confirmed the red line reconciles to the copied data's total payments and is labelled Total Expenses. No database write, commit, push or production access was performed for this chart change.

## Stage 5 - Payroll, Loans, Owner Money and Requested UI Refinements

Status: **PASSED**. Work remains on migration/flask; prior uncommitted chart/documentation changes are preserved in this stage's checkpoint. Usage began at 56% five-hour / 26% weekly and reached 89% / 32% at final verification.

### Scope and implementation

- Owner/CSRF-protected payroll/advance entry, salary preview, employment/payment history, FIFO recovery, deductions, zero-net salary, corrections/reclassification and confirmed reversal. Existing proration, advance limits and monthly uniqueness remain authoritative. Business-loan listing/creation, business/owner-personal principal repayment and fee handling, history/corrections; owner funding/drawings/repayments and liability summary.
- New loan association links an unidentified repayment to a known loan under row locks and principal limits. It updates the relationship only, never creates another payment or changes the principal. The outer command stores actor/reason/before-after evidence atomically, as for all Stage 5 mutations. Unknown loan facts are not fabricated.
- Reuses the durable command key, shared transaction and reference-data lock for retries/stale forms/concurrency. New money snapshots include employment, payroll, owner/loan and correction records; legacy correction evidence is retained. Reads of related money history share repeatable-read snapshots.
- Isolated-only setup grants the new payroll/loan tables explicitly, correction_audit INSERT only, and owner_loans UPDATE(notes) solely to permit existing integrity-trigger row locking without opening identity/name/active edits. Initializes only missing Other/Owner Drawings categories. No business schema change, source/VPS connection or real financial entry.
- Expense entry now starts with General / Bus Specific; only Bus Specific shows/requires a bus. Ordinary expenses and cashing resolve active Airtel Money server-side and ignore forged account choices; Paid from/Paid into controls removed. Cashing labels show registration only; selected-bus sections have individual 6px bordered cards in the same single form.
- Driver editing is a button; bus status auto-submits its GET filter without Apply (noscript fallback retained). Recording shortcuts remain on Home and Finance General only, not Collections/Expenses/Balances. Account-management links are removed from More/Finance; Bus Accounts stays available. The old owner-only account compatibility URL/service remains for existing regression/financial compatibility, not as a restored navigation workflow.
- More follows the latest Streamlit Quick actions / Management grouping and includes recording, fleet, driver money, loans, owner money, Bus Accounts, presets and obligations. The Stage 6 servicing/reminders/reports/backups/help buttons are present but explicitly disabled until those workflows migrate; no dead active links or false parity claim.

### Diagnosis and safe recovery

- First fixture error was an explicit ID in an ALWAYS identity owner account; changed only the synthetic fixture to use the database-generated ID.
- A zero-net salary test exposed the existing service subtracting other deductions without creating required deduction allocations. Added exact deduction/allocation records and cancellation applied-status refresh; no constraint or trigger was changed. Initial unit/web regression: 122 passed. Legacy regression after the salary fix: 97 passed in 39.357s (read-only PGOPTIONS, live connection excluded).
- Confirmed owner-payment privilege failure by reproducing the required SELECT FOR UPDATE on owner_loans. Added the narrowly scoped local notes-column privilege above. Owner drawing reversal's joined FOR UPDATE unnecessarily locked expense_categories; narrowed it to FOR UPDATE OF e rather than granting category mutations.
- Loan principal and fees are separate existing records with no durable fee-to-repayment FK. Preserve the existing policy: principal reversal does not infer a fee association from free text/date or erase separately funded charges. UI says Reverse principal. Tests explicitly retain fees and resulting owner liability after a principal reversal. A safe unified finance-charge correction needs a separately reviewed exact-link design; no schema/policy invention here.

### Verification evidence

Focused PostgreSQL cases: **30 passed in 172.55s** after the diagnosed fixes, including a fresh-Python-process replay. Subsequent employment/proration and competing-repayment cases are included in the pending full suite rather than claimed in this earlier count. Expanded Edge phone/desktop journeys: **3 passed in 67.23s**, at 375x667,390x844,1366x900; screenshot reviewed. Final legacy regression after all service changes: **97 passed in 37.006s**, using read-only PGOPTIONS and excluding the live connection test.

Installed-environment pip-audit: **no known vulnerabilities**; pip check: no broken requirements; Ruff lint and format check passed (**37 files formatted**). Generated-secret scan: **zero matches** across 249 tracked/unignored candidates against 11 private values. Full combined acceptance and reviewed checkpoint remain pending. No dependencies changed.

### Final acceptance and remaining scope

- Full combined command, workspace TEMP/TMP and SMARTFLEET_BROWSER_CHANNEL=msedge: `.venv-flask/Scripts/python.exe -m pytest tests/web tests/integration -q`: **293 passed in 866.16s (14:26)**. No required case was skipped/disabled. Includes owner/CSRF checks on every money action/reversal; real process restart replay; simultaneous retries and competing repayments; stale forms; audit and deferred-commit rollback; deductions/zero-net salary/cancellation; historical reclassification and loan association without duplicate cash; proration/employment dates; server-authoritative Airtel and bus scope; existing chart/schedule/fleet/financial regressions and all phone/desktop journeys.
- Separate final Streamlit regression: **97 passed in 37.006s**, read-only PGOPTIONS and excluding only the unapproved live connection test. Earlier targeted counts overlap the full suite and are not additional distinct tests.
- Final Ruff lint and format check passed (37 files); package consistency, installed-environment advisory audit, whitespace check and private-value scan passed. No new dependency or schema migration. No test was weakened to bypass an integrity failure; newly clarified principal/fee assertions follow the existing separately stored records and verify fees remain intact.
- Verified project preview restarted only after executable/command/binding checks. New owner login and nine protected page requests passed; Home balance still reconciled with the copied business data. Browser screenshots reviewed; the preview remains http://127.0.0.1:5002, PC-only HTTP, with the existing local credentials. Automated writes were confined to smartfleet_flask_test; isolated setup changed only local writer permissions/reference categories. No original/VPS financial data or schema change.
- Protected master and peeled streamlit-final remain 46c76438b53b12f7779b89d0e2e74f72c6eb0d4f. Stage 5 is eligible for its reviewed commit/push on migration/flask only; exact implementation hash will be recorded after publication.
- Stop here. Stage 6 menu items remain disabled until their workflows migrate. The old account-management compatibility URL is not exposed in normal navigation. Separate finance-charge correction needs explicit linkage/policy review; principal reversals intentionally do not erase independent fees. Production activation, public/phone hosting and Stage 7 deployment work remain unauthorized/pending.

### Published Stage 5 Checkpoint

- Implementation **1620629bac220785f785d691a2e5712547495097**, successfully pushed to origin/migration/flask after all gates above passed. Includes the previously requested total-expense chart update and preserved preview-copy documentation, without publishing real records, local credentials or artifacts.
- Working tree was clean and synchronized after the implementation push. This documentation-only follow-up records its immutable hash. No required test, installer or audit session remains running; only the intentional local preview remains. Stage 6 has not started.

## Stage 6 and Approved Cashing Invoice Follow-Up

Date: 17 October 2026. Status: **PASSED**, including the final targeted regression below. Started from clean migration/flask at 3f98b46f9b5fe88a7099de37b53d1e4b2c4dcebc. Five-hour usage began at 0%; final verification check 42% (39% weekly). Protected baseline/tag and original/VPS database remain unchanged. Earlier interim notes below are chronological evidence.

- Stage 6 adds servicing entry/history/corrections and manual schedules, read-only reminder groups, consistent-snapshot full reports/reconciliation and protected CSV/XLSX downloads, searchable Flask help, setup warnings and private backups. Existing services are reused. Isolated setup grants maintenance INSERT/UPDATE and reader sequence SELECT, and adds only the missing Servicing category. No schema definition change or real financial entry.
- New private backup adapter never reads the old service's main-database settings or backup folder. It validates the isolated reader/database, serializes work using a database advisory lock, bounds subprocess time/archive size/private storage, publishes a completed archive/actor/hash manifest atomically, and guards downloads with owner authentication, UUID identity and integrity verification. No restore endpoint, automatic retention deletion or production setup. Archive checking is explicitly distinguished from an actual restore rehearsal.
- Early diagnostics: corrected operation callback signatures to match the existing zero-argument command wrapper and excluded transport tokens from durable financial intent. Narrowed database exception handling so an unexpected deferred integrity failure produces a rollback/error, never a false success. Backup diagnosis found duplicated connect_timeout kwargs, then Windows rejecting fsync on a read-only descriptor; fixed with merged connection settings and a writable private file descriptor. XML normalizes CR to LF in workbook strings; the formula-safety test now checks that documented normalization while preserving literal string type and the protective apostrophe.
- Focused Stage 6 PostgreSQL suite initially reached **23 passed in 53.82s**, including real archive creation/download/replay and isolated restoration. Expanded restore/restart and browser cases are still pending; this earlier count is not final acceptance. Focused support/security unit cases: **40 passed in 8.11s**. Full combined regression/security/browser gates remain pending.
- Owner supplied the approved Record Cashing redesign during Stage 6. Implementing it as a targeted new-entry follow-up, not a business-service rewrite: all eligible buses in Standard; only selected exceptions editable in Adjusted Buses; untouched buses retain standard expectations; explicit zero versus missing amount validation; conditional difference/responsibility controls; recomputed complete total and persisted receipt. Airtel, historical rates/activity/schedules, optional Sunday, obligations, atomic auditing and retry safety remain authoritative. Existing historical correction tools preserve direct/signed/unallocated records without silently changing stored financial history.
- Existing new-entry UI tests are being updated only where the owner explicitly replaced the workflow. Signed historical-difference assertions are retained through the existing correction editor, not removed. Legacy service tests remain unchanged. A new rate-change fixture initially attempted the active rate's existing start date; the service correctly rejected it. Changed the synthetic fixture to a later effective date, preserving the rule.
- No commit/push or Stage 7 authorization is implied by this interim record. Exact final commands, outcomes, limitations and checkpoint hashes will be recorded after all required checks pass.

### Changed File Register

- Cashing: smartfleet_web/cashing_entry.py, smartfleet_web/recording.py, smartfleet_web/static/cashing-entry.js, smartfleet_web/templates/complete_cashing.html and cashing_receipt.html. Legacy correction allocation/service logic is retained.
- Stage 6 application: smartfleet_web/operations.py, support.py, private_backups.py, help_content.py, __init__.py and views.py; services/validation_service.py adds an optional backup-age provider without changing legacy defaults.
- Stage 6 templates: servicing.html, servicing_form.html, reminders.html, reports.html, backups.html and help.html. Navigation/shortcuts: more.html, bus_detail.html and dashboard.html. Shared styling/servicing total: static/app.css and app.js.
- Isolated permissions/tooling: scripts/setup_flask_stage6.py and pyproject.toml. No requirements or SQL migration file change.
- New integration tests: test_complete_cashing.py, test_complete_cashing_browser.py, test_stage6.py and test_stage6_browser.py. Existing test_stage3.py and Stage 3/5 browser journeys adapt only the approved new-entry behavior while retaining correction, Sunday, obligation, rollback and retry assertions. integration/conftest.py snapshots/cleans synthetic servicing/reminder rows in FK order.
- Web unit/security tests: test_cashing_invoice_unit.py, test_operations_security.py and test_recording_security.py. web/conftest.py stubs only setup warnings for unit tests without a database; actual setup checks still run against isolated PostgreSQL.
- Working documents: FLASK_MIGRATION_AUDIT_AND_PLAN.md, FLASK_DEVELOPMENT.md and this progress record. Generated dumps, diagnostics, screenshots, local verification helpers and credentials remain ignored, not part of the checkpoint.

### Broad Acceptance Results

- Full Flask gate, workspace TEMP/TMP and SMARTFLEET_BROWSER_CHANNEL=msedge: `.venv-flask/Scripts/python.exe -m pytest tests/web tests/integration -q`: **399 passed in 676.24s (11:16)**. No required case skipped or disabled. Initial full-suite collection found a duplicate unit/integration module basename; renamed only the unit module to test_cashing_invoice_unit.py and reran the complete gate successfully.
- Includes all-bus Standard invoices, single/multiple exceptions, unedited/reset amounts, missing/invalid values, zero receipts and obligations, responsibility/classification, effective rates/schedules, historical activity, Airtel enforcement, receipt refresh, durable restart replay, competing/double submissions, stale forms, audit-insert and deferred-commit rollback. Existing fleet, expenses, cashing corrections/deletions, salary/loans/owner money, schedules, charts, reports and authorization/CSRF cases remain active.
- Stage 6 restore test creates real synthetic financial history, makes a custom archive using the restricted reader, verifies/downloads/replays it after a new app/session, changes only synthetic rows, then actually restores only smartfleet_flask_test with pg_restore --clean --if-exists --single-transaction --exit-on-error. All 41 table row counts/full-row fingerprints and trigger counts match before/after; tampered archives and invalid identities cannot download. No restore endpoint or dev/original/VPS restore exists.
- Report tests reconcile revenue/payments/negative closing balance and financing exclusions, round-trip CSV/XLSX dates/numbers, preserve formula-like content as literal cells, exclude out-of-period entries and reject resource-excessive requests. Servicing proves one linked expense/payment, paid/zero/paid corrections, older-event scheduling, duplicate/stale/restart/rollback behavior and actor-attributed before/after evidence.
- Browser coverage includes 375x667, 390x844 and 1366x900. Screenshots inspected. The initial new header assertion incorrectly required CSS position:fixed; the established app pins header/nav using a fixed-height flex shell and scrolling main. Replaced that implementation-specific assertion with actual bounding-box checks before/after scrolling, retaining the user's stationary-banner requirement without changing the working shell. Targeted new invoice journeys passed 3 cases; other targeted Stage 6/Stage 3/Stage 5 journeys passed 9 in 122.17s. These overlap the 399-test full gate, not additional unique tests.
- Separate legacy `.venv` unittest discovery with read-only PGOPTIONS, excluding the unapproved live connection test: **97 passed in 36.496s**; expected Streamlit bare-context warnings only. No legacy test changed.
- Ruff lint passed; format check passed for 49 files. pip check: no broken requirements. Installed-environment pip-audit with private cache/strict mode: **no known vulnerabilities**. No dependency change. Private-value scan: zero matches across 270 tracked/unignored candidates against 11 actual local private values. Git whitespace check passed; only normal Windows line-ending notices.
- Final review then found a client preview discrepancy for valid scientific numeric notation (for example a synthetic amount entered as 1e3). Updated only the client preview parser to match the server's Decimal precision/limit semantics and added a PostgreSQL case plus phone/desktop browser coverage. Also corrected one Help backfill sentence to refer to reviewing the invoice, not selecting buses. The post-review targeted regression is recorded below; the earlier 399-test count applies to the broad run immediately before these narrow display/help refinements.

### Final Verification and Limits

- Post-review command: `.venv-flask/Scripts/python.exe -m pytest tests/web/test_cashing_invoice_unit.py tests/web/test_operations_security.py tests/integration/test_complete_cashing.py tests/integration/test_stage3.py tests/integration/test_complete_cashing_browser.py -q`, with workspace TEMP/TMP and Edge: **105 passed in 148.50s (2:28)**. Includes the new actual 1e3 receipt and all three browser sizes exercising its displayed total. Overlaps the broad suite; do not add these counts as unique tests.
- Final Ruff lint and 49-file format check passed; whitespace and private-value scan passed again. No dependency or SQL migration change. Existing 97-test legacy result remains applicable; post-review edits touched only new cashing display/help and its tests, not legacy services.
- Restarted only the verified project-owned Python process listening at 127.0.0.1:5002. New owner login, 20 protected page checks and a workbook download passed. Read-only before/after fingerprints of all 41 preview tables were identical. No preview financial entry was created/edited by verification. Confirmed the refreshed listener remains exactly 127.0.0.1:5002, not a LAN/public listener; existing local credentials and strong hash policy unchanged.
- Preview: http://127.0.0.1:5002. The database remains the owner's recognizable development copy, not an authoritative/synchronized source. No recopy, reset, original/VPS access, deployment or public phone link. Backup age/setup warnings refer only to this development copy's private archive store.
- Mandatory Stage 6 and cashing-follow-up gates passed. No required test, audit or installer session remains running; only the intentional preview remains. Implementation is eligible for a reviewed secret-free migration/flask commit/push; the immutable hash will be recorded after publication. master and peeled streamlit-final still equal 46c76438b53b12f7779b89d0e2e74f72c6eb0d4f; annotated tag object remains b82c40b383a74d6d20c49d53c6208d37fff66f44.
- Stop after Stage 6. Stage 7 clean Ubuntu 24.04/Python 3.12/PostgreSQL 18.6 release verification, CI/deployment approval flow and authorized hosting work remain pending. The Windows/local acceptance is not a claim of production deployment readiness. Off-host encrypted backups/retention/recovery objectives and a production background backup runner still need an operational decision. Existing independent principal/fee correction linkage and larger-than-5,000-row command evidence limits are not silently redesigned in this stage.

### Published Stage 6 and Cashing Checkpoint

- Implementation **fbf328bdccf907f7604f997c6100ae869a6283f2**, successfully pushed to origin/migration/flask. Reviewed checkpoint: 40 files, 2,648 insertions and 50 deletions, including documentation and the approved existing-test workflow adaptations. No real records, credentials, dumps, browser artifacts, dependency snapshot or SQL migration included.
- Publication followed the 399-test full gate, the 105-test final focused gate, 97 legacy tests, real synthetic restore/fingerprints, phone/desktop screenshots, package/security/lint checks and read-only live-preview verification described above. Counts overlap where explicitly stated; no skipped/blocked gate was relabelled as passing.
- Working tree was clean and synchronized after the implementation push. This documentation-only follow-up records its immutable hash without amending history. Only migration/flask was pushed; master and streamlit-final remain protected/unchanged. Preview remains http://127.0.0.1:5002, with no required background verification session left running and no Stage 7 or production deployment started.
