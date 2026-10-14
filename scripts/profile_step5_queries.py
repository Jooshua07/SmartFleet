"""Measure financial query counts without changing database records."""
from datetime import date
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services import performance_service, finance_service, business_report_service


class CountingCursor:
    def __init__(self,cursor,counter):
        self.cursor=cursor
        self.counter=counter

    def __enter__(self):
        self.cursor.__enter__()
        return self

    def __exit__(self,*args):
        return self.cursor.__exit__(*args)

    def execute(self,*args,**kwargs):
        self.counter[0]+=1
        return self.cursor.execute(*args,**kwargs)

    def __getattr__(self,key):
        return getattr(self.cursor,key)


class CountingConnection:
    def __init__(self,conn,counter):
        self.conn=conn
        self.counter=counter

    def __enter__(self):
        self.conn.__enter__()
        return self

    def __exit__(self,*args):
        return self.conn.__exit__(*args)

    def cursor(self,*args,**kwargs):
        return CountingCursor(self.conn.cursor(*args,**kwargs),self.counter)


def main():
    for name,fn,expected in [('operating summary',performance_service.get_operating_summary,2),
                            ('performance series',performance_service.get_business_performance_series,1),
                            ('financial timeline',performance_service.get_business_financial_timeline,3)]:
        count=[0]
        perf=performance_service.get_connection
        fin=finance_service.get_connection
        with patch.object(performance_service,'get_connection',side_effect=lambda:CountingConnection(perf(),count)), \
             patch.object(finance_service,'get_connection',side_effect=lambda:CountingConnection(fin(),count)):
            fn(date(2026,10,1),date(2026,10,14))
        assert count[0]==expected,(name,count[0])
        print(f'{name}: {count[0]} measured SQL executions')
    count=[0]
    original=business_report_service.get_connection
    def connect():
        count[0]+=1
        return original()
    with patch.object(business_report_service,'get_connection',side_effect=connect):
        business_report_service.get_report_warnings(date(2026,10,1),date(2026,10,14))
    assert count[0]==1
    print('Report warnings: 1 measured connection, previously 11')


if __name__=='__main__':
    main()
