# FastAPI + Flet Target Architecture

Date: 2026-10-15. Proposed design, not implemented or package-tested in this audit.

## 1. Recommended deployment

```text
Android / iOS native Flet app
  UI state + HTTPS client; no DB credentials
                  |
                HTTPS
                  |
Domain / TLS reverse proxy / request limits
                  |
FastAPI backend on Python VPS
  authenticated routes -> command/query services -> psycopg
                  |
          private PostgreSQL
  existing checks + FKs + triggers + financial functions

Private document storage and encrypted off-host backups
are accessible through authorized backend operations only.
```

Keep Streamlit available during migration, but use only one authorized financial writer at cutover. A GitHub repository is source distribution, not the live database, API host or backup destination.

### Android/iOS feasibility and limits
Flet can package standalone mobile applications containing Python and Flutter. Windows can build Android; native iOS packaging requires macOS. Mobile dependencies need compatible target-platform wheels. The native app talks to FastAPI directly; a persistent Flet server is not required for this native-client model. [Flet publishing](https://flet.dev/docs/publish/)

iOS release requires a Mac build environment, Xcode, signing/provisioning and appropriate Apple distribution access; a Linux VPS cannot build/sign the native iOS app by itself. [Flet iOS publishing](https://flet.dev/docs/publish/ios/)

For an earlier browser pilot, retain Streamlit or design a Flet web deployment separately. Server-rendered/dynamic Flet web has its own session/connection deployment needs; it is not identical to the native REST client. Confirm browser-specific networking, CORS, storage and reconnect behavior before choosing web as the primary product.

## 2. Backend boundaries

Proposed packages, not folders created by this audit:
- api/routes: authentication, parsing, permission checks, command/query dispatch, HTTP errors.
- schemas: explicit request/response contracts; no direct serialization of arbitrary DB rows.
- application: use cases, transaction ownership, idempotency, audit actor and coordination.
- domain: money/date/allocation/payroll/loan rules without Streamlit or HTTP dependencies.
- persistence: existing parameterized PostgreSQL queries, adapted to accept a connection/unit of work.
- infrastructure: settings, private storage, backup job, logs, health monitoring.

Initially keep psycopg, not a mandatory ORM. Blocking psycopg services can be used in regular def FastAPI routes; do not call them directly inside async def routes and block the event loop. [FastAPI async guidance](https://fastapi.tiangolo.com/async/)

Each financial command uses one connection/transaction and returns only after commit. Query services producing a single report share a coherent snapshot. Bound concurrency/connection counts for all server workers. Start with measured needs, not a speculative distributed cache or queue.

## 3. Authentication and permissions

New capability required; the existing app has no implemented user identity model.

Suggested roles for owner approval:
| Role | Allowed by default |
|---|---|
| Owner/admin | All business screens; presets, opening balances, users, authorized corrections and backups |
| Recorder | Read fleet/reference data; record approved cashing/expenses/servicing; no silent historical deletion |
| Read-only viewer | Approved dashboards/reports; no writes, configuration or backup downloads |

Payroll/loans/owner funding and historical corrections should have explicit permissions, not be automatically granted to every recorder. Restrict records and exports on the server. No multi-tenant business isolation is assumed; if required later, design tenant scoping and PostgreSQL policies deliberately.

Use established password hashing and token/session libraries. Define token expiry, refresh/revocation, logout, password reset, failed-login throttling and device-loss response. Never put DB credentials or signing keys in Flet. Choose device secure storage only after confirming platform support; do not put long-lived credentials in plain preferences/logs. [FastAPI security reference](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)

Native HTTP clients do not gain security from CORS. Browser origins require a narrow CORS policy; cookie-based sessions additionally require a deliberate CSRF strategy.

## 4. Request, money and error contracts

- Version prefix /api/v1; ISO dates, Africa/Lusaka business-date policy.
- Money: explicit ZMW, decimal strings such as "4000.00", server-side Decimal, scale/range checked against each column.
- IDs are server identities; clients cannot supply derived balances, generated costs, ledger IDs, actor IDs or allocation provenance without validation.
- Reads support bounded pagination/search and stable ordering. List DTOs should not expose private notes/chassis/personal data unnecessarily.
- Domain failures produce stable error codes plus safe field messages: 401 unauthenticated, 403 forbidden, 404 missing, 409 stale/conflicting command, 422 invalid request.
- DB exceptions are logged privately with request IDs; do not return raw SQL, connection settings or tracebacks.
- Optimistic version checks or equivalent row locking protect edits from stale screens. Avoid introducing a version column until a reviewed migration is approved.
- Audit records carry actor, reason, target, before/after snapshot, command/request ID and timestamp; protect audit mutation rights.

## 5. Safe mobile financial commands

For expenses, cashing, obligation settlement, payroll, advances, debt payments and corrections:
1. Client generates a command ID and retains the same ID while outcome is uncertain.
2. Backend checks actor/permission and validates canonical payload.
3. In one transaction, reserve the command key, lock the relevant business rows, apply existing service logic and store the committed result.
4. Same key + same payload returns the original result; same key + different payload conflicts.
5. Client clears the form only after confirmed success; timeout leaves an explicit unresolved state with safe status/retry.

A disabled Submit button improves UX but is not durable duplicate prevention. Do not auto-queue offline financial writes in the first release. Permit clearly dated cached reads if wanted; require connection for recording. Never announce "saved" before server confirmation.

## 6. Screens and existing behavior to preserve

- Fixed SmartFleet header/bottom navigation; Home reporting controls remain in the body as requested.
- Home: broad business overview with date scope explicit; chart figures in actual currency units, grouped bars independently rising from zero.
- Finance: Business Balance Now outside the selector; period Money Received/Money Paid Out; opening/closing balances in Reports.
- Cashing: one paid-into/bus-selection form, driver-labelled bus options, per-bus amounts when necessary, coverage/variance/obligation details, successful reset. Preserve current smart-cashing rules only after confirming them against the desired workflow.
- Expenses: grouped categories, bus/general/shared scope, allocation, paid-to/reference, payment source; no duplicate operating expense for loan/drawing/advance.
- Buses/routes/drivers/history; Bus Accounts with reconciling summary/detail.
- Payroll/advances, loans, owner money and servicing remain separate workflows with their existing accounting meanings.
- Reports/exports, reminders, presets, help and owner-only backup controls.

Rebuild widgets/charts in Flet; reuse tested calculations and server queries. Do not ship pandas/Altair and a database connection to phones just to reuse a Streamlit chart.

## 7. Uploads, reports and backups

Document metadata exists, but binary upload/storage is new work. Define MIME/size validation, authorization, safe opaque filenames, private storage, checksum, malware handling appropriate to risk, backup coverage and authorized download. Never trust client file paths. Add file-reference schema only through reviewed migrations.

Reports calculate on the server from a consistent snapshot, not by summing paginated client rows. Preserve CSV formula-injection sanitization in report_export_service. Native file sharing/downloading must be device-tested. Export and backup are different: an XLSX report cannot restore relational integrity.

Backups are scheduled server operations using restricted credentials and PostgreSQL tools; owner UI can request/list authorized results. Do not hand raw backup paths or shell arguments to clients. Large backup jobs may later need a worker, but no queue package is required for the bus prototype.

## 8. Operations and future growth

Run the backend under a supervised service with TLS termination, automatic restart, health checks, private logs, resource limits, and explicit secrets. Never enable development reload publicly. Monitor DB connections, error rate, latency, disk/backups and failed logins. [FastAPI deployment concepts](https://fastapi.tiangolo.com/deployment/concepts/)

Keep PostgreSQL off the public internet when colocated; if managed/remote, use private networking and verified TLS. Determine VPS location, OS, memory, restore objectives, domain/DNS, file storage and expected concurrent users before sizing. No host/provider or cost is assumed.

Future additions should extend domain use cases and contracts, not bypass them with table-level generic CRUD. If more than one business is introduced, revisit tenancy before sharing credentials/data.

## 9. Acceptance boundary

Architecture is suitable for the requested mobile, centralized, multi-user direction. It does not by itself provide authentication, offline-safe writes, reconciliation or app-store readiness. Those are implementation and verification work listed in Document 5. Nothing in this audit creates a deployable backend or mobile package.

