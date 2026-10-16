import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--http", action="store_true", help="Use HTTP on loopback only.")
    args = parser.parse_args()
    if not (ROOT / ".env.flask.local").is_file():
        raise SystemExit("Run the isolated local setup first.")
    load_dotenv(ROOT / ".env.flask.local", override=True)
    from smartfleet_web import create_app

    overrides = None
    if args.http:
        overrides = {
            "SESSION_COOKIE_SECURE": False,
            "SESSION_COOKIE_NAME": "smartfleet_loopback_session",
        }
    app = create_app(overrides)
    app.run(
        host="127.0.0.1",
        port=args.port,
        debug=False,
        use_reloader=False,
        ssl_context=None if args.http else "adhoc",
    )


if __name__ == "__main__":
    main()
