# Step-by-Step Migration Implementation Plan

Date: 2026-10-15. Planning only. No endpoints, mobile app, packages or schema changes were implemented.

## 1. Rules and release gates

Work in small vertical slices: existing query/rule -> explicit API contract -> Flet screen -> parity tests. Keep the existing database rules and parameterized queries first; an ORM conversion is a separate optional project.

**Gate A, before any prototype:** confirm audited commit, read-only/isolated database target, test-data isolation and no public exposure. Bus proof of concept below is local-only.

**Gate B, before remote financial writes:** least-privileged runtime role; authentication/permissions; durable idempotency; single-transaction command ownership; actor-attributed correction policy; reviewed schema baseline and proven isolated restore. Decide stale-edit behavior and money/date contracts.

**Gate C, before cutover:** all domain/API/database/device parity tests pass, bus summary/detail reconciles, logs/error handling and backup monitoring work, user acceptance succeeds, one writer and rollback/reconciliation procedure agreed.

Do not overwrite new real records with an old backup. A code rollback and a data rollback are different operations.

## 2. Module-by-module order

Endpoint names are proposed contracts, not existing features. All write endpoints require Gate B.

### 0. Freeze evidence and establish baseline
- Existing: git checkpoint, migrations 001-031, scripts/verify_migrations.py and backup verification tooling.
- Reuse: schema SQL and integrity test expectations; historical docs as evidence, not executable truth.
- API/screens: none yet.
- DB: full schema, functions, triggers, privileges, sequences; isolated restored copy.
- Tests: restore/manifest comparison, read-only role, record counts and financial reconciliation, scripts forbidden on production.
- Risk/difficulty: high; protect real October data and unknown historical loan details.

### 1. Settings, money/date contracts and transaction boundary
- Existing: database/connection.py; utils/validation.py, dates.py, reporting_periods.py; services/financial_rules.py.
- Reuse: Decimal, Lusaka dates, period calculations and operating classification. Add strict external validation, settings validation and connection timeout/UOW boundary.
- API/screens: health/readiness without credentials or detailed catalog output; common error/display contracts.
- DB: no schema rewrite; one connection per command/report snapshot.
- Tests: invalid/NaN/infinite/overscale amounts, baseline/reversed dates, leap/month ends, commit-time failure and rollback.
- Risk/difficulty: medium; avoid accidental behavioral change in calendar/coverage windows.

### 2. Read-only bus proof of concept
- Existing: bus_service.get_all_buses; route_service.get_all_routes; app_pages/buses.py.
- Reuse: read queries, registration/status fields; limit DTO to needed fields.
- API: GET /buses, then /buses/{id}, /routes with pagination/search for production.
- Flet: bus list, loading, empty, error and retry.
- DB: buses/routes only; read-only credentials.
- Tests: zero/one/multiple buses, inactive bus, missing optional route label, server error, unavailable network, stable IDs/order.
- Risk/difficulty: low; no business writes.

### 3. Authentication, roles and accountable commands
- Existing: no authentication implementation; correction_service and migration 030 provide partial snapshot support.
- Reuse: JSON-safe snapshot conversion. Design new identity/idempotency/audit additions separately.
- API: login/session refresh/logout, current user; common authorization dependencies; command status for uncertain mobile outcomes.
- Flet: login/session expiry, permission-based navigation, no stored DB secrets.
- DB: reviewed new identity/command/audit schema only after approval; grants for restricted runtime.
- Tests: wrong/expired/revoked identity, role denial, direct unauthorized ID access, key collision/different payload, simultaneous same command, rollback on integrity failure.
- Risk/difficulty: high; required before external writes.

### 4. Reference data and fleet/history management
- Existing: bus_service, route_service, driver_service; add_bus/buses pages.
- Reuse: create_bus, update_bus_details, set_bus_status, create_driver/update_driver and route validation/history queries.
- API: POST/PATCH /buses; status/route-history commands; GET/POST /routes; GET/POST/PATCH /drivers. Add employment/assignment lifecycle endpoints only after defining gaps.
- Flet: Buses/Routes/Drivers tabs, add/edit/detail, status confirmation and history.
- DB: fleet/history/doc metadata/drivers/employments/assignments.
- Tests: duplicate registration/route, invalid capacity, missing required route, acquired/start/end dates, inactive bus, reactivation, backdated and overlapping history, driver changes across periods.
- Risk/difficulty: medium-high; history influences cashing and salary.

