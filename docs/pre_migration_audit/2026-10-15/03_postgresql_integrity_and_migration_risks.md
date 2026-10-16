# PostgreSQL Integrity and Migration Risk Report

Date: 2026-10-15. Audited source: checkpoint 46c7643 on migration/fastapi-flet.  
Read with [Technical Audit](01_technical_audit_report.md) and [Migration Plan](05_migration_implementation_plan.md).

## 1. Evidence boundary

**Source:** migrations 001-031, integrity SQL test file, connection/service transaction code.  
**Live:** PostgreSQL 18.6; catalogs inspected inside an explicitly read-only, repeatable-read transaction. No schema or business data was changed.

Live confirms installed objects and selected definitions/indexes, not byte-for-byte equivalence of every function body to every committed migration. No migration ledger exists to prove execution order. Migration 031 fields/indexes are installed. A full definition manifest and restored-clone comparison remain prerequisites.

| Live public-schema object | Count / observation |
|---|---|
| Tables / primary keys | 39 / 39 |
| Foreign keys | 51 |
| CHECK / UNIQUE constraints | 100 / 11 |
| NOT NULL constraints | 276, PostgreSQL 18 catalog representation |
| Non-internal triggers | 51, inspected enabled |
| Deferred integrity triggers | 19, DEFERRABLE INITIALLY DEFERRED |
| sf_* functions | 20, all SECURITY INVOKER |
| Exclusion constraints | None found |
| RLS-enabled tables | None found |
| Migration tracking table | None found |
| Overlapping bus-status intervals | Zero currently |
| Application connection role | Superuser, create-role, create-database, bypass-RLS |

Unique indexes are additional to the 11 UNIQUE constraints; do not interpret that constraint count as the full uniqueness inventory.

## 2. All tables and relationship groups

| Area | Tables | Main relationships |
|---|---|---|
| Fleet | routes; buses; bus_documents; bus_status_history; bus_route_history | buses.route_id -> routes; documents/status/route histories -> buses; route history -> routes |
| People | drivers; driver_employments; driver_assignments | employments -> drivers; assignments -> employments and buses |
| Accounts/ledger | financial_accounts; financial_transactions; transfers; transfer_fee_rules | ledger -> account; transfers -> source/destination account and fee rule; transfer ledger rows -> transfer |
| Expenses | expense_categories; expenses; expense_allocations | expense -> category, optional bus/account/ledger; allocations -> expense and bus |
| Cashing | remittance_collections; remittances; cashing_rates; cashing_schedules; cashing_schedule_rules; cashing_obligations; cashing_obligation_payments | collection -> paid-into account/ledger; remittances -> collection/bus; obligations -> collection/remittance/driver; settlement -> obligation/account/ledger |
| Driver money | driver_advances; driver_deductions; driver_salaries; salary_advance_recoveries; salary_deduction_allocations; driver_salary_presets | money rows -> employment; salary recovery/allocation -> salary and original advance/deduction |
| Business/owner money | business_loans; loan_repayments; owner_loans; owner_loan_transactions | repayment -> loan when identified; repayment links business ledger OR owner funding; owner transaction -> owner loan, optional expense/ledger |
| Maintenance | maintenance; maintenance_schedules | both -> bus; maintenance may link expense |
| Configuration/support | business_settings; business_preset_audit; reminder_presets; reminders; correction_audit | reminders may link bus, loan or maintenance schedule; audit stores JSON snapshots |

These groups enumerate all 39 live tables. FKs inspected use NO ACTION rather than a general cascade-deletion policy. Service deletion order and deferred integrity semantics are part of the current contract.

## 3. Migration history and final definitions

- 001-018 create core transport/accounting tables.
- 019 adds integrity/indexes.
- 020-021 seed configuration/rates.
- 022 hardens the schema with sf_* functions and deferred triggers.
- 023 bus details/document metadata; 024 expense vendor/reference.
- 025 finance/presets, replacement loan/integrity functions.
- 026 fleet history/editing.
- 027 smart cashing; replaces collection reconciliation.
- 028 historical October rate baseline.
- 029 money workflows, nullable/unknown loan details, advance settings.
- 030 correction snapshots.
- 031 servicing costs, generated total, schedule/backfill changes.

