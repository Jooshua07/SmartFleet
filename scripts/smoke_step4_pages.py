from datetime import date
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import streamlit as st
from streamlit.testing.v1 import AppTest
from services.finance_service import get_period_balance
from utils.formatting import format_whole_kwacha


def main():
    root=Path(__file__).resolve().parents[1]
    for name in ('home','buses','finance','more','record_cashing','record_expense','record_servicing','accounts',
                 'business_presets','backups','reports','reminders','driver_money','loans','owner_money','add_bus'):
        st.cache_data.clear()
        app=AppTest.from_file(root/'app_pages'/f'{name}.py',default_timeout=30).run()
        assert not app.exception,(name,[row.message for row in app.exception])
    app=AppTest.from_file(root/'app_pages/finance.py',default_timeout=30).run()
    app.segmented_control(key='finance_period').set_value('Custom').run()
    app.date_input(key='finance_start').set_value(date(2026,10,1))
    app.date_input(key='finance_end').set_value(date(2026,10,4)).run()
    for section in ('Collections','Expenses','Balances','General'):
        app.segmented_control(key='finance_section').set_value(section).run()
        assert not app.exception
        assert app.session_state['finance_end']==date(2026,10,4)
        if section=='Balances':
            expected=get_period_balance(date(2026,10,1),date(2026,10,4))
            metric=next(row for row in app.metric if row.label=='Closing Business Balance')
            assert metric.value==format_whole_kwacha(expected['closing_balance'])
    app.date_input(key='finance_start').set_value(date(2026,10,10)).run()
    assert app.error and not app.exception
    app=AppTest.from_file(root/'app_pages/home.py',default_timeout=30).run()
    app.segmented_control(key='home_chart_period').set_value('6 Months').run()
    assert app.session_state['home_period']=='1 month'
    app.segmented_control(key='home_period').set_value('3 months').run()
    assert app.session_state['home_chart_period']=='6 Months'
    assert not app.exception
    print('16 live read-only pages PASS; Finance tab persistence, historical balances, invalid dates and independent Home controls PASS')


if __name__=='__main__':
    main()
