import hashlib
import hmac
import math
import secrets
import time
from collections import OrderedDict, deque
from functools import wraps
from threading import Lock
from urllib.parse import urlsplit

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

bp = Blueprint("auth", __name__)


class OwnerSessions:
    """Revocable, bounded sessions; a process restart safely signs all devices out."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.sessions = OrderedDict()
        self.lock = Lock()

    def issue(self):
        sid = secrets.token_urlsafe(32)
        with self.lock:
            self.sessions[sid] = self.clock() + 1800
            while len(self.sessions) > 32:
                self.sessions.popitem(last=False)
        return sid

    def valid(self, sid):
        if not isinstance(sid, str):
            return False
        with self.lock:
            deadline = self.sessions.get(sid, 0)
            if deadline <= self.clock():
                self.sessions.pop(sid, None)
                return False
            return True

    def revoke(self, sid):
        with self.lock:
            self.sessions.pop(sid, None)


class LoginThrottle:
    """Bound attempts and memory for the initial single-process owner pilot."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.clients = OrderedDict()
        self.global_attempts = deque()
        self.lock = Lock()

    def consume(self, address):
        now = self.clock()
        key = hashlib.sha256(address.encode()).hexdigest()
        with self.lock:
            while self.global_attempts and self.global_attempts[0] <= now - 60:
                self.global_attempts.popleft()
            attempts = self.clients.setdefault(key, deque())
            while attempts and attempts[0] <= now - 60:
                attempts.popleft()
            self.clients.move_to_end(key)
            while len(self.clients) > 1024:
                self.clients.popitem(last=False)
            blocked_until = []
            if len(attempts) >= 5:
                blocked_until.append(attempts[0] + 60)
            if len(self.global_attempts) >= 30:
                blocked_until.append(self.global_attempts[0] + 60)
            if blocked_until:
                return max(1, math.ceil(max(blocked_until) - now))
            attempts.append(now)
            self.global_attempts.append(now)
        return 0


def credential_version():
    value = current_app.config["OWNER_USERNAME"] + current_app.config["OWNER_PASSWORD_HASH"]
    return hashlib.sha256(value.encode()).hexdigest()


def is_owner():
    version = session.get("credential_version", "")
    return (
        session.get("subject") == "owner"
        and isinstance(version, str)
        and hmac.compare_digest(version, credential_version())
        and current_app.extensions["owner_sessions"].valid(session.get("sid"))
    )


def owner_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_owner():
            session.clear()
            return redirect(url_for("auth.login", next=request.full_path))
        return view(*args, **kwargs)

    return wrapped


def safe_next(target):
    target = target or ""
    try:
        parts = urlsplit(target)
    except ValueError:
        return url_for("home.index")
    if (
        parts.scheme
        or parts.netloc
        or "\\" in target
        or parts.path not in {"/", "/buses", "/finance", "/more"}
    ):
        return url_for("home.index")
    return parts.path + ("?" + parts.query if parts.query else "")


@bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = safe_next(request.args.get("next"))
    if is_owner():
        return redirect(next_url)
    error = None
    status = 200
    retry = 0
    username = request.form.get("username", "") if request.method == "POST" else ""
    if request.method == "POST":
        retry = current_app.extensions["login_throttle"].consume(request.remote_addr or "unknown")
        if retry:
            error = "Too many attempts. Please wait a minute and try again."
            status = 429
        else:
            password = request.form.get("password", "")
            password_ok = check_password_hash(
                current_app.config["OWNER_PASSWORD_HASH"], password[:1024]
            )
            username_ok = hmac.compare_digest(
                username.encode(), current_app.config["OWNER_USERNAME"].encode()
            )
            if username_ok and password_ok and len(password) <= 1024:
                session.clear()
                session["subject"] = "owner"
                session["credential_version"] = credential_version()
                session["sid"] = current_app.extensions["owner_sessions"].issue()
                session.permanent = True
                current_app.logger.info("Owner signed in")
                return redirect(next_url, code=303)
            error = "Sign-in details were not recognised."
            status = 401
            current_app.logger.warning("Owner sign-in failed")
    response = current_app.make_response(
        (
            render_template("login.html", error=error, next_url=next_url, username=username[:100]),
            status,
        )
    )
    if retry:
        response.headers["Retry-After"] = str(retry)
    return response


@bp.post("/logout")
@owner_required
def logout():
    current_app.extensions["owner_sessions"].revoke(session.get("sid"))
    session.clear()
    return redirect(url_for("auth.login"), code=303)
