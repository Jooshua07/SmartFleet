import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from psycopg import sql
from psycopg.rows import dict_row
from database.connection import get_connection
from services.finance_service import get_period_balance
from services.preset_service import get_reporting_baseline_date
from utils.dates import today_lusaka


def main():
    original=json.loads(Path('backups/step4_before_snapshot.json').read_text(encoding='utf-8'))
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            for table,rows in original.items():
                if table=='maintenance_schedules':
                    continue
                cursor.execute(sql.SQL('SELECT * FROM {} ORDER BY id').format(sql.Identifier(table)))
                current=json.loads(json.dumps(cursor.fetchall(),default=str))
                assert current==rows, f'Live records changed in {table}; inspect before proceeding'
    result=get_period_balance(get_reporting_baseline_date(),today_lusaka())
    print('All original live financial and maintenance event records unchanged.')
    print('Current live reconciliation:', result)


if __name__=='__main__':
    main()
