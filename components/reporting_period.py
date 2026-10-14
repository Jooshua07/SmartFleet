import streamlit as st

from services.preset_service import get_reporting_baseline_date
from utils.dates import today_lusaka
from utils.reporting_periods import reporting_period


def period_controls(key: str, options=('Month', '3 Months', 'Custom'), label='Reporting period'):
    baseline = get_reporting_baseline_date()
    today = today_lusaka()
    mode = st.segmented_control(label, options, default='Month', key=f'{key}_period') or 'Month'
    start = end = None
    if mode == 'Custom':
        start = st.date_input('Start date', value=baseline, format='DD/MM/YYYY', key=f'{key}_start')
        end = st.date_input('End date', value=today, format='DD/MM/YYYY', key=f'{key}_end')
    try:
        return reporting_period(mode, baseline, today, start, end)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
