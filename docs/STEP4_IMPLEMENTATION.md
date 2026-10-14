# Step 4 execution

## Stage 1

- Baseline: 77 existing tests passed (Windows temporary-folder cleanup warning after OK).
- Backup: `smartfleet_20261014_195248.dump`, restored to disposable PostgreSQL database.
- Restored financial and maintenance rows matched live database exactly.
- Before-change Git tag: `smartfleet-before-step4-20261014`.
- Shared calendar periods use current month-to-date, current plus previous two/five months, or validated custom dates.
- Independent state prefixes for Finance, Home chart and Reports.
- Reporting baseline opening is zero; later openings carry ledger movement forward.
- Internal transfers are excluded from consolidated cash flows.
- Five focused calendar/classification tests passed.

## Financial definitions

Operating revenue is recorded cashing, not financing. Operating costs recognize ordinary expenses and earned payroll once. Salaries are recognized on the first day of their payroll month, matching existing performance and Bus Accounts calculations; actual payments stay on their payment dates. Principal payments, drawings and advances are separate cash movements. Historical closing balances use the selected end date.

## Stage 2

Scheduled cumulative chart uses Thursday/Sunday points and adds a labelled period-end point for trailing activity. Transaction dates remain unchanged. Revenue excludes financing, costs exclude principal/drawings/advances, and cash balance uses the ledger. Separate Month/3 Months/6 Months chart controls. Seven focused chart/performance tests passed; mobile browser verification follows during regression.

## Stage 3

Migration 031 extends existing maintenance records with transport, servicing flag and actual payment date. Other costs use the existing parts_cost field; no inventory workflow. All three real buses had no prior maintenance and were safely scheduled for 18 October 2026. Completion, linked operating expense and ledger payment save atomically. Zero-cost completions have no expense/payment. Audited corrections reuse the payment, and latest completion controls the due date. Threshold tests and disposable PostgreSQL scenarios passed, including duplicates, backdating, zero cost and corrections. Record Servicing is reachable from More and each bus.
