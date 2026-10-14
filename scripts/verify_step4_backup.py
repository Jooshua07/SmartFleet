"""Restore a backup to a disposable database and compare live financial rows."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.backup_service import _find_tool, _load_database_settings, PG_RESTORE_CANDIDATES


def main():
    settings = _load_database_settings()
    backup = Path(sys.argv[1])
    name = f"smartfleet_restore_check_{int(time.time())}"
    kwargs = dict(host=settings['DB_HOST'], port=settings['DB_PORT'], user=settings['DB_USER'], password=settings['DB_PASSWORD'])
    with psycopg.connect(**kwargs, dbname='postgres', autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    try:
        env = os.environ.copy()
        env['PGPASSWORD'] = settings['DB_PASSWORD']
        result = subprocess.run([_find_tool('pg_restore', PG_RESTORE_CANDIDATES), '--exit-on-error', '--no-owner', '--host', settings['DB_HOST'], '--port', settings['DB_PORT'], '--username', settings['DB_USER'], '--dbname', name, str(backup)], env=env, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError('Disposable restore failed: ' + result.stderr)
        snapshots = []
        for dbname in (settings['DB_NAME'], name):
            with psycopg.connect(**kwargs, dbname=dbname, row_factory=dict_row) as conn:
                snapshot = {}
                for table in ('financial_transactions', 'expenses', 'remittance_collections', 'remittances', 'driver_salaries', 'loan_repayments', 'owner_loan_transactions', 'maintenance', 'maintenance_schedules'):
                    snapshot[table] = conn.execute(sql.SQL('SELECT * FROM {} ORDER BY id').format(sql.Identifier(table))).fetchall()
                snapshots.append(snapshot)
        assert snapshots[0] == snapshots[1], 'Restored records differ from live records'
        Path('backups/step4_before_snapshot.json').write_text(json.dumps(snapshots[0], default=str, indent=2), encoding='utf-8')
        print('Restore verified; financial and maintenance records match live database.')
        print({key: len(value) for key, value in snapshots[0].items()})
    finally:
        with psycopg.connect(**kwargs, dbname='postgres', autocommit=True) as conn:
            conn.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))


if __name__ == '__main__':
    main()
