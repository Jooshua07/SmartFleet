# Step 4 completion report

## Delivered

Finance now shares Month, 3 Months and Custom calendar periods across all tabs. General shows Collections, Operating Costs and Other Payments; Balances shows opening cash, money in/out, net movement and historical closing cash. Period changes never reset cash or delete records.

Home shows cumulative Total Revenue, Total Expenses and actual Business Balance at Thursday/Sunday points. Actual transactions retain their dates; between-date movements appear at the next point, and trailing activity gets a labelled period-end point. Month/3 Months/6 Months controls are independent. Adaptive axes, zero line, tooltips and horizontal mobile scrolling are implemented.

Servicing uses the existing maintenance tables, with labour, transport and other components, actual completion/payment dates, zero-cost events, one linked bus expense/payment, history and audited corrections. The latest valid completion controls the next due date; manual scheduling is separately audited. More and bus cards share the same form. In Garage is removed from status filters.

Historical ordinary expense editing reuses its payment, clears obsolete attribution and protects specialized and servicing payments. Reports is a long, organized page with business overview, bus/status performance, costs, maintenance, driver money, loans/owner money and data checks. Five CSV/Excel summaries and a complete workbook use report calculations. Baseline reconciliation is read-only.

## Database and preservation

- Backup: `backups/smartfleet_20261014_195248.dump`, 380 archive entries, restored successfully into a disposable PostgreSQL database; all original financial and maintenance rows matched.
- Applied migration: `031_servicing_workflow.sql`. Adds transport cost, servicing flag, payment date, generated combined cost and unique servicing expense linkage; adds Servicing category and guarded initial schedules. Existing constraints and historical migrations remain.
- Initial schedules: AIF 9681, AIG 5301 and AIH 2715, each 18 October 2026, 35-day interval. No prior completion/schedule existed; none was overwritten.
- Live original financial and maintenance event records compared unchanged after implementation.
- Real reconciliation: opening K0, received K16,200, operating payments K2,000, principal repayments K15,000, total paid K17,000, closing K-800.
- The K15,000 repayment still lacks an identified loan. It is flagged for the owner to clarify; no principal or lender is invented.
- No fake financial records, automatic adjustments, public deployment or paid infrastructure.

## Verification

| Check | Executed result |
| --- | --- |
| Existing baseline | 77 unit/page tests passed |
| Final unittest suite | 93 passed |
| Migration recreation | All 31 applied in disposable PostgreSQL DB |
| Smart Cashing integration | Passed |
| Expense/finance integration | Passed |
| Driver/loan/owner-money integration | Passed, including expanded reporting scenarios |
| Step 4 scenarios | Passed: servicing components, zero cost, early/late, backdate, correction, duplicates, one payment, scope changes, one-week/multi-bus cashing, deactivation, unresolved allocation, report/chart equality |
| Read-only AppTest sweep | All 16 pages passed; Finance tab persistence, historical cutoff, invalid dates and independent Home controls passed |
| Browser layout | Six changed screens passed at 390x844 and 1440x1000; no page-wide horizontal overflow; phone chart scroll region 560px inside 358px content |
| Excel/CSV | Numeric/date round trips and five-sheet workbook reopening passed; totals match report sources |
| Compilation and whitespace | Passed |
| Real-record preservation | Passed |

Browser automation emulates viewport sizes; it does not replace testing the actual phone browser or cellular/network setup. Six-month chart geometry is verified with over 50 test points; current live history is limited to October. The legacy SQL integrity script is preserved and was not used against live data. Safe financial scenarios execute in disposable databases.

## Git checkpoints

Before changes: `smartfleet-before-step4-20261014` tag.

| Stage | Commit |
| --- | --- |
| Calendar periods and balances | `9dd8dc8` |
| Financial chart | `9a53753` |
| Servicing | `83bcd44` |
| Historical expense safeguards | `49feb49` |
| Business report | `9bad738` |
| Exports/reconciliation | `0507a7f` |
| Regression and documentation | `3005903` |

Checkpoints are local on `codex/expense-finance-refinement`. This run did not publish or push them to GitHub.

## Files changed

- Application/pages: `app.py`, `app_pages/home.py`, `finance.py`, `buses.py`, `more.py`, `record_expense.py`, `record_servicing.py`, `reminders.py`, `reports.py`.
- Shared UI: `components/reporting_period.py`, `components/servicing_form.py`.
- Services: `services/finance_service.py`, `performance_service.py`, `expense_service.py`, `maintenance_service.py`, `business_report_service.py`, `report_export_service.py`.
- Utilities: `utils/reporting_periods.py`, `utils/dashboard_charts.py`.
- Migration/dependencies: `migrations/031_servicing_workflow.sql`, `requirements.txt` (openpyxl), `.gitignore` (runtime logs).
- Tests: `tests/test_reporting_periods.py`, `test_financial_timeline.py`, `test_servicing.py`, `test_servicing_page.py`, `test_report_exports.py`, `test_expense_service.py`, `test_home_page.py`.
- Scripts: `scripts/verify_step4_backup.py`, `verify_step4_live.py`, `smoke_step4.py`, `smoke_step4_pages.py`, `smoke_step4_ui.py`, `smoke_money_workflows.py`.
- Documentation: `docs/PROJECT_STATE.md`, `ARCHITECTURE.md`, `MODULE_REFERENCE.md`, `FEATURE_STATUS.md`, `TESTING.md`, `ADDING_NEW_FEATURES.md`, `STEP4_IMPLEMENTATION.md`, this report and `NEXT_PHASE_GUIDE_AND_CLEANUP.md`.

## Phone review

1. Open `http://172.20.10.2:8501` on the same Wi-Fi/hotspot as the PC and refresh. Keep the PC on.
2. Home: swipe the chart horizontally; switch its period and check the other Home filter stays unchanged. Tap/hover a point to inspect amounts.
3. Buses: confirm the three 18 October due dates and urgent reminders. Check Edit Bus shows date/frequency; cancel if no real correction is needed.
4. More > Record Servicing: inspect components and actual dates. Save only actual completed work; future completion dates are rejected. History has a correction action with a required reason.
5. Finance: select Custom 1-4 October, move through all tabs and check dates persist. Balances should reflect that date, not today's balance.
6. Reports: inspect all sections, change the period, reconcile October and download/open CSV and Excel. Compare category/receipt totals with the screen.
7. Record Expense: expand older history. Corrections should use the existing payment; servicing corrections belong in servicing history.

## Next phase and remaining scope

`NEXT_PHASE_GUIDE_AND_CLEANUP.md` specifies a short Welcome/Help area, searchable task guides, More entry, optional first-use orientation and practical correction/financial examples. It also specifies evidence-based cleanup with call-site checks, small commits and disposable financial tests. This is a specification only; the next large feature phase has not started.

No implementation requirement was intentionally skipped. Operational loan identification remains a user data task. The app remains local, and existing authentication/document-upload/assignment expansions are outside this Step 4 scope.