### 5. Presets and starting balances
- Existing: preset_service; account_service; business_presets/finance UI.
- Reuse: rate/schedule/salary/reminder/baseline retrieval and validation; account management.
- API: GET/PATCH /settings and effective-dated presets; GET /financial-accounts; restricted opening-balance command.
- Flet: owner settings and clear account starting balances.
- DB: accounts, settings, preset audits, rate/schedule/salary/reminder presets.
- Tests: permissions, first-October baseline, future/historical effective dates, overlapping rates, same-transaction audit, opening-balance changes after transactions, optional negative warning behavior.
- Risk/difficulty: high; changes reinterpret reports, not merely labels.

### 6. Operating expenses
- Existing: expense_service, record_expense.py, report_service expense export.
- Reuse: scope/payment-source/category restrictions, allocation and ledger linking.
- API: GET/POST /expenses; PATCH or explicit correction command; authorized cancellation policy rather than unaudited generic delete.
- Flet: category groups, paid-to/reference, account, general/bus/multi-bus allocation, receipt metadata.
- DB: expenses/categories/allocations/accounts/ledger; owner funding where applicable.
- Tests: one/shared/general expense, missing vendor/reference when optional, invalid bus/account, allocation mismatch, zero/negative/overscale, owner-personal expense, double tap/timeouts, stale edit, rollback, audit and no duplicate ledger.
- Risk/difficulty: high; do not create salary/loan/drawing as an ordinary operating expense.

### 7. Smart cashing and obligation settlement
- Existing: smart_cashing_service, cashing_service, utils/cashing_form.py, record_cashing.py.
- Reuse: coverage dates, expected rates/active days, allocation provenance, ledger/obligation reconciliation, correction locks.
- API: GET /cashing/preview; GET/POST /collections; correction command; GET /obligations; POST /obligations/{id}/payments.
- Flet: a single paid-into/multi-bus form, per-bus amounts, applicable Sunday/coverage/variance fields, review then submit, clear only on confirmed success.
- DB: collections/remittances/rates/fleet histories/obligations/payments/ledger.
- Tests: one/multiple buses, equal/different amounts, missing amount, Sunday/Thursday coverage, inactive days, partial/excess/missing allocation, signed difference, confirm-vs-estimated provenance, two concurrent same-coverage submissions, settlement/correction race, repeat command, failed submission preserves input, successful form reset.
- Risk/difficulty: high; extract float/UI calculations before reusing them.

### 8. Finance and Home
- Existing: finance_service, dashboard_service, performance_service; finance/home pages; dashboard_charts.
- Reuse: ledger and operating queries, pure financial timeline, date filters and measure definitions.
- API: GET /finance/balance-now; /finance/cashflow?start=&end=; /finance/ledger; /performance/summary; /performance/series.
- Flet: Business Balance Now independent of period; filtered received/paid; Home overview; native charts.
- DB: ledger/accounts plus cashing/expenses/payroll according to each measure.
- Tests: opening balances, October/November/December and 3-month view, internal transfer cancellation/fee, financing vs operating, future dates, baseline clamp, zero/negative contribution, 4000 not 400000, both grouped bars independently anchored at zero, empty periods.
- Risk/difficulty: medium-high; agree definitions before reusing similarly named legacy helpers.

### 9. Bus Accounts and historical performance
- Existing: bus_account_service; accounts.py.
- Reuse: attribution queries and provenance, after resolving summary/detail cost mismatch.
- API: GET /bus-accounts; /bus-accounts/{id}?start=&end=.
- Flet: bus summary, detail, cost breakdown and trend with estimated revenue labels.
- DB: remittances, allocated/direct expenses, salary assignments and fleet histories.
- Tests: summary/detail/category reconciliation, attributed salary, multi-assignment salary ambiguity, shared general costs, historical excluded-category rows, bus/date filtering.
- Risk/difficulty: high; do not reproduce incompatible SQL definitions.

