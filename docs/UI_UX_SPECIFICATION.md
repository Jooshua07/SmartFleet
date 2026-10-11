# SmartFleet UI and UX specification

Last updated: 2026-10-11

This document records the approved phone-first design direction from `docs/ui-references/`. The screenshots are visual references, not real data specifications. Do not copy mockup figures, dates, names, unsupported statuses or unsupported fields into production UI.

## Current UI state

An initial Streamlit UI foundation has been implemented. `app.py` defines explicit navigation, `app_pages/` contains the first page scripts, and `components/` contains reusable layout/card/form helpers. The current UI is a functional foundation, not the final polished screenshot match.

## Design principles

- Phone-first. Test narrow screens before desktop.
- Real data only. Empty states are better than fake records.
- White and light-grey content surfaces.
- Deep navy header and navigation.
- Blue primary actions and selected navigation.
- Limited green, amber and red status colors.
- Rounded but restrained cards.
- Clear hierarchy, readable labels and large touch targets.
- Minimal animation beyond loading skeletons and native feedback.
- Business terminology should match the owner's language, especially `Record Cashing`.

## Visual references inspected

| File | Screen |
| --- | --- |
| `docs/ui-references/01_Home.png` | Home dashboard |
| `docs/ui-references/02_Buses.png` | Buses, Routes and Drivers tabs |
| `docs/ui-references/03_Record_Cashing.png` | Record Cashing form |
| `docs/ui-references/04_Finance_General.png` | Finance general tab |
| `docs/ui-references/05_Finance_Collections.png` | Finance collections tab |
| `docs/ui-references/06_Finance_Expenses.png` | Finance expenses tab |
| `docs/ui-references/07_Reminders.png` | Reminders page |
| `docs/ui-references/08_Add_Bus_Step1.png` | Add Bus step 1 |
| `docs/ui-references/09_Add_Bus_Step2.png` | Add Bus step 2 |

## Page hierarchy

Primary mobile navigation:

```text
Home | Buses | Finance | More
```

Quick actions available through the menu or More section:

- Record Cashing
- Record Expense
- Add Bus
- Drivers
- Reminders

Internal page tabs:

- Buses page: Buses, Routes, Drivers.
- Finance page: General, Collections, Expenses, Balances.

## Navigation behavior

- The selected primary item must be visually clear.
- Bottom navigation must not cover forms or primary buttons.
- On narrow screens, the navigation should keep labels short and touch targets comfortable.
- The app uses supported Streamlit navigation APIs. `st.navigation` is configured with hidden native navigation, and a custom bottom action row is rendered with `st.bottom`. Browser/mobile verification is still required before treating it as final.
- Avoid CSS selectors that depend on Streamlit's internal class names.
- Do not create a separate inconsistent sidebar navigation unless it is the documented fallback.

## Colors

Recommended token direction:

| Role | Color direction |
| --- | --- |
| Primary navy | Header and bottom navigation background |
| Primary blue | Main buttons, selected navigation, active tab underline |
| Light blue | Selected/filter backgrounds and contextual panels |
| Light grey | App background and dividers |
| White | Cards and forms |
| Green | Active, success, positive cashing/collection values |
| Amber | Warning, due soon, pending |
| Red | Deactivated, overdue, errors, expenses where appropriate |

Configure theme tokens through `.streamlit/config.toml` where possible. Use custom CSS only when native Streamlit features cannot meet a required interaction or layout.

## Typography

- Use Streamlit's system font stack unless a theme change is approved.
- Use sentence casing in implementation labels where practical.
- Use strong, compact headings inside cards and panels.
- Avoid oversized display text inside dense operational screens.
- Ensure all button text fits on 320px wide screens.

## Components

Shared components should exist for:

- App header.
- Bottom or fallback navigation.
- Quick-action menu.
- KPI cards.
- Status badges.
- Search and filters.
- Bus cards.
- Financial list rows.
- Reminder sections and rows.
- Mobile-friendly forms.
- Loading skeletons.
- Empty states.
- Error, warning, success and info messages.
- Confirmation dialogs.

Prefer native Streamlit widgets and Material Symbols icons:

- `st.metric` for KPI cards where possible.
- `st.container(border=True)` for cards.
- `st.segmented_control` for Week/Month and other 2-5 option controls.
- `st.pills` for small status filters.
- `st.selectbox` for bus, route, driver and account selections.
- `st.form` for write operations.
- `st.skeleton` for loading placeholders.

## Screen specifications

### Home

Required sections in order:

1. Financial summary cards:
   - Total Revenue.
   - Total Expenses.
   - Use real period-derived figures.
2. Bus status strip:
   - `ALL BUSES ACTIVE` when applicable.
   - Otherwise active/deactivated counts.
   - Empty-fleet state when there are no buses.
3. Bus revenue vs expenses chart:
   - Grouped bars by bus.
   - Revenue and expenses in ZMW.
   - Use only validated allocation rules.
4. Alerts and reminders:
   - Show the three most relevant real alerts.
   - Link to Reminders.
5. Recent Activity:
   - Use real cashing, expense, bus status, maintenance or other domain records.
   - Do not invent an audit trail.

### Buses

