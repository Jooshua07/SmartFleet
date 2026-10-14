"""Task guides: update alongside the corresponding page/workflow."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Guide:
    id: str
    question: str
    category: str
    steps: tuple[str, ...]
    example: str = ''
    note: str = ''
    section: str = 'How-To Guides'


GUIDES = (
    Guide('cashing', 'How do I record Thursday/Sunday cashing?', 'Cashing and expenses', (
        'Open More > Record Cashing. Use today\'s date, or turn on Backfill / edit date to choose another date.',
        'Check the coverage dates and Bus(es). On Thursdays, select Sunday workers only for buses that worked that Sunday.',
        'Use Standard for a combined receipt, or Adjust Buses when you know each bus\'s actual amount.',
        'Check Actual received (K), add any explanation, then select Save cashing or Save adjusted cashing.',
    ), 'For AIH 2715, AIG 5301 and AIF 9681, record the money actually received, not just the expected amount.',
       'Standard allocations may be estimates. A shortage is not automatically a confirmed debt.'),
    Guide('backfill', 'How do I enter cashing from a previous date?', 'Cashing and expenses', (
        'Open More > Record Cashing.',
        'Turn on Backfill / edit date and choose the original Thursday or Sunday in Collection date.',
        'Check the historical coverage, buses and Sunday workers, then enter the actual received amount.',
        'Check Recent cashing for an existing receipt before saving.',
    ), note='Eligible buses depend on recorded active history for the covered days. Do not change the date simply to make a bus appear.'),
    Guide('bus_expense', 'How do I record an expense for a specific bus?', 'Cashing and expenses', (
        'Open More > Record Expense and choose Specific Bus.',
        'Select the bus, actual Expense date and Category.',
        'Enter Amount (K), a short Expense title, Paid to and Receipt/reference where known.',
        'Add details in Notes, check the amount and select Save expense.',
    ), 'A tyre repair for AIH 2715 belongs to AIH 2715, not to the other buses.'),
    Guide('general_expense', 'How do I record general business expenses?', 'Cashing and expenses', (
        'Open More > Record Expense and keep General Business selected.',
        'Enter the actual date, category, amount and short title.',
        'Add supplier/reference details and Notes, then select Save expense.',
    ), 'Office costs used by the whole business stay General; they are not divided across AIH 2715, AIG 5301 and AIF 9681.'),
    Guide('edit_expense', 'How do I edit an expense or correct an incorrect entry?', 'Cashing and expenses', (
        'Open More > Record Expense and find the entry in Recent expenses.',
        'Use Find older expenses > Show latest to display a longer history.',
        'Select Edit, correct the details and select Update expense.',
        'If a payment never happened or was duplicated, review it carefully before Delete > Confirm delete.',
    ), note='Editing an ordinary expense updates the same payment. Servicing, loans, salaries and owner money must be corrected in their own workflow.', section='Fixing Mistakes'),
    Guide('add_bus', 'How do I add or edit a bus?', 'Buses and servicing', (
        'To add, open More > Add Bus, enter the details and use Next through the setup steps.',
        'Choose the route and driver details where available, then select Submit/Add Bus.',
        'To edit, open Buses > Buses, find the registration and select Edit.',
        'Correct the details or Next Servicing Date and select Save bus.',
    ), 'Check that AIG 5301 is not already registered before adding it.'),
    Guide('status', 'How do I deactivate or reactivate a bus?', 'Buses and servicing', (
        'Open Buses > Buses and find the registration.',
        'Select Deactivate or Reactivate.',
        'Enter the actual Effective date and a reason, then save the status change.',
    ), 'If AIF 9681 stopped operating because it was in the garage, deactivate it with that reason.',
       'Historical cashing and active-day calculations use the effective date; the old records remain.'),
    Guide('servicing', 'How do I record completed servicing?', 'Buses and servicing', (
        'Open More > Record Servicing, or select Record Servicing on the bus card.',
        'Choose the bus and Actual completion date.',
        'Enter mechanic labour, mechanic transport and other costs; check Total servicing cost.',
        'For paid servicing, enter the actual payment date and select Record servicing.',
    ), 'Servicing for AIH 2715 is linked to that bus. A genuinely free service can have zero costs.',
       'This form records completed, paid or zero-cost servicing. Ask an administrator about unpaid servicing; do not invent a payment.'),
    Guide('warnings', 'What do yellow, red and overdue servicing warnings mean?', 'Buses and servicing', (
        'More than 14 days remaining: normal.',
        '8-14 days remaining: yellow warning.',
        '0-7 days remaining: red urgent warning.',
        'Past the due date: red overdue warning.',
    ), note='Warnings do not mean servicing has been completed. Record the real completion when it happens.'),
    Guide('cycle', 'How does the five-week servicing schedule work?', 'Buses and servicing', (
        'The usual interval is 35 calendar days.',
        'After saving a completion, the next date is calculated from the latest valid Actual completion date.',
        'Check the next date in Buses. An incorrect schedule can be corrected in Edit > Next Servicing Date.',
    ), 'If AIH 2715 is serviced on 16 October 2026, the next date is 20 November, even if you enter it later.',
       'Passing the due date does not restart the timer. A backdated older service does not replace a newer completion.'),
    Guide('salary', 'How do I record a driver\'s salary?', 'Drivers', (
        'Open More > Driver Money, select Driver and Record Salary.',
        'Choose Salary year and Salary month; check Gross earned and Suggested recovery.',
        'Enter Payment date and check Advance recovery (K) and any other deductions.',
        'Confirm the payment details, then select Save salary.',
    ), note='Choose the earned payroll month separately from the date cash was paid. A salary is recorded once per employment and month.'),
    Guide('advance', 'How do I give a salary advance?', 'Drivers', (
        'Open More > Driver Money and select the driver.',
        'Choose Record Advance, then enter the actual Advance date and amount.',
        'Add a reason/notes and select Save advance.',
        'Check Outstanding advances before giving another advance.',
    ), note='The outstanding advance limit is enforced. An advance is money paid early, not an extra salary cost.'),
    Guide('recovery', 'How is an advance deducted from the next salary?', 'Drivers', (
        'Open the driver\'s Record Salary view.',
        'Check Suggested recovery against the advance history.',
        'Confirm Advance recovery (K) and the actual payment date, then save the salary.',
    ), 'Example: K2,500 earned salary minus K1,000 already advanced leaves K1,500 to pay, if there are no other deductions.',
       'The salary cost stays K2,500; the advance is not counted again as an extra expense.'),
    Guide('loan', 'How do I add a business loan?', 'Loans and owner money', (
        'Open More > Loans and choose Add Loan.',
        'Enter Loan name, Lender/company/association, Original principal (K) and Start date.',
        'Enter repayment terms only when known, add notes and select Save loan.',
    ), note='Original principal must be known. If it is unknown, keep the real repayment unidentified rather than inventing a loan balance.'),
    Guide('repay', 'How do I repay Carecoop or another lender?', 'Loans and owner money', (
        'Open More > Loans > Record Repayment and select the loan, or Unidentified loan if necessary.',
        'Choose Business funds when the business paid.',
        'Enter Repayment date, Principal paid (K), any Interest/fees (K), Paid to and Reference.',
        'Add notes identifying what is known and select Save repayment.',
    ), note='Principal reduces the loan and Business Balance; interest/fees are operating costs. Do not put the entire payment in ordinary expenses again.'),
    Guide('owner_external', 'What happens when the owner pays a business loan using personal money?', 'Loans and owner money', (
        'Open Loans > Record Repayment and choose Owner personal funds.',
        'Alternatively, open Owner Money > Owner Pays Business Loan; use only one of these entry points.',
        'Select the loan, record the actual date, principal, fees and reference, then save.',
    ), 'Example: the owner personally pays Carecoop K5,000. The business owes the owner K5,000; business cash does not decrease.',
       'Do not record the same personal payment twice.'),
    Guide('repay_owner', 'How do I record repayments to the owner?', 'Loans and owner money', (
        'Open More > Owner Money and check Owed to owner.',
        'Choose Business Repays Owner.',
        'Enter the actual date, amount and notes, then select Save repayment.',
    ), note='This reduces business cash and the amount owed to the owner. Owner Drawing is a separate personal withdrawal, not debt repayment.'),
    Guide('balance', 'How do I understand Business Balance?', 'Reports and finances', (
        'Open Finance > Balances. Business Balance Now shows today\'s recorded business cash position.',
        'Select a period below it. Money Received and Money Paid Out show only those dates.',
        'Open Reports for the balance at the start and end of a historical period.',
    ), 'Example: you start with K3,200, receive K12,000 and pay K9,000; the ending balance is K6,200.',
       'Changing the period never resets the current balance. Internal transfers do not change total business cash.', section='Understanding Your Money'),
    Guide('costs', 'What is the difference between operating costs and other payments?', 'Reports and finances', (
        'Operating costs are costs of running the business: repairs, servicing, office costs and earned salaries.',
        'Other Payments are business cash paid for principal repayments, owner drawings, recoverable advances and repayments to the owner.',
        'Both can reduce business cash, but only operating costs reduce operating contribution.',
    ), 'A K1,000 repair for AIG 5301 is an operating cost. K1,000 paid off loan principal is an Other Payment.',
       'Owner funding and borrowed money are financing, not cashing revenue.', section='Understanding Your Money'),
    Guide('compare', 'How do I compare bus performance?', 'Reports and finances', (
        'Open More > Bus Accounts and select the dates.',
        'Compare Recorded Revenue, Attributed Operating Costs and Recorded Contribution for each bus.',
        'Review Shared business costs separately and open the individual bus details.',
    ), 'Compare AIH 2715, AIG 5301 and AIF 9681 over the same dates.',
       'Recorded cashing is driver remittance, not total passenger fares. Estimated allocations are not confirmed bus receipts.'),
    Guide('graph', 'How do I read the Home financial graph?', 'Reports and finances', (
        'Use Chart period: Month, 3 Months or 6 Months. It is separate from the other Home filter.',
        'Total Revenue adds up recorded cashing; Total Expenses adds up operating costs.',
        'Business Balance follows actual cash, including loan/owner movements and advances.',
        'Swipe sideways for more dates and inspect a point for its amounts.',
    ), note='Thursday/Sunday points include earlier between-date activity. A labelled period-end point includes trailing activity. Revenue does not decrease when an expense occurs.'),
    Guide('months', 'How do I view previous months?', 'Reports and finances', (
        'Open Finance or More > Reports and choose Custom.',
        'Choose the first and last dates of the month you want.',
        'Check the displayed dates before reading the totals.',
    ), 'For October, choose 1 October through 31 October. Finance\'s Business Balance Now still shows today; Reports shows historical opening/closing balances.',
       'Month means the current calendar month through today. 3 Months includes this month and the previous two.'),
    Guide('exports', 'How do I export reports?', 'Reports and finances', (
        'Open More > Reports and select the period.',
        'Scroll to Downloads and expand the summary you need.',
        'Choose CSV or Excel, or choose Complete Excel report for all five summaries.',
    ), note='Files contain the selected period\'s report figures. Use Excel if you want formatted dates and amounts.'),
    Guide('corrections', 'What are the Correction buttons for?', 'Loans and owner money', (
        'Use Correction only when a recorded payment or advance is wrong or duplicated.',
        'Review its history, enter a Correction reason and use the appropriate reverse/cancel action.',
        'For servicing, use Record Servicing > Servicing history > Correct servicing.',
    ), note='Reversals change balances. They do not attach an unidentified repayment to a lender. Leave genuine unidentified payments recorded and ask an administrator to link them safely.', section='Fixing Mistakes'),
    Guide('missing_bus', 'Why is a bus missing from cashing?', 'Troubleshooting', (
        'Check the collection and coverage dates.',
        'Open Buses, check the status filter and search for the registration.',
        'Review the historical active dates. Cashing needs eligible active history for the covered days.',
        'Ask an administrator to review missing history; do not invent active days or register the same bus twice.',
    ), section='Fixing Mistakes'),
    Guide('wrong_amount', 'What should I do about an incorrect amount?', 'Troubleshooting', (
        'Find the original record and compare its date, amount and reference with the real receipt.',
        'Use Edit for an ordinary expense; use the relevant cashing or servicing correction for those records.',
        'For a loan, salary or owner-money amount without a safe edit option, ask an administrator to review it.',
    ), note='Do not enter a second payment just to make the displayed total look right.', section='Fixing Mistakes'),
    Guide('negative', 'Why is the balance negative?', 'Troubleshooting', (
        'A negative recorded balance means payments exceed the starting balance plus recorded money received.',
        'Check Reports > Ledger reconciliation for the dates, money received and payments.',
        'Look for missing receipts/funding, duplicate payments or incorrect amounts and ask for review where needed.',
    ), 'Example: K0 + K16,200 received - K17,000 paid = -K800.',
       'This describes the records; a physical cash wallet cannot contain negative money. Never add fake income to hide the shortfall.', section='Fixing Mistakes'),
    Guide('duplicate', 'How do I handle duplicate records?', 'Troubleshooting', (
        'Compare dates, bus, amount, supplier and reference; equal amounts alone do not prove duplication.',
        'Keep the genuine record and use the duplicate\'s supported delete/correction workflow.',
        'For locked cashing, recovered advances or unsupported corrections, ask an administrator to review the linked records.',
    ), note='Create a backup from More > Backups before a significant correction. Never reverse a genuine payment merely because its lender is unknown.', section='Fixing Mistakes'),
)

CATEGORIES = tuple(dict.fromkeys(guide.category for guide in GUIDES))
SECTIONS = ('How-To Guides', 'Understanding Your Money', 'Fixing Mistakes')


def filter_guides(query: str = '', category: str = 'All') -> tuple[Guide, ...]:
    terms = query.casefold().split()
    return tuple(guide for guide in GUIDES
                 if (category == 'All' or guide.category == category)
                 and all(term in ' '.join((guide.question, *guide.steps, guide.example, guide.note)).casefold()
                         for term in terms))
