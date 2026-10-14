from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from psycopg.rows import dict_row

from database.connection import get_connection
from services.account_service import get_default_business_payment_account
from services.correction_service import record_correction_audit


def servicing_warning(due: date | None, today: date) -> str:
    if due is None:
        return 'Not scheduled'
    remaining = (due - today).days
    if remaining < 0:
        return 'Overdue'
    if remaining <= 7:
        return 'Urgent'
    if remaining <= 14:
        return 'Warning'
    return 'Normal'


def servicing_costs(labour, transport, other) -> tuple[Decimal, Decimal, Decimal]:
    try:
        values = tuple(Decimal(str(value)) for value in (labour, transport, other))
        if any(not value.is_finite() or value < 0 or value != value.quantize(Decimal('.01')) for value in values):
            raise ValueError('Costs must be non-negative amounts with at most two decimal places.')
        return values
    except (InvalidOperation, TypeError):
        raise ValueError('Enter valid servicing costs.') from None


def get_servicing_schedules() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute('''SELECT b.id AS bus_id, b.registration_number, b.status,
                ms.next_due_date, ms.interval_days, ms.last_completed_date
                FROM buses b LEFT JOIN maintenance_schedules ms
                  ON ms.bus_id=b.id AND ms.schedule_name='Servicing' AND ms.active
                ORDER BY b.registration_number''')
            return cursor.fetchall()


def get_servicing_history(bus_id=None, start_date=None, end_date=None) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute('''SELECT m.*, b.registration_number FROM maintenance m
                JOIN buses b ON b.id=m.bus_id WHERE m.is_servicing AND m.status='COMPLETED'
                AND (%s::integer IS NULL OR m.bus_id=%s)
                AND (%s::date IS NULL OR m.completed_date >= %s)
                AND (%s::date IS NULL OR m.completed_date <= %s)
                ORDER BY m.completed_date DESC, m.id DESC''',
                (bus_id,bus_id,start_date,start_date,end_date,end_date))
            return cursor.fetchall()


def _refresh_schedule(cursor, bus_id):
    cursor.execute('''SELECT MAX(completed_date) AS latest FROM maintenance
        WHERE bus_id=%s AND is_servicing AND status='COMPLETED' ''', (bus_id,))
    latest = cursor.fetchone()['latest']
    if latest:
        cursor.execute("SELECT last_completed_date FROM maintenance_schedules WHERE bus_id=%s AND schedule_name='Servicing'", (bus_id,))
        previous=cursor.fetchone()
        if previous and previous['last_completed_date']==latest:
            return
        cursor.execute('''INSERT INTO maintenance_schedules(bus_id,schedule_name,interval_days,last_completed_date,next_due_date)
            VALUES (%s,'Servicing',35,%s,%s) ON CONFLICT(bus_id,schedule_name)
            DO UPDATE SET last_completed_date=EXCLUDED.last_completed_date,
            next_due_date=EXCLUDED.last_completed_date + maintenance_schedules.interval_days,
            updated_at=CURRENT_TIMESTAMP''', (bus_id,latest,latest+timedelta(days=35)))


def set_servicing_schedule(bus_id: int, next_due_date: date, interval_days: int = 35, reason='Schedule correction'):
    if not isinstance(next_due_date, date) or not isinstance(interval_days, int) or interval_days <= 0:
        raise ValueError('Choose a servicing date and positive frequency.')
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute('SELECT id FROM buses WHERE id=%s FOR UPDATE', (bus_id,))
            if not cursor.fetchone():
                raise ValueError('Bus not found.')
            cursor.execute("SELECT * FROM maintenance_schedules WHERE bus_id=%s AND schedule_name='Servicing' FOR UPDATE", (bus_id,))
            previous = cursor.fetchone()
            record_correction_audit(cursor, area='Maintenance', record_type='schedule', record_id=bus_id, action='UPDATE', reason=reason,
                snapshot={'before': previous, 'next_due_date': next_due_date, 'interval_days': interval_days})
            cursor.execute('''INSERT INTO maintenance_schedules(bus_id,schedule_name,interval_days,next_due_date)
                VALUES (%s,'Servicing',%s,%s) ON CONFLICT(bus_id,schedule_name) DO UPDATE
                SET next_due_date=EXCLUDED.next_due_date, interval_days=EXCLUDED.interval_days, active=TRUE,
                updated_at=CURRENT_TIMESTAMP''', (bus_id,interval_days,next_due_date))