### 10. Driver payroll and advances
- Existing: driver_money_service, driver_money.py.
- Reuse: salary preview/proration, FIFO recovery, caps, employment checks and locking.
- API: GET /driver-money; salary preview; POST /advances, /salaries, authorized correction/cancellation commands.
- Flet: driver balances, advance entry, salary review/payment and correction.
- DB: employments/assignments/salaries/advances/deductions/recoveries/ledger/presets.
- Tests: partial month, capped/oversized advance, concurrent recovery/payment, salary uniqueness, fully deducted zero-net salary, unrelated employment, cancellation releases allocations, earned salary versus cash payment.
- Risk/difficulty: very high; maintain financial/DB regression coverage before new UI.

### 11. Lender loans and owner money
- Existing: loan_service, loans.py, owner_money.py.
- Reuse: outstanding checks/locks, owner funding sources, unidentified repayments, corrections.
- API: GET/POST /loans; POST /loan-repayments; association command if approved; GET /owner-money; owner funding/drawing/repayment commands.
- Flet: separate loan and owner screens; unknown loan detail clearly labelled.
- DB: business loans/repayments, owner loans/transactions, expense and ledger links.
- Tests: known/unknown principal and loan identity, owner-personal vs business-funded repayment, cap exceedance, concurrent repayment, paid expense funded personally, drawing not operating expense, corrections restore debt correctly.
- Risk/difficulty: very high; association changes must preserve original payment facts and audit trail.

### 12. Servicing and reminders
- Existing: maintenance_service, reminder_service, servicing_form, servicing/reminders pages.
- Reuse: cost validation, linked expense workflow, latest-service schedule refresh, warning calculations.
- API: GET/POST /servicing; GET/PATCH /maintenance-schedules; GET /reminders.
- Flet: servicing entry/history/due list; due/expiry indicators.
- DB: maintenance/schedules/expenses/allocations/ledger/document metadata/reminders.
- Tests: parts+labour+transport total, payment vs service date, duplicate expense link, owner funding, future schedule, correction to most-recent service, legacy partial-cost record, due-boundary and expiry handling.
- Risk/difficulty: high; older DB maintenance rule is weaker than servicing command validation.

### 13. Reports and exports
- Existing: business_report_service, report_service, report_export_service; reports page.
- Reuse: report data tables, spreadsheet/CSV export and formula sanitization after measure reconciliation.
- API: GET /reports/business; /reports/reconciliation; authorized CSV/XLSX export.
- Flet: period selection, opening/closing and report warnings, native download/share.
- DB: coherent read snapshot across finance/fleet/payroll/loans/maintenance.
- Tests: cross-report totals, empty month, all-time/baseline, 3/6/custom months, unknown expected/principal, concurrent entry snapshot, non-ASCII names, formula-like vendor text, phone file export.
- Risk/difficulty: high; expected values are not a reconstructed complete calendar.

### 14. Documents, backup UI and help
- Existing: bus metadata; backup_service/backups.py; help_content/help_guide.py.
- Reuse: metadata validation, backup tool discovery, pure guide topics; adapt guide labels.
- API: authorized document upload/download only when designed; owner-only backup job/list/download; help can be client-bundled.
- Flet: attachments, backup status and searchable help.
- DB: document metadata and any approved private-file/job references; no client DB access.
- Tests: forbidden download/path traversal/oversize upload, malicious filenames, missing pg tools, failed backup, actual isolated restore, help search, phone accessibility.
- Risk/difficulty: medium-high; no existing complete upload feature to port automatically.

### 15. Operational rehearsal and cutover
- Existing: smoke/profile/verification scripts and testing docs.
- Reuse: expected outcomes; redirect all write tests to disposable restored copies. Rewrite Streamlit-specific UI checks as Flet/API/device scenarios.
- API/screens: full role-specific acceptance flow; production health and recovery.
- DB: manifest/grants/backup restore confirmed; no unaudited schema diff.
- Tests: simultaneous recorders, timeout after commit, restart during request, reconnect/login expiry, data export, report parity and rollback rehearsal.
- Risk/difficulty: high; owner signs off, freeze old writer, deploy compatible backend/client, reconcile opening totals and monitor.

