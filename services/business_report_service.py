"""Read-only, period-aware reports using the financial source services."""
from collections import defaultdict
from datetime import date
from decimal import Decimal

from psycopg.rows import dict_row

from database.connection import get_connection
from services.bus_account_service import get_bus_contribution_summary
from services.finance_service import get_period_balance, get_period_ledger
from services.maintenance_service import get_servicing_history, get_servicing_schedules
from services.performance_service import get_operating_summary, EXCLUDED_OPERATING_EXPENSE_CATEGORIES
from services.preset_service import get_reporting_baseline_date
from services.report_service import get_collection_export, get_expense_export


ZERO = Decimal('0')


def _query(query, params=()):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()


def get_business_report(start_date: date, end_date: date) -> dict:
    if start_date > end_date:
        raise ValueError('End date must be on or after start date.')
    summary = get_operating_summary(start_date,end_date)
    balance = get_period_balance(start_date,end_date)
    collections = get_collection_export(start_date,end_date)
    expenses = get_expense_export(start_date,end_date)
    operating_expenses = [row for row in expenses if row['category'] not in EXCLUDED_OPERATING_EXPENSE_CATEGORIES]
    bus_summary = get_bus_contribution_summary(start_date,end_date)
    statuses = _query('''SELECT b.id AS bus_id,
        COUNT(DISTINCT day) FILTER(WHERE h.status='ACTIVE') AS active_days,
        COUNT(DISTINCT day) FILTER(WHERE h.status='INACTIVE') AS deactivated_days,
        COUNT(DISTINCT day) FILTER(WHERE h.id IS NULL) AS unknown_days
        FROM buses b CROSS JOIN generate_series(%s::date,%s::date,INTERVAL '1 day') day
        LEFT JOIN bus_status_history h ON h.bus_id=b.id AND h.effective_from <= day::date
          AND (h.effective_to IS NULL OR h.effective_to >= day::date)
        GROUP BY b.id''',(start_date,end_date))
    status_by_bus = {row['bus_id']:row for row in statuses}
    expected = _query('''SELECT r.bus_id, SUM(r.expected_amount) AS expected_cashing,
        COUNT(*) FILTER(WHERE r.expected_amount IS NULL) AS unknown_expected
        FROM remittances r JOIN remittance_collections c ON c.id=r.collection_id
        WHERE c.collection_date BETWEEN %s AND %s GROUP BY r.bus_id''',(start_date,end_date))
    expected_by_bus = {row['bus_id']:row for row in expected}
    history = get_servicing_history(start_date=start_date,end_date=end_date)
    schedules = get_servicing_schedules()
    due_by_bus = {row['bus_id']:row for row in schedules}
    for bus in bus_summary['buses']:
        bus.update(status_by_bus.get(bus['bus_id'],{}))
        bus.update(expected_by_bus.get(bus['bus_id'],{'expected_cashing':None,'unknown_expected':0}))
        if bus['unknown_expected']:
            bus['expected_cashing']=None
        bus['difference'] = bus['recorded_revenue']-bus['expected_cashing'] if bus['expected_cashing'] is not None else None
        events=[row for row in history if row['bus_id']==bus['bus_id']]
        bus['servicing_events']=len(events)
        bus['servicing_costs']=sum((row['total_cost'] for row in events),ZERO)
        bus['next_servicing_due']=due_by_bus.get(bus['bus_id'],{}).get('next_due_date')
    categories=defaultdict(lambda:ZERO)
    for row in operating_expenses:
        categories[row['category']]+=row['amount']
    if summary['salary_costs']:
        categories['Earned driver salaries']+=summary['salary_costs']
    if summary['other_costs']:
        categories['Other operating payments']+=summary['other_costs']
    salaries=_query('''SELECT d.full_name AS driver, make_date(s.salary_year,s.salary_month,1) AS payroll_month,
        s.prorated_salary AS salary_cost,s.net_salary,s.advance_recovery,s.payment_date,s.status
        FROM driver_salaries s JOIN driver_employments e ON e.id=s.employment_id
        JOIN drivers d ON d.id=e.driver_id WHERE s.status<>'CANCELLED'
        AND (make_date(s.salary_year,s.salary_month,1) BETWEEN %s AND %s OR s.payment_date BETWEEN %s AND %s)
        ORDER BY payroll_month,driver''',(start_date,end_date,start_date,end_date))
    advances=_query('''SELECT a.id,d.full_name AS driver,a.advance_date,a.amount,
        a.amount-COALESCE((SELECT SUM(r.amount) FROM salary_advance_recoveries r
            JOIN driver_salaries s ON s.id=r.salary_id WHERE r.advance_id=a.id
            AND s.status<>'CANCELLED' AND s.payment_date<=%s),0) AS outstanding
        FROM driver_advances a JOIN driver_employments e ON e.id=a.employment_id
        JOIN drivers d ON d.id=e.driver_id WHERE a.status<>'CANCELLED' AND a.advance_date<=%s
        ORDER BY a.advance_date,driver''',(end_date,end_date))
    loans=_query('''SELECT l.loan_name,l.lender,l.original_amount,l.start_date,
        l.original_amount-COALESCE(SUM(r.amount),0) AS outstanding_principal
        FROM business_loans l LEFT JOIN loan_repayments r ON r.loan_id=l.id AND r.repayment_date<=%s
        WHERE l.start_date<=%s GROUP BY l.id ORDER BY l.loan_name''',(end_date,end_date))
    repayments=_query('''SELECT r.repayment_date,r.amount,r.payment_source,l.loan_name,l.lender,
        r.loan_id,r.owner_loan_transaction_id,r.financial_transaction_id FROM loan_repayments r
        LEFT JOIN business_loans l ON l.id=r.loan_id WHERE r.repayment_date BETWEEN %s AND %s
        ORDER BY r.repayment_date,r.id''',(start_date,end_date))
    owner=_query('''SELECT transaction_date,transaction_type,amount,description FROM owner_loan_transactions
        WHERE transaction_date BETWEEN %s AND %s ORDER BY transaction_date,id''',(start_date,end_date))
    owner_balance=_query('''SELECT COALESCE(SUM(CASE WHEN transaction_type='OWNER_FUNDED' THEN amount ELSE -amount END),0) AS balance
        FROM owner_loan_transactions WHERE transaction_date<=%s''',(end_date,))[0]['balance']
    known_expected = sum((row['expected_cashing'] for row in bus_summary['buses'] if row['expected_cashing'] is not None),ZERO)
    expected_complete = all(row['expected_cashing'] is not None for row in bus_summary['buses']) and bool(collections)
    result=dict(start=start_date,end=end_date,operating=summary,balance=balance,collections=collections,
        expenses=operating_expenses,buses=bus_summary['buses'],shared_costs=bus_summary['shared_general_costs'],
        categories=[{'Category':key,'Amount (K)':value} for key,value in sorted(categories.items(),key=lambda item:item[1],reverse=True)],
        history=history,schedules=schedules,salaries=salaries,advances=advances,loans=loans,
        repayments=repayments,owner=owner,owner_balance=owner_balance,
        expected=known_expected if expected_complete else None)
    result['warnings']=get_report_warnings(start_date,end_date,result)
    return result


