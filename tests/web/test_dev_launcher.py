from unittest.mock import Mock

import pytest

from scripts import run_flask_dev


@pytest.mark.parametrize("use_http", [False, True])
def test_preview_transport_is_explicit_and_loopback_only(monkeypatch, tmp_path, use_http):
    (tmp_path / ".env.flask.local").touch()
    monkeypatch.setattr(run_flask_dev, "ROOT", tmp_path)
    monkeypatch.setattr(run_flask_dev, "load_dotenv", Mock())
    factory = Mock()
    monkeypatch.setattr("smartfleet_web.create_app", factory)
    arguments = ["run_flask_dev.py", "--port", "5002"]
    if use_http:
        arguments.append("--http")
    monkeypatch.setattr("sys.argv", arguments)

    run_flask_dev.main()

    factory.assert_called_once_with(
        {"SESSION_COOKIE_SECURE": False, "SESSION_COOKIE_NAME": "smartfleet_loopback_session"}
        if use_http
        else None
    )
    factory.return_value.run.assert_called_once_with(
        host="127.0.0.1",
        port=5002,
        debug=False,
        use_reloader=False,
        ssl_context=None if use_http else "adhoc",
    )