## 3. Minimal end-to-end proof of concept

**Documentation example only. Not created as Python files, installed, run, compiled or tested.** It deliberately has no write endpoints. Run only later on loopback with an isolated/read-only database. It is not safe to expose this unauthenticated example over a LAN/public internet. Complete stages 1-3 before a real remote pilot.

Proposed backend example, run from a project import context where the existing services are available:

```python
from fastapi import FastAPI
from pydantic import BaseModel

from services.bus_service import get_all_buses

app = FastAPI(title="SmartFleet read-only prototype")


class BusView(BaseModel):
    id: int
    registration_number: str
    status: str
    route_name: str | None = None


@app.get("/api/v1/buses", response_model=list[BusView])
def list_buses():
    return [
        BusView(
            id=row["id"],
            registration_number=row["registration_number"],
            status=row["status"],
            route_name=row["route_name"],
        )
        for row in get_all_buses()
    ]
```

Proposed desktop/native Flet client example (not browser/Pyodide code):

```python
import asyncio
import os

import flet as ft
import requests

API_URL = os.getenv("SMARTFLEET_API_URL", "http://127.0.0.1:8000")


def fetch_buses():
    response = requests.get(f"{API_URL}/api/v1/buses", timeout=10)
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list):
        raise ValueError("Unexpected bus response")
    return rows


async def main(page: ft.Page):
    page.title = "SmartFleet"
    body = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
    page.add(ft.Text("SmartFleet"), body)

    async def reload_buses(event=None):
        body.controls = [ft.Text("Loading buses...")]
        page.update()
        try:
            rows = await asyncio.to_thread(fetch_buses)
            controls = [
                ft.Text(
                    f'{bus["registration_number"]} | '
                    f'{bus["status"]} | {bus.get("route_name") or "No route"}'
                )
                for bus in rows
            ]
            body.controls = controls or [ft.Text("No buses recorded.")]
        except (requests.RequestException, ValueError, KeyError, TypeError):
            body.controls = [ft.Text("Could not load buses. Please retry.")]
        page.update()

    page.add(ft.Button(content="Refresh", on_click=reload_buses))
    await reload_buses()


ft.run(main)
```

The async UI structure follows [Flet async-app guidance](https://flet.dev/docs/cookbook/async-apps/). Confirm exact APIs against the chosen installed Flet version before implementation. The sample does not include cancellation/race handling for repeated refresh clicks, auth or production pagination; those are subsequent requirements.

Future local run command after approved environment setup: `python -m uvicorn bus_api:app --host 127.0.0.1 --port 8000` (bus_api is the proposed example filename, not a current module). Execute the client in its separate environment. No server was started by this audit.

A physical phone's 127.0.0.1 refers to the phone, not the PC. Use an authenticated HTTPS pilot endpoint before device testing; do not fix this by publicly exposing the unauthenticated sample or PostgreSQL.

## 4. Test ladder and acceptance

1. Retain all relevant existing domain tests; current baseline is 98 passing.
2. Add isolated PostgreSQL integration tests that actually commit both valid and invalid transactions; mocked tests cannot prove deferred constraints.
3. Add HTTP contracts, role denial, strict money validation and commit-time error mapping.
4. Add multi-connection races and durable request retry tests for every financial command.
5. Replace Streamlit AppTest checks with Flet control-state tests and packaged-device interactions.
6. Run human scenarios: select wrong bus then change it; blank a required amount; submit twice; lose network after submit; expire login during edit; revisit a prior month; correct an already settled record; export then reopen report.
7. Check grouped charts at zero, actual ZMW values, empty/negative-profit periods and compact phone layouts.
8. Compare reports to agreed database fixtures and real records under read-only review; never seed demo values into production.
9. Restore a backup on a separate database and prove business totals before approving cutover.

## 5. Effort and unknowns

Difficulty is concentrated in safe writes, identity/audit, historical rules and payroll/loan/report parity, not in the bus list UI. No defensible completion date is available until authentication policy, device distribution (especially iOS), VPS, missing workflows and the audit findings are agreed. Estimate after the read-only prototype and one complete expense slice; do not treat a successful demo screen as migration completion.