def get_reconciliation(end_date: date) -> dict:
    baseline=get_reporting_baseline_date()
    if end_date<baseline:
        raise ValueError('Reconciliation end date must be on or after the reporting baseline.')
    rows=get_period_ledger(baseline,end_date)
    result=get_period_balance(baseline,end_date)
    grouped=defaultdict(lambda:ZERO)
    for row in rows:
        if row['transaction_type']!='TRANSFER':
            grouped[(row['transaction_type'],row['direction'])]+=row['amount']
    result['movements']=[{'Movement':kind.replace('_',' ').title(),'Direction':direction,'Amount (K)':amount}
        for (kind,direction),amount in sorted(grouped.items())]
    result['ledger']=rows
    return result


def get_report_warnings(start_date, end_date, report=None):
    checks=[
        ('''SELECT COUNT(*) AS count FROM remittance_collections WHERE collection_date BETWEEN %s AND %s AND unallocated_amount>0''', 'Cashing received still needs bus allocation.'),
        ('''SELECT COUNT(*) AS count FROM loan_repayments WHERE repayment_date BETWEEN %s AND %s AND loan_id IS NULL''','A loan repayment needs its lender or loan identified.'),
        ('''SELECT COUNT(*) AS count FROM loan_repayments r LEFT JOIN owner_loan_transactions o ON o.id=r.owner_loan_transaction_id
            WHERE r.repayment_date BETWEEN %s AND %s AND r.payment_source='OWNER_PERSONAL'
            AND (o.id IS NULL OR o.amount<>r.amount OR o.financial_transaction_id IS NOT NULL)''','An owner-paid loan settlement needs its owner funding link checked.'),
        ('''SELECT COUNT(*) AS count FROM expenses e LEFT JOIN financial_transactions f ON f.id=e.financial_transaction_id
            WHERE e.expense_date BETWEEN %s AND %s AND e.payment_source='BUSINESS_ACCOUNT'
            AND (f.id IS NULL OR f.amount<>e.amount OR f.transaction_date<>e.expense_date)''','An expense payment does not match its money record.'),
        ('''SELECT COUNT(*) AS count FROM maintenance m LEFT JOIN expenses e ON e.id=m.expense_id
            WHERE m.completed_date BETWEEN %s AND %s AND m.is_servicing AND m.status='COMPLETED'
            AND ((m.total_cost>0 AND (e.id IS NULL OR m.payment_date IS NULL OR e.amount<>m.total_cost))
              OR (m.total_cost=0 AND e.id IS NOT NULL))''','A servicing event needs its cost or payment status checked.'),
        ('''SELECT COUNT(*) AS count FROM driver_salaries s WHERE s.payment_date BETWEEN %s AND %s AND s.status<>'CANCELLED'
            AND s.advance_recovery<>COALESCE((SELECT SUM(r.amount) FROM salary_advance_recoveries r WHERE r.salary_id=s.id),0)''','A salary advance recovery needs checking.'),
        ('''SELECT COUNT(*) AS count FROM bus_status_history a JOIN bus_status_history b ON a.bus_id=b.bus_id AND a.id<b.id
            WHERE a.effective_from<=%s AND COALESCE(a.effective_to,'infinity'::date)>=%s
            AND daterange(a.effective_from,a.effective_to,'[]') && daterange(b.effective_from,b.effective_to,'[]')''','A bus has overlapping historical status dates.'),
        ('''SELECT COUNT(*) AS count FROM expenses e JOIN expense_categories c ON c.id=e.category_id
            JOIN financial_transactions f ON f.id=e.financial_transaction_id WHERE e.expense_date BETWEEN %s AND %s
            AND c.name IN ('Loan Repayments','Driver Advances','Owner Drawings','Driver Salaries') AND f.transaction_type='EXPENSE' ''','A specialized payment is still classified as an ordinary expense.'),
    ]
    warnings=[]
    for query,message in checks:
        params=(end_date,start_date) if 'bus_status_history a' in query else (start_date,end_date)
        if _query(query,params)[0]['count']:
            warnings.append(message)
    if report:
        if any(row['unknown_days'] for row in report['buses']):
            warnings.append('Some bus days have no confirmed status history.')
        if report['expected'] is None:
            warnings.append('Expected cashing is incomplete; no full-period shortfall is inferred.')
        if sum((row['Amount (K)'] for row in report['categories']),ZERO)!=report['operating']['expenses']:
            warnings.append('Operating cost breakdown differs from the business total.')
        if sum((row['recorded_revenue'] for row in report['buses']),ZERO)!=report['operating']['revenue']:
            warnings.append('Recorded cashing differs from its bus allocations.')
        if report['balance']['collections']!=report['operating']['revenue']:
            warnings.append('Cashing receipts differ from their ledger total.')
    return warnings
