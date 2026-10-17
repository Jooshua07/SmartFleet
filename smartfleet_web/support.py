"""Owner-only help and private backup controls."""

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
)

from smartfleet_web import private_backups
from smartfleet_web.auth import owner_required
from smartfleet_web.commands import decode_token, form_token

bp = Blueprint("support", __name__)


@bp.route("/backups", methods=["GET", "POST"])
@owner_required
def backups():
    settings = current_app.config["DB_SETTINGS"]
    root = current_app.config.get("PRIVATE_BACKUP_ROOT")
    state = {"database": settings["dbname"]}
    token = (
        request.form.get("command_token", "")
        if request.method == "POST"
        else form_token("backup", state)
    )
    error, status = None, 200
    if request.method == "POST":
        try:
            decoded = decode_token(token, "backup")
            private_backups.create_archive(
                settings, decoded["key"], current_app.config["OWNER_USERNAME"], root
            )
            flash("Backup created and archive checked.", "success")
            return redirect("/backups", code=303)
        except (ValueError, OSError) as exc:
            # Only explicit validation messages are suitable for display.
            error = (
                str(exc)
                if isinstance(exc, ValueError)
                else "Private backup storage is unavailable."
            )
            status = 409
    return render_template(
        "backups.html",
        title="Backups",
        active="more",
        command_token=token,
        records=private_backups.list_archives(settings, root),
        error=error,
    ), status


@bp.get("/backups/<key>/download")
@owner_required
def download(key):
    try:
        path, record = private_backups.archive(
            current_app.config["DB_SETTINGS"], key, current_app.config.get("PRIVATE_BACKUP_ROOT")
        )
    except (ValueError, OSError):
        abort(404)
    return send_file(
        path,
        as_attachment=True,
        mimetype="application/octet-stream",
        download_name=f"smartfleet-{record['created_at'][:10]}-{key}.dump",
    )


@bp.get("/help")
@owner_required
def help_page():
    from smartfleet_web.help_content import GUIDES

    query = request.args.get("q", "").strip()
    category = request.args.get("category", "All")
    categories = sorted({g.category for g in GUIDES})
    if len(query) > 100 or category not in ["All", *categories]:
        abort(400)
    selected = [
        g
        for g in GUIDES
        if (category == "All" or g.category == category)
        and all(
            word in " ".join((g.question, *g.steps, g.note)).casefold()
            for word in query.casefold().split()
        )
    ]
    return render_template(
        "help.html",
        title="Help & Guide",
        active="more",
        query=query,
        category=category,
        categories=categories,
        guides=selected,
    )
