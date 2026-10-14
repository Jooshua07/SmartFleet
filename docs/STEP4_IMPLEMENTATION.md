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
