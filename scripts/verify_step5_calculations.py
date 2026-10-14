"""Before/after calculation comparisons on real records, read-only."""
from datetime import date
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services.finance_service import get_business_balance, get_period_balance
from services.performance_service import get_operating_summary, get_business_performance_series, get_business_financial_timeline
from services.bus_account_service import get_bus_contribution_summary
from services.business_report_service import get_business_report, get_reconciliation
from services.report_export_service import report_export_tables

SNAPSHOT=Path('backups/step5_before_calculations.json')


def main():
    results={'business_balance':get_business_balance()}
    for start,end in [(date(2026,10,1),date(2026,10,4)),(date(2026,10,1),date(2026,10,31)),
                      (date(2026,11,1),date(2026,11,30)),(date(2026,12,1),date(2026,12,31))]:
        report=get_business_report(start,end)
        results[str(start)]={'balance':get_period_balance(start,end),'operating':get_operating_summary(start,end),
            'daily':get_business_performance_series(start,end),'weekly':get_business_performance_series(start,end,'Weekly'),
            'timeline':get_business_financial_timeline(start,end),'buses':get_bus_contribution_summary(start,end),
            'report':report,'exports':report_export_tables(report),'reconciliation':get_reconciliation(end)}
    results=json.loads(json.dumps(results,default=str))
    if '--capture' in sys.argv:
        if SNAPSHOT.exists():
            raise RuntimeError('Calculation baseline already exists; do not overwrite it.')
        SNAPSHOT.write_text(json.dumps(results,indent=2),encoding='utf-8')
        print('Captured October/historical/empty-month financial calculation baselines.')
    else:
        assert results==json.loads(SNAPSHOT.read_text(encoding='utf-8')), 'Calculation results changed; investigate'
        print('Balances, operating costs, daily/weekly charts, Bus Accounts, reports, exports and reconciliation match the before-cleanup baseline.')


if __name__=='__main__':
    main()