Tabs: Buses, Routes, Drivers.

Buses tab:

- Search by bus registration, driver or route where supported by actual joins.
- Filter chips: All, Active, In Garage, Deactivated.
- Map user-facing Deactivated to `buses.status = 'INACTIVE'`.
- Do not implement In Garage until a safe definition is selected. A possible future definition is active maintenance/downtime, not a third bus status.
- Bus cards should show registration, status, assigned driver and route.
- Handle missing driver honestly.
- Actions: Edit and Deactivate for active buses, Activate for deactivated buses where allowed.
- Prominent Add New Bus action.

Routes tab:

- List routes.
- Add route.
- Edit route.
- Activate/deactivate route where supported.
- Respect bus assignment dependencies.

Drivers tab:

- List drivers.
- Show employment and assignment state.
- Actions should preserve historical employment and assignment records.

### Record Cashing

User-facing title: `Record Cashing`.

Primary fields only:

- Bus.
- Amount (K).
- Date, defaulting to the business date.
- Notes, optional.

Context:

- Show assigned driver as read-only information after bus selection.
- Driver lookup must be based on the selected cashing date.

Do not require:

- Route selection.
- Received From.
- Transaction Type.

Submission:

- Primary button: `Record Cashing`.
- Use a form to avoid rerunning on every field change.
- Prevent double submission.
- Show confirmation only after database persistence succeeds.

### Finance

Tabs: General, Collections, Expenses, Balances.

General:

- Week/Month segmented control.
- Week selected by default.
- Period selector.
- Cards for Total Collections, Total Expenses and Pending Remittances.
- Show balance only when the calculation is fully defined.
- Recent Activity from real records.

Collections:

- Group entries by date.
- Each row: bus/registration, driver name for the historical date and amount.
- Allow opening an entry for details.

Expenses:

- Total expenses summary for selected period.
- Search and filter controls.
- Rows with date, category/expense name, amount, bus or company-wide designation.
- Opening a row shows notes, allocations and payment source details.
- Do not add fuel tracking.

Balances:

- Answer how much money the business should have and how much is accounted for.
- Use financial accounts and transactions only where definitions are reliable.
- Avoid double-counting transfers.
- Do not invent opening balances.

### Record Expense

Form fields:

- Expense category.
- Amount (K).
- Date.
- Bus-level or company-wide designation.
- Required bus or allocation details when relevant.
- Payment source where required by schema.
- Account where paid from a business account.
- Optional notes.

Preserve `BUS`, `MULTI_BUS` and `GENERAL` expense scope rules.

### Reminders

Sections:

- Maintenance due in the next 21 days.
- Deactivated buses.
- Document expiry where stored or manually entered as reminders.
- Missing or pending cashing only when supported by schedule rules.
- Other stored reminders.

Differentiate:

- Overdue.
- Due soon.
- Informational.
- Completed or dismissed where supported.

### Add Bus wizard

The current implemented wizard is a schema-supported version of the required three-step flow. It explicitly warns that model, seating capacity and document upload persistence are not available yet.

Target three-step flow:

1. Basic information:
   - Registration Number.
   - Bus Model only if schema support is approved.
   - Seating Capacity only if schema support is approved.
2. Assignment:
   - Route.
   - Driver.
   - Initial Status.
   - Additional Information / Notes.
3. Documents and review:
   - Optional document information only if persistence is available.
   - Review entered data.
   - Submit/Add Bus.

Current schema issue:

- `buses` supports registration number, route, status, acquisition date and notes.
- It does not support bus model, seating capacity or uploaded documents.
- The wizard must not silently discard unsupported fields or store them in notes as structured data.

## Empty states

Use direct empty-state messages:

- No buses registered yet.
- No drivers registered yet.
- No collections for this period.
- No expenses for this period.
- No reminders due.
- No maintenance schedules configured.

Empty states may offer a relevant action, such as Add Bus or Add Route.

## Loading states

Use skeletons shaped like the final content:

- KPI card skeletons.
- Bus-list row/card skeletons.
- Chart skeletons.
- Finance list skeletons.
- Reminder section skeletons.

Do not show fake operational data while loading.

## Error and success states

- Use `st.error` for blocked operations.
- Use `st.warning` for incomplete definitions or non-blocking risks.
- Use `st.success` or `st.toast` only after confirmed persistence.
- Keep technical details out of user-facing errors in production.

## Accessibility and touch interaction

- Inputs and controls should have accessible labels.
- Touch targets should be approximately 44px or larger.
- Icons should have text or clear labels/tooltips.
- Color should not be the only indicator of status.
- Charts need accessible `alt=` descriptions.
- Inputs must remain usable with mobile keyboards.

## Streamlit limitations and trade-offs

- Streamlit native navigation does not directly provide the exact mockup bottom nav. A verified implementation using `st.bottom`, native navigation state and minimal stable CSS may be needed.
- Hidden tab content can still compute unless gated. Expensive tabs should be guarded by tab open state where supported.
- UI screenshots include unsupported items such as In Garage, model, seating capacity, document details and fake data. These require schema/business decisions before implementation.
- A production-grade mobile shell may need additional frontend technology in the future, but Streamlit remains the approved MVP stack for now.
