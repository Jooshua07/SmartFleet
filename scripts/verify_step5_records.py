"""Capture/compare live application rows without writing to the database."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from psycopg import sql
from database.connection import get_connection

SNAPSHOT = Path('backups/step5_before_records.json')


def main():
    records = {}
    with get_connection() as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        tables = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()
        for (table,) in tables:
            records[table] = [row[0] for row in conn.execute(sql.SQL(
                'SELECT to_jsonb(t) FROM {} t ORDER BY to_jsonb(t)::text'
            ).format(sql.Identifier(table))).fetchall()]
    if '--capture' in sys.argv:
        if SNAPSHOT.exists():
            raise RuntimeError('Step 5 baseline already captured; do not overwrite it.')
        SNAPSHOT.write_text(json.dumps(records, indent=2), encoding='utf-8')
        print(f'Captured {len(records)} tables for the Step 5 preservation check.')
    else:
        previous = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
        assert records == previous, 'Live records differ from Step 5 baseline; investigate before claiming preservation.'
        print(f'All rows in {len(records)} live tables are unchanged from the Step 5 baseline.')


if __name__ == '__main__':
    main()