def record_servicing(bus_id: int, completed_date: date, labour=0, transport=0, other=0,
                     payment_date: date | None = None, notes=None, event_id=None, reason=None):
    labour, transport, other = servicing_costs(labour,transport,other)
    total = labour + transport + other
    if not isinstance(completed_date, date):
        raise ValueError('Choose an actual completion date.')
    from utils.dates import today_lusaka
    if completed_date > today_lusaka():
        raise ValueError('Completion date cannot be in the future.')
    if total and (not isinstance(payment_date,date) or payment_date > today_lusaka()):
        raise ValueError('Choose the actual payment date. This form records paid servicing.')
    account_id = get_default_business_payment_account()['id'] if total else None
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute('SELECT registration_number FROM buses WHERE id=%s FOR UPDATE', (bus_id,))
            bus = cursor.fetchone()
            if not bus:
                raise ValueError('Choose a valid bus.')
            title = f"{bus['registration_number']} - Servicing - {completed_date:%d %b %Y}"
            existing = None
            if event_id:
                cursor.execute('SELECT * FROM maintenance WHERE id=%s AND is_servicing FOR UPDATE', (event_id,))
                existing = cursor.fetchone()
                if not existing or existing['bus_id'] != bus_id:
                    raise ValueError('Servicing record not found for this bus.')
                record_correction_audit(cursor,area='Maintenance',record_type='servicing',record_id=event_id,action='UPDATE',reason=reason,
                    snapshot={'before':existing, 'completed_date':completed_date,'labour':labour,'transport':transport,'other':other})
            cursor.execute('''SELECT id FROM maintenance WHERE bus_id=%s AND completed_date=%s
                AND is_servicing AND status='COMPLETED' AND (%s::integer IS NULL OR id<>%s)''',
                (bus_id,completed_date,event_id,event_id))
            if cursor.fetchone():
                raise ValueError('Servicing is already recorded for this bus and date. Edit that record.')
            expense_id = existing['expense_id'] if existing else None
            ledger_id = None
            if expense_id:
                cursor.execute('SELECT financial_transaction_id FROM expenses WHERE id=%s FOR UPDATE', (expense_id,))
                ledger_id = cursor.fetchone()['financial_transaction_id']
            if total:
                if ledger_id:
                    cursor.execute('''UPDATE financial_transactions SET transaction_date=%s, amount=%s,
                        description=%s, notes=%s WHERE id=%s''', (payment_date,total,title,notes,ledger_id))
                    cursor.execute('''UPDATE expenses SET expense_date=%s,amount=%s,description=%s,notes=%s WHERE id=%s''',
                        (payment_date,total,title,notes,expense_id))
                else:
                    cursor.execute('''INSERT INTO financial_transactions(account_id,transaction_date,transaction_type,direction,amount,description,notes)
                        VALUES (%s,%s,'EXPENSE','OUT',%s,%s,%s) RETURNING id''', (account_id,payment_date,total,title,notes))
                    ledger_id = cursor.fetchone()['id']
                    cursor.execute("SELECT id FROM expense_categories WHERE name='Servicing'")
                    category_id = cursor.fetchone()['id']
                    cursor.execute('''INSERT INTO expenses(expense_date,category_id,amount,description,scope,bus_id,payment_source,
                        financial_account_id,financial_transaction_id,notes)
                        VALUES (%s,%s,%s,%s,'BUS',%s,'BUSINESS_ACCOUNT',%s,%s,%s) RETURNING id''',
                        (payment_date,category_id,total,title,bus_id,account_id,ledger_id,notes))
                    expense_id = cursor.fetchone()['id']
            elif expense_id:
                cursor.execute('UPDATE maintenance SET expense_id=NULL WHERE id=%s', (event_id,))
                cursor.execute('DELETE FROM expense_allocations WHERE expense_id=%s', (expense_id,))
                cursor.execute('DELETE FROM expenses WHERE id=%s', (expense_id,))
                cursor.execute('DELETE FROM financial_transactions WHERE id=%s', (ledger_id,))
                expense_id = None
            if existing:
                cursor.execute('''UPDATE maintenance SET description=%s,completed_date=%s,reported_date=%s,
                    labour_cost=%s,transport_cost=%s,parts_cost=%s,expense_id=%s,payment_date=%s,notes=%s,
                    updated_at=CURRENT_TIMESTAMP WHERE id=%s RETURNING id''',
                    (title,completed_date,completed_date,labour,transport,other,expense_id,payment_date if total else None,notes,event_id))
            else:
                cursor.execute('''INSERT INTO maintenance(bus_id,maintenance_type,description,reported_date,completed_date,status,
                    labour_cost,transport_cost,parts_cost,expense_id,payment_date,notes,is_servicing)
                    VALUES (%s,'PLANNED',%s,%s,%s,'COMPLETED',%s,%s,%s,%s,%s,%s,TRUE) RETURNING id''',
                    (bus_id,title,completed_date,completed_date,labour,transport,other,expense_id,payment_date if total else None,notes))
            result = cursor.fetchone()
            _refresh_schedule(cursor,bus_id)
            return result
