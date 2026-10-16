# SmartFleet development instructions

- Work only on `migration/flask`. Never change `master` or historical tags.
- Read `docs/FLASK_MIGRATION_AUDIT_AND_PLAN.md` and the progress document before resuming.
- Keep the Streamlit application operational until Flask parity is demonstrated.
- Flask development must connect only to loopback PostgreSQL and the explicitly isolated `smartfleet_flask_dev` or `smartfleet_flask_test` databases. Never run tests or setup against the VPS or the real smartfleet database.
- Credentials, generated fixtures, browser artifacts and local environments belong in ignored paths, never Git.
- Reuse services and preserve PostgreSQL constraints, triggers, Decimal calculations and recorded financial history.
- Use authenticated POSTs with CSRF for mutations. Show success only after commit. Required financial command tests must prove restart-safe deduplication and atomic actor-attributed auditing.
- Any production deployment, production schema/data change or unresolved financial policy requires owner authorization.
- Run the relevant pytest, integration, browser, Ruff and dependency security checks for each stage. An unavailable mandatory check is BLOCKED, not PASSED.
- Record commands/results/limitations in `docs/FLASK_MIGRATION_PROGRESS.md`. Commit/push only stages with verified acceptance gates, then continue to the next authorized stage.
- Do not install production dependencies from the Streamlit environment snapshot. Target Python 3.12, Ubuntu 24.04 and PostgreSQL 18.6; keep the production runtime small.
