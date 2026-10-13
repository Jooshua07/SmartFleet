from datetime import date
from pathlib import Path
import os
import sys
import time

import psycopg
from dotenv import load_dotenv
from psycopg import sql


load_dotenv()
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def _connection_kwargs(dbname: str) -> dict:
    return {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "dbname": dbname,
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
    }


def main() -> None:
    temp_db = f"smartfleet_money_smoke_{int(time.time())}"
    with psycopg.connect(**_connection_kwargs("postgres"), autocommit=True) as admin_conn:
        with admin_conn.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(temp_db)))

    try:
        with psycopg.connect(**_connection_kwargs(temp_db)) as conn:
            with conn.cursor() as cursor:
                for migration in sorted(Path("migrations").glob("[0-9][0-9][0-9]_*.sql")):
                    cursor.execute(migration.read_text(encoding="utf-8"))

        os.environ["DB_NAME"] = temp_db

        from services.bus_service import create_bus
        from services.driver_money_service import (
            cancel_driver_advance,
            get_salary_preview,
            list_outstanding_advances,
            record_driver_advance,
            record_driver_salary,
        )
        from services.driver_service import create_driver, get_driver
        from services.finance_service import get_business_balance
        from services.loan_service import (
            add_business_loan,
            cancel_loan_repayment,
            cancel_owner_drawing,
            cancel_owner_loan_transaction,
            get_owner_money_summary,
            list_business_loans,
            record_business_repayment_to_owner,
            record_loan_repayment,
            record_owner_drawing,
            record_owner_loan_to_business,
        )
        from services.performance_service import get_operating_summary
        from services.preset_service import set_driver_salary_preset
        from services.route_service import add_route

        route = add_route("Smoke Route")
        driver = create_driver("Smoke Driver", start_date=date(2026, 10, 1), monthly_salary=2500)
        employment = get_driver(driver["id"])
        create_bus("PAY123", route["id"], date_acquired=date(2026, 10, 1), employment_id=employment["employment_id"])
        set_driver_salary_preset(2500, date(2026, 10, 1), driver_id=driver["id"])

        record_driver_advance(employment["employment_id"], date(2026, 10, 1), 1000, "October advance")
        try:
            record_driver_advance(employment["employment_id"], date(2026, 10, 2), 1, "Above cap")
        except ValueError:
            pass
        else:
            raise RuntimeError("Advance above K1,000 outstanding cap should fail.")

        preview = get_salary_preview(employment["employment_id"], 2026, 10)
        if preview["suggested_recovery"] != 1000:
            raise RuntimeError(f"Expected K1,000 recovery, got {preview['suggested_recovery']}")
        salary = record_driver_salary(
            employment["employment_id"],
            2026,
            10,
            date(2026, 10, 31),
            recovery_amount=1000,
        )
        if salary["net_salary"] != 1500:
            raise RuntimeError(f"Expected K1,500 net salary, got {salary['net_salary']}")
        if list_outstanding_advances(employment["employment_id"]):
            raise RuntimeError("Advance should be fully recovered.")

        loan = add_business_loan("Carecoop smoke", "Carecoop", 30000, date(2026, 10, 1))
        record_loan_repayment(date(2026, 10, 5), 5000, "BUSINESS_ACCOUNT", loan_id=loan["id"])
        balance_after_business_repayment = get_business_balance()["business_balance"]
        record_loan_repayment(date(2026, 10, 6), 10000, "OWNER_PERSONAL", loan_id=loan["id"])
        if get_business_balance()["business_balance"] != balance_after_business_repayment:
            raise RuntimeError("Owner-paid loan repayment must not move business cash.")
        owner_summary = get_owner_money_summary()
        if owner_summary["owner_balance"] != 10000:
            raise RuntimeError(f"Owner balance should be K10,000, got {owner_summary['owner_balance']}")

        record_business_repayment_to_owner(date(2026, 10, 7), 2000)
        record_owner_drawing(date(2026, 10, 8), 500)
        owner_summary = get_owner_money_summary()
        if owner_summary["owner_balance"] != 8000:
            raise RuntimeError(f"Owner balance should be K8,000, got {owner_summary['owner_balance']}")

        loans = list_business_loans()
        smoke_loan = next(item for item in loans if item["id"] == loan["id"])
        if smoke_loan["outstanding_principal"] != 15000:
            raise RuntimeError(f"Loan outstanding should be K15,000, got {smoke_loan['outstanding_principal']}")

        summary = get_operating_summary(date(2026, 10, 1), date(2026, 10, 31))
        if summary["expenses"] != 2500:
            raise RuntimeError(f"Operating expenses should count salary once as K2,500, got {summary['expenses']}")

        extra_advance = record_driver_advance(employment["employment_id"], date(2026, 10, 9), 500, "Mistaken advance")
        cancel_driver_advance(extra_advance["id"], "Smoke correction")
        if list_outstanding_advances(employment["employment_id"]):
            raise RuntimeError("Cancelled advance should not remain outstanding.")

        extra_repayment = record_loan_repayment(date(2026, 10, 9), 1000, "BUSINESS_ACCOUNT", loan_id=loan["id"])
        cancel_loan_repayment(extra_repayment["id"], "Smoke correction")
        smoke_loan = next(item for item in list_business_loans() if item["id"] == loan["id"])
        if smoke_loan["outstanding_principal"] != 15000:
            raise RuntimeError("Cancelled loan repayment should restore loan outstanding.")

        extra_drawing = record_owner_drawing(date(2026, 10, 9), 250)
        cancel_owner_drawing(extra_drawing["id"], "Smoke correction")

        extra_owner_loan = record_owner_loan_to_business(date(2026, 10, 10), 750)
        cancel_owner_loan_transaction(extra_owner_loan["id"], "Smoke correction")

        with psycopg.connect(**_connection_kwargs(temp_db)) as audit_conn:
            with audit_conn.cursor() as audit_cursor:
                audit_cursor.execute("SELECT COUNT(*) FROM correction_audit;")
                if audit_cursor.fetchone()[0] != 4:
                    raise RuntimeError("Expected four correction audit records from smoke corrections.")

        print(f"Money workflow smoke passed in {temp_db}.")
    finally:
        with psycopg.connect(**_connection_kwargs("postgres"), autocommit=True) as admin_conn:
            with admin_conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s
                      AND pid <> pg_backend_pid();
                    """,
                    (temp_db,),
                )
                cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(temp_db)))


if __name__ == "__main__":
    main()