Later replacement definitions take precedence. Seed/backfill scripts contain business assumptions and must not be blindly replayed over the real database. The standalone integrity SQL suite is test code, not a migration and not safe to run against production without reviewing its writes.

## 4. Uniqueness and checks that must survive

Confirmed examples:
- Unique registrations, route/category/account names.
- One current open bus status and route history per bus; one active permanent bus/employment assignment; one active employment per driver.
- Salary unique by employment/year/month.
- Expense allocations unique by expense/bus; remittances unique by collection/bus.
- Maintenance schedule unique by bus/name.
- Partial unique ledger references for expense, collection, driver advance, salary, owner transaction and loan repayment.
- Owner funding expense and loan-repayment owner transaction links unique.
- Salary recovery unique by salary/advance and deduction allocation by salary/deduction.
- Unique servicing expense link when is_servicing and expense_id is not null.
- Monetary positivity/nonnegativity, valid enum-like text values, scope/link compatibility and date conditions are enforced by table checks and cross-row functions.

Do not widen text values or change column nullability casually. NULL loan principal means unknown, not zero. Read-only generated amounts such as maintenance.total_cost must not be assigned by an ORM or accepted from client payloads.

## 5. Installed function inventory

sf_assert_advance, sf_assert_business_loan, sf_assert_collection, sf_assert_deduction, sf_assert_employment, sf_assert_expense, sf_assert_fee_rule, sf_assert_ledger, sf_assert_loan_repayment, sf_assert_maintenance, sf_assert_owner_balance, sf_assert_owner_loan_transaction, sf_assert_rate, sf_assert_salary, sf_assert_transfer, sf_integrity_deferred, sf_is_external_transfer, sf_preserve_account_type, sf_suggest_transfer_fee, sf_touch_updated_at.

The 19 deferred integrity triggers cover: business_loans, cashing_rates, driver_advances, driver_assignments, driver_deductions, driver_employments, driver_salaries, expense_allocations, expenses, financial_transactions, loan_repayments, maintenance, owner_loan_transactions, remittance_collections, remittances, salary_advance_recoveries, salary_deduction_allocations, transfer_fee_rules, transfers.

Other installed triggers include timestamp maintenance and account-type preservation. Keep their enabled state, timing and security-invoker behavior. Restricted-role testing must include function access to related tables.

## 6. Financial rules

### Ledger, expenses and transfers
Migration 022's sf_assert_expense (around line 198), sf_assert_transfer (122) and sf_assert_ledger (528) reconcile document/link/type/direction/date/amount relationships. Expense scope and multi-bus allocations matter. An internal transfer is not business revenue or consolidated spending; fees are real outflows. Ledger rows must not be independently inserted by a generic public CRUD endpoint.

### Cashing
The collection check replaced in migration 027 (around line 141) reconciles the incoming ledger/header total with bus allocations and signed unallocated difference. Estimated/proportional allocations are not confirmed individual receipts. Preserve provenance and obligations; a later obligation settlement must not duplicate the original collection.

A SELECT duplicate check in smart_cashing_service is not a concurrency constraint across different headers. Decide allowable bus/date/coverage combinations and add atomic command deduplication before remote writes.

### Payroll and advances
sf_assert_advance / deduction / salary (022 around lines 263/299/328) require consistent employment, recovery/allocation amounts and appropriate paid-ledger linkage. Recoveries cannot exceed advances. Allocated recovery/deduction totals must match salary components. A fully deducted zero-net salary legitimately has no zero-value ledger payment. Repaid status requires full recovery.

Do not count advance payment and its salary recovery as two salary expenses. Cost recognition and payment cashflow are different. Preserve cancellation/allocation behavior and row-locking when adapting driver_money_service.

### Loans and owner money
sf_assert_loan_repayment (replaced in 025 around line 142), sf_assert_business_loan, sf_assert_owner_loan_transaction and sf_assert_owner_balance protect source and outstanding balances.

