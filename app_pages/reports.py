import pandas as pd
import streamlit as st

from components.reporting_period import period_controls
from services.business_report_service import get_business_report
from services.maintenance_service import servicing_warning
from utils.dates import today_lusaka
from utils.formatting import format_date, format_whole_kwacha as money


@st.cache_data(ttl=15, max_entries=32, show_spinner=False)
def _load_report(start,end):
    return get_business_report(start,end)


st.subheader('Business Report')
start,end=period_controls('reports',('Month','3 Months','6 Months','Custom'))
st.caption(f'{format_date(start)} to {format_date(end)}')
report=_load_report(start,end)
summary=report['operating']
balance=report['balance']
st.subheader('Business overview')
st.write(f"During {format_date(start)} to {format_date(end)}, the business recorded {money(summary['revenue'])} in cashing collections and {money(summary['expenses'])} in operating costs.")
contribution=summary['revenue']-summary['expenses']
st.write(f"Recorded operating contribution was {money(contribution)}." if summary['revenue'] or summary['expenses'] else 'No operating activity was recorded in this period.')
with st.container(horizontal=True):
    for label,value in [('Recorded cashing',summary['revenue']),('Operating costs',summary['expenses']),
                        ('Other payments',balance['other_payments']),('Operating contribution',contribution),
                        ('Opening Business Balance',balance['opening_balance']),('Closing Business Balance',balance['closing_balance'])]:
        st.metric(label,money(value),border=True)
if report['expected'] is not None:
    st.write(f"Recorded expected cashing: {money(report['expected'])}; received minus expected: {money(summary['revenue']-report['expected'])}.")
else:
    st.caption('Expected cashing is not fully recorded for this period.')
st.caption('Expected amounts use saved collection coverage and rates, not an invented full-calendar target.')

st.subheader('Bus performance')
for bus in report['buses']:
    with st.expander(bus['registration_number'],expanded=True):
        st.write(f"Recorded cashing {money(bus['recorded_revenue'])}; attributed costs {money(bus['attributed_costs'])}; recorded contribution {money(bus['recorded_contribution'])}.")
        if bus['estimated_revenue']:
            st.caption(f"{money(bus['estimated_revenue'])} of this bus allocation is estimated; the business receipt itself is recorded.")
        if bus['expected_cashing'] is not None:
            st.write(f"Expected cashing {money(bus['expected_cashing'])}; difference {money(bus['difference'])}.")
        else:
            st.caption('No complete expected cashing amount recorded.')
        st.write(f"{bus['active_days']} active days; {bus['deactivated_days']} deactivated days; {bus['unknown_days']} unconfirmed days.")
        st.write(f"{bus['servicing_events']} servicing events, costing {money(bus['servicing_costs'])}.")
        st.caption(f"Current next servicing: {format_date(bus['next_servicing_due'])}")
st.caption(f"Shared/general operating costs: {money(report['shared_costs'])}. These are not assigned to arbitrary buses.")

st.subheader('Expense summary')
st.write(f"General business expenses: {money(sum(row['amount'] for row in report['expenses'] if row['scope']=='GENERAL'))}.")
st.write(f"Bus and shared-bus expenses: {money(sum(row['amount'] for row in report['expenses'] if row['scope']!='GENERAL'))}.")
if report['categories']:
    st.dataframe(pd.DataFrame(report['categories']),hide_index=True,alt='Operating cost categories ranked by amount')
    largest=report['categories'][0]
    st.caption(f"Largest recorded cost category: {largest['Category']} ({money(largest['Amount (K)'])}).")
else:
    st.caption('No operating costs recorded.')

st.subheader('Maintenance summary')
if report['history']:
    st.dataframe(pd.DataFrame([{'Bus':row['registration_number'],'Completed':row['completed_date'],'Paid':row['payment_date'],'Cost (K)':row['total_cost']} for row in report['history']]),hide_index=True,alt='Completed servicing by bus')
else:
    st.caption('No completed servicing in this period.')
for row in report['schedules']:
    if row['next_due_date']:
        label=servicing_warning(row['next_due_date'],today_lusaka())
        text=f"{row['registration_number']}: {format_date(row['next_due_date'])} ({label})"
        if label in ('Urgent','Overdue'):
            st.error(text)
        elif label=='Warning':
            st.warning(text)
        else:
            st.caption(text)

st.subheader('Driver money summary')
salary_payments=sum((row['net_salary'] for row in report['salaries'] if row['status']=='PAID' and start<=row['payment_date']<=end),0)
recovered=sum((row['advance_recovery'] for row in report['salaries'] if row['status']=='PAID' and start<=row['payment_date']<=end),0)
given=sum((row['amount'] for row in report['advances'] if start<=row['advance_date']<=end),0)
outstanding=sum((row['outstanding'] for row in report['advances']),0)
st.write(f"Earned salary costs {money(summary['salary_costs'])}; net salary payments {money(salary_payments)}.")
st.write(f"Advances given {money(given)}; recovered {money(recovered)}; outstanding at period end {money(outstanding)}.")
st.caption('Earned salaries are recognized in their payroll month; advance recovery reduces the cash paid, not salary cost.')

st.subheader('Loan and owner money summary')
if report['loans']:
    st.dataframe(pd.DataFrame(report['loans']),hide_index=True,alt='Registered business loans and principal outstanding at period end')
else:
    st.caption('No registered loans; unidentified repayments do not imply a known opening principal.')
business_repaid=sum((row['amount'] for row in report['repayments'] if row['payment_source']=='BUSINESS_ACCOUNT'),0)
owner_external=sum((row['amount'] for row in report['repayments'] if row['payment_source']=='OWNER_PERSONAL'),0)
st.write(f"Loan principal paid from business funds {money(business_repaid)}; owner-paid external settlements {money(owner_external)}.")
st.write(f"Money owed to owner at period end: {money(report['owner_balance'])}.")
st.write(f"Owner drawings {money(balance['other_payment_breakdown'].get('OWNER_DRAWING',0))}; business repayments to owner {money(balance['other_payment_breakdown'].get('OWNER_LOAN_REPAYMENT',0))}.")

st.subheader('Data quality')
if report['warnings']:
    for warning in report['warnings']:
        st.warning(warning)
else:
    st.success('Report totals and recorded payment links agree.')
