from flask import Blueprint, abort, current_app, render_template, request

from services.bus_service import get_all_buses
from smartfleet_web.auth import owner_required

bp = Blueprint("home", __name__)


@bp.get("/")
@owner_required
def index():
    from smartfleet_web.reporting import show

    return show("home")


@bp.get("/buses")
@owner_required
def buses():
    try:
        page = int(request.args.get("page", "1"))
    except ValueError:
        abort(400)
    if not 1 <= page <= 10_000:
        abort(400)
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "")
    if len(search) > 100 or status not in {"", "ACTIVE", "INACTIVE"}:
        abort(400)
    rows = get_all_buses(limit=21, offset=(page - 1) * 20, search=search, status=status)
    return render_template(
        "buses.html",
        title="Buses",
        active="buses",
        buses=rows[:20],
        page=page,
        has_next=len(rows) > 20,
        search=search,
        status=status,
    )


@bp.get("/finance")
@owner_required
def finance():
    from smartfleet_web.reporting import show

    return show("finance")


@bp.get("/bus-accounts", defaults={"bus_id": None})
@bp.get("/bus-accounts/<int:bus_id>")
@owner_required
def bus_accounts(bus_id):
    from smartfleet_web.reporting import show

    return show("bus-accounts", bus_id)


@bp.get("/more")
@owner_required
def more():
    from services.validation_service import get_data_validation_warnings
    from smartfleet_web.private_backups import latest_age

    warnings = get_data_validation_warnings(
        lambda: latest_age(
            current_app.config["DB_SETTINGS"], current_app.config.get("PRIVATE_BACKUP_ROOT")
        )
    )
    return render_template("more.html", title="More", active="more", warnings=warnings)


@bp.get("/health/live")
def live():
    return {"status": "ok"}


@bp.get("/health/ready")
@owner_required
def ready():
    from database.connection import get_connection

    with get_connection() as conn:
        row = conn.execute(
            "SELECT current_database(), current_user, "
            "current_setting('transaction_read_only'), to_regclass('public.buses') IS NOT NULL"
        ).fetchone()
    if row[:2] != (
        current_app.config["DB_SETTINGS"]["dbname"],
        current_app.config["DB_SETTINGS"]["user"],
    ) or row[2:] != ("on", True):
        abort(503)
    return {"status": "ready"}
