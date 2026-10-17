import logging

import psycopg
from flask import Flask, g, render_template, request
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.exceptions import SecurityError

from database.connection import reset_connection_settings, set_connection_settings
from smartfleet_web.auth import LoginThrottle, OwnerSessions, is_owner
from smartfleet_web.config import settings_from_environment, validate_settings

csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(settings_from_environment())
    if test_config:
        app.config.update(test_config)
    validate_settings(app.config)
    app.logger.setLevel(logging.INFO)
    app.extensions["login_throttle"] = LoginThrottle()
    app.extensions["owner_sessions"] = OwnerSessions()
    csrf.init_app(app)

    from smartfleet_web.auth import bp as auth_bp
    from smartfleet_web.management import bp as management_bp
    from smartfleet_web.money import bp as money_bp
    from smartfleet_web.recording import bp as recording_bp
    from smartfleet_web.views import bp as home_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(management_bp)
    app.register_blueprint(recording_bp)
    app.register_blueprint(money_bp)

    @app.before_request
    def bind_database():
        g.database_token = set_connection_settings(app.config["DB_SETTINGS"])

    @app.teardown_request
    def release_database(error=None):
        token = g.pop("database_token", None)
        if token is not None:
            reset_connection_settings(token)

    @app.context_processor
    def shell_context():
        return {"owner_signed_in": is_owner()}

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; object-src 'none'; base-uri 'self'; "
            "frame-ancestors 'none'; form-action 'self'"
        )
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store"
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        return render_template(
            "error.html", code=400, message="Your form expired. Reload and retry."
        ), 400

    @app.errorhandler(SecurityError)
    def invalid_host(error):
        # Host rejection has no URL adapter; do not render links or reflect that host.
        return "Invalid request host.", 400, {"Content-Type": "text/plain; charset=utf-8"}

    @app.errorhandler(psycopg.Error)
    def database_error(error):
        app.logger.error("Database request failed: %s", type(error).__name__)
        return render_template(
            "error.html", code=503, message="Records are unavailable. Please retry."
        ), 503

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(405)
    @app.errorhandler(413)
    def client_error(error):
        return render_template("error.html", code=error.code, message=error.name), error.code

    @app.errorhandler(500)
    def server_error(error):
        return render_template(
            "error.html", code=500, message="Something went wrong. Please retry."
        ), 500

    return app
