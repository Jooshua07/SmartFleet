from database.connection import get_connection
from services.account_service import get_negative_balance_warnings
from services.backup_service import latest_backup_age_hours


def get_data_validation_warnings(backup_age_provider=None) -> list[str]:
    warnings = []

    backup_age = (backup_age_provider or latest_backup_age_hours)()
    if backup_age is None:
        warnings.append("No database backup has been created yet.")
    elif backup_age > 24:
        warnings.append("The latest database backup is more than 24 hours old.")

    with get_connection() as conn:
        with conn.cursor() as cursor:
            checks = [
                ("routes", "No routes have been added yet."),
                ("drivers", "No drivers have been added yet."),
                ("buses", "No buses have been added yet."),
            ]
            for table_name, message in checks:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                if cursor.fetchone()[0] == 0:
                    warnings.append(message)

            cursor.execute("SELECT COUNT(*) FROM financial_accounts WHERE active = TRUE;")
            if cursor.fetchone()[0] == 0:
                warnings.append("No active payment accounts are configured.")

    warnings.extend(get_negative_balance_warnings())
    return warnings
