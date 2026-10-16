# Environment and Dependency Setup Guide

Date: 2026-10-15. Recommendations only. Nothing was installed or reconfigured.

## 1. Verified current environment

- Local Windows workspace, PostgreSQL 18.6.
- Python 3.14.0; Streamlit 1.65.0; psycopg/psycopg-binary 3.3.6.
- pandas 3.0.6; openpyxl 3.1.5; uvicorn 0.54.0; starlette 1.7.0.
- FastAPI, Flet, SQLAlchemy and Alembic were not installed in the inspected project environment.
- requirements.txt pins 41 packages, including direct and transitive dependencies. It is a legacy environment snapshot, not a designed backend/mobile split.
- .streamlit/config.toml configures theme, minimal toolbar, polling file watcher and run-on-save. It does not configure an authenticated production API.

Keep the existing .venv and requirements intact during migration. Do not copy all legacy pins into the new backend and force a modern FastAPI onto an unrelated Starlette version.

## 2. Python and separate environments

Use separate backend and Flet environments; retain the old Streamlit environment for parity/recovery. They may eventually use different dependency versions even if both use the same Python minor.

A conservative starting choice is the latest supported Python 3.13 patch available in the chosen deployment/build environments, subject to a clean install/build/test check. This is a risk-reduction recommendation, not a finding that 3.14 is unsupported. Current Flet publishing documentation lists 3.14, 3.13 and 3.12 bundled runtimes. Explicitly choose the intended runtime instead of relying on changing build defaults. [Flet publishing reference](https://flet.dev/docs/publish/)

Do not change the operating app's Python or PostgreSQL major version as part of the first bus API slice. Test the new environment against an isolated PostgreSQL version matching production before considering an upgrade.

## 3. Minimal target dependency sets

| Environment | Direct dependencies to consider | Why |
|---|---|---|
| Backend initial read-only slice | fastapi; uvicorn; psycopg with suitable binary/runtime installation; python-dotenv for local development | REST, server, existing PostgreSQL queries, local settings |
| Backend reports, when migrated | openpyxl; pandas only if retained report/dataframe code needs it | XLSX and existing report table builders |
| Backend security, when implemented | one maintained password-hash implementation and one token/session approach; FastAPI/Pydantic validation | Do not hand-roll cryptography; exact packages depend on approved session policy |
| Backend uploads, when implemented | python-multipart only if multipart endpoints are used | No reason to add upload dependencies before the feature |
| Backend pooling, if justified | psycopg pool support | Bounded request connections; configure by measured workers/load |
| Flet client | flet; one HTTP client (requests for initial native POC, or httpx if asynchronous API is chosen) | UI plus HTTPS only |
| Tests | existing unittest; httpx if FastAPI TestClient tests require it; device/build tooling separately | Avoid replacing working tests merely to adopt another runner |
| Optional later persistence tooling | SQLAlchemy/Alembic only after separate review | Not required to reuse psycopg or to build FastAPI |

Pydantic arrives through FastAPI and should be explicitly managed if directly imported for contracts. Select a mutually compatible release set, resolve in a fresh environment, run checks, then record/pin that set. These are not tested target-version recommendations: target packages have not been installed.

## 4. Classification of every currently pinned package

Backend/client labels below mean retain only if required by direct code or the dependency resolver. Do not manually transplant transitive pins.

| Existing packages | Target decision |
|---|---|
| psycopg, psycopg-binary | Backend only; preserve PostgreSQL access. Validate binary packaging on the VPS. Never bundle in mobile. |
| python-dotenv | Local backend configuration only; production process secrets preferred. |
| openpyxl | Backend reports. No mobile requirement. |
| pandas | Backend only if current report transformations remain. Bus/domain logic should not require it. |
| tzdata | Retain where the platform lacks timezone data; needed for correct Lusaka/date handling, especially Windows. |
| requests | One possible native client HTTP choice. Do not keep both requests and httpx without a reason. |
| uvicorn | Backend; select compatible version with new dependency set. |
| starlette, anyio, typing_extensions | Backend framework dependencies, resolved with FastAPI rather than copied pins. |
| h11, httptools, websockets | Conditional server/client stack dependencies; let selected server/Flet packages determine need. No standalone business need. |
| python-multipart | Backend optional for upload/form endpoints; JSON-only POC does not need it. |
| certifi, charset-normalizer, idna, urllib3 | HTTP-stack transitive dependencies as resolved; not hand-selected business dependencies. |
| click, packaging | Tooling/framework dependencies as required. |
| numpy, python-dateutil, six | Keep only if retained pandas/report dependency chain requires them. Prefer stdlib date/Decimal for domain rules. |
| pillow | Retain only for proven image/report/client needs; no mandatory bus/API requirement. |
| Jinja2, MarkupSafe, itsdangerous | No direct need in the proposed JSON API/native client; retain only if chosen framework/session/template feature requires them. |
| attrs, jsonschema, jsonschema-specifications, referencing, rpds-py, narwhals | Primarily chart/schema dependency chain in current environment; no direct domain reuse requirement. |
| streamlit | Legacy environment only; remove from new backend/client dependency lists. |
| altair | Legacy chart renderer; replace chart UI in Flet, preserve data/axis tests. |
| pydeck | Legacy UI dependency; no planned mobile map requirement. |
| pyarrow | Legacy dataframe/Streamlit stack; not needed just to transmit JSON bus records. |
| protobuf | Legacy/framework transitive dependency; no independent domain reason to carry it over. |
| toml | Legacy tooling; use standard tomllib for new read-only TOML configuration where suitable. |
| watchdog | Legacy development watcher; not a production domain dependency. |

This table covers all 41 requirement entries. A package may reappear transitively in a new environment; exclusion here is not a request to uninstall it from the working app.

## 5. Future setup procedure, not executed

After authorization to implement:
1. Verify Python interpreter and build target versions.
2. Create a backend environment and a client environment without altering .venv.
3. Install only the direct dependencies required for the approved slice.
4. Resolve and record compatible versions; run dependency consistency/security checks.
5. Run existing reusable tests under the backend environment against isolated/read-only targets.
6. Run the Flet POC on desktop, then a packaged Android test; validate required mobile wheels before expanding dependencies.
7. Establish repeatable backend and client lock/build procedures and CI secrets before production.

Illustrative PowerShell commands only:

```powershell
py -3.13 -m venv .venv-api
py -3.13 -m venv .venv-client
.\.venv-api\Scripts\python.exe -m pip install fastapi uvicorn "psycopg[binary]" python-dotenv
.\.venv-client\Scripts\python.exe -m pip install flet requests
```

These unpinned install commands are for a future disposable compatibility trial, not a production lockfile or a command to execute during this audit. macOS/Linux use their platform interpreter and environment paths.

## 6. Server/client configuration and secrets

### Backend only
- Existing DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD; validate presence/type and avoid unsafe defaults.
- Add explicit environment identifier, allowed origins if browser use, connection/request timeouts, logging level, token/session settings and secret sources as the architecture is implemented.
- PostgreSQL TLS/CA settings must be explicit for remote DB connections; local/private deployment still requires restricted network access.
- Separate runtime, migration and backup credentials; no superuser runtime role.
- Secure private upload directory/object-store settings, file size policy, backup destination/retention and encryption.
- Do not log DSNs/passwords/tokens, raw financial payloads or customer documents.

### Flet client
- API base URL and non-secret build metadata only.
- No DB_HOST/DB_PASSWORD, database connection, backup credentials or server signing secret.
- Runtime API token storage must use a verified platform-secure mechanism appropriate to the chosen session design.
- Development desktop loopback URL is not a phone-access URL. Production uses the HTTPS domain.

.env is not tracked in the current repository. Review .gitignore and all future secret files, including Streamlit secrets if introduced, before adding them. Ignore rules do not erase credentials already committed; this audit did not find or claim such a leak. Review access to tracked operational CSV/XLSX files.

## 7. Mobile build prerequisites

Flet host tooling requires a supported Python environment; use its installation checks in the isolated client environment. [Flet installation](https://flet.dev/docs/getting-started/installation/)

Android packaging needs the supported JDK/Android SDK toolchain. Plan for tool downloads, signing key custody, device testing and a chosen distribution path before telling users they can install the app. No Android tools were installed in this audit. [Flet Android publishing](https://flet.dev/docs/publish/android/)

iOS needs a Mac build/signing environment; see the dedicated constraints in [Target Architecture](04_fastapi_flet_target_architecture.md). Native binary dependency support must be verified per platform, rather than inferred from a successful Windows import.

## 8. VPS checklist

Choose a Python-supported OS/provider only after estimating active users, DB size, reports, uploads and backup retention. Define domain/DNS, reverse-proxy TLS, firewall, private PostgreSQL access, supervised API process, least-privileged service user, logs/monitoring, time sync, disk alerts and encrypted off-host backups.

Match PostgreSQL dump/restore tools to the chosen server compatibility requirements; the current service discovers Windows-local tools, which needs adaptation for Linux. Verify an actual restore on another database. Keep the old app and real DB private until Gate B in the migration plan passes.

## 9. Documentation and outstanding decisions

Create and maintain, during implementation: exact supported environments, dependency locks, API/OpenAPI contracts, role matrix, money/date/baseline definitions, schema manifest/migration ledger, test-target safety rules, deployment/runbook, backup restore/cutover procedure and mobile signing/distribution guide.

Still undecided: host/domain, user count and permissions, iOS distribution access, offline read expectations, full document upload policy, transfer UI need, unidentified loan association behavior and historical correction policy. Do not let environment setup implicitly decide these business requirements.