Business-funded lender repayment uses a business OUT ledger entry. Owner-personal lender repayment uses the corresponding owner-funding transaction without inventing a business cash withdrawal. Owner funding can represent personal settlement of an expense or lender, not necessarily money received into an account. Known principal caps repayments; unknown principal/identity must stay unknown. Owner repayment cannot exceed the outstanding owner-funded amount.

### Maintenance
sf_assert_maintenance (022 around line 506) protects expense/bus association, but intentionally does not require every maintenance record's cost to equal its linked expense. Legacy partial/multiple-job costing exists. Migration 031 introduces servicing flags, transport cost, payment date and generated total = parts + labour + transport.

record_servicing in maintenance_service must retain its stronger coordinated-workflow validation. Do not add a blanket equality constraint that invalidates legacy data, and do not assume the older trigger enforces all servicing semantics.

### Rates and history
sf_assert_rate / sf_assert_fee_rule enforce relevant validity rules. Bus history currently has unique open rows, not an exclusion rule for all date overlaps. No live status overlap was found. Retain inclusive boundary behavior and test status/route changes, acquisition date, backfill and unknown days.

## 7. Transaction and concurrency risks

Current service pattern is a psycopg connection context and cursor. Successful exit commits; exceptions roll back. Deferred integrity errors may occur at commit, after the individual statements succeeded. Catch/translate errors around the complete transaction, not only execute(). Return success only after commit.

[Official psycopg transaction guidance](https://www.psycopg.org/psycopg3/docs/basic/transactions.html) documents the context behavior and implicit transactions. Avoid idle-in-transaction connections and autocommit-per-statement financial workflows.

Some services already lock relevant employment/loan/obligation rows. Preserve those locks. This audit did not execute concurrent writes and does not certify all interleavings. Add races for simultaneous advance recovery, loan/owner repayment, correction/settlement and duplicate cashing.

Reports use multiple connections today; a single snapshot is required for internally coherent reports under concurrent entry.

## 8. SQLAlchemy/Alembic introduction risks

SQLAlchemy is optional, not a prerequisite for FastAPI. Initial reuse of psycopg avoids converting the database and application architecture together.

If introduced later:
1. Reflect/review the real schema; map NUMERIC to Decimal, dates to date, JSONB snapshots faithfully.
2. Preserve generated expressions, identity/sequence behavior, checks, named and partial indexes, foreign keys, functions and trigger timing.
3. No metadata.create_all against the existing database.
4. No ORM delete-orphan/cascade behavior unless explicitly compatible with historical and financial rules.
5. One unit of work owns commit; do not wrap several independently committing services and claim atomicity.
6. Review ORM autoflush ordering against deferred checks; never return before commit.
7. Review every migration's forward and rollback SQL on restored copies. Do not rely on autogeneration to reconstruct custom trigger functions.

[SQLAlchemy PostgreSQL dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html) is the reference for database-specific mapping. [Alembic autogeneration](https://alembic.sqlalchemy.org/en/latest/autogenerate.html) explicitly requires review and has detection limitations; it is not a schema-preservation guarantee.

## 9. Required baseline/restore evidence before cutover

No commands in this section were executed.
- Approved snapshot/backup of actual schema and data; keep business records private.
- Manifest of tables, columns/types/defaults/generated values, identities/sequences, checks, FKs, all unique/partial indexes, function definitions, triggers/timing/enabled state and grants.
- Restore on an isolated supported PostgreSQL instance; compare manifest and sequence next values; run integrity tests only there.
- Reconcile account opening/current values, period cashflow, collection headers vs allocations, expense allocations, payroll recoveries, business and owner debt, maintenance associations and historical date ranges.
- Test with least-privileged runtime credentials, including commit-time rejection/rollback.
- Establish reviewed migration baseline, future migration ledger, deployment compatibility and backup retention.
- Document rollback without losing new transactions: stop writes, preserve post-cutover data, switch one writer, reconcile; do not restore a stale backup over newly entered real data.

Database protections must remain database protections. Server validation improves usability but does not replace them.

