# Next phase: Welcome to SmartFleet and controlled cleanup

## In-app guide

Add Help to More, with a concise Welcome to SmartFleet introduction, search and task categories: Getting started, Cashing, Costs and servicing, Drivers, Loans/owner money, Reports and corrections. Each answer should take under a minute to read, with three to five numbered actions and a link to the actual page. Optional first-use orientation is dismissible and never blocks recording.

First-time setup: confirm reporting baseline, routes, bus registration and historical status, drivers/employment/assignment, rates and schedule, default business payment account, and servicing due dates. Explain the clean-slate reporting opening before entering historical transactions.

Required questions and scenarios:

- How do I record today's or a previous Thursday/Sunday cashing? Show the current Smart Cashing summary, received amount, bus adjustments, Sunday coverage and unresolved difference handling.
- How do I record one bus's expense or a General business expense? Show scope, title, category, amount, supplier/reference and notes. General costs remain unassigned.
- How do I record servicing? Select bus, actual completion, cost components and actual payment date; explain the next 35-day cycle and zero-cost completion.
- How do I give an advance and pay salary afterwards? Explain recoverable advances, earned salary, recovery and net cash payment with a simple K2,500 salary / K1,000 advance example.
- How do I repay a loan or record the owner paying the lender personally? Use Loans; personal settlement creates owner liability and no business cash outflow.
- How do I repay the owner or record drawings? Distinguish debt repayment and money withdrawn for personal use.
- How do I compare buses or view last month's report? Use Bus Accounts and Reports > Custom. Explain estimated bus allocations and shared costs.
- What is Business Balance versus operating contribution? Balance follows cash; contribution excludes principal, drawings and recoverable advances.
- How do I correct mistakes? Ordinary expenses reuse their payment; servicing corrections use servicing history and a reason; specialized money corrections use their own pages. Explain backups before corrections.

Acceptance: copy matches actual labels, searchable on phone, no unsupported features, no long manual, navigation links tested, financial terms verified, and optional orientation persists per user/session without adding authentication scope.

## Controlled code cleanup

Before editing, create a verified database backup and Git checkpoint. Inventory call sites with repository search, including tests, navigation, indirect imports and database triggers. Remove only helpers/imports with no callers and evidence of obsolete behavior. Consolidate duplicate period/calculation SQL where tests establish identical definitions. Investigate import-reload workarounds and server file-watch behavior, retaining recovery functionality until a tested replacement exists.

Keep migrations, financial constraints, correction snapshots, restore tooling and indirectly used services. Use small commits with unit/AppTest and disposable PostgreSQL regression checks. Prioritize report query batching and a consistent read snapshot after profiling. Do not begin a broad rewrite.
