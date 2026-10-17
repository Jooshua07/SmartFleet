import os
from pathlib import Path
from threading import Thread

import pytest
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

pytestmark = [pytest.mark.integration, pytest.mark.browser]
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(params=["https", "http"])
def live_server(isolated_app, request):
    use_http = request.param == "http"
    if use_http:
        isolated_app.config.update(
            SESSION_COOKIE_SECURE=False, SESSION_COOKIE_NAME="smartfleet_loopback_session"
        )
    server = make_server(
        "127.0.0.1", 0, isolated_app, threaded=True, ssl_context=None if use_http else "adhoc"
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"{request.param}://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join(timeout=5)
    server.server_close()


@pytest.mark.parametrize("width,height", [(375, 667), (390, 844), (1366, 900)])
def test_owner_phone_and_desktop_journey(live_server, width, height):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.environ.get("SMARTFLEET_BROWSER_CHANNEL"))
        context = browser.new_context(
            ignore_https_errors=True, viewport={"width": width, "height": height}
        )
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(live_server + "/buses")
        page.get_by_label("Username").fill("browser-owner")
        page.get_by_label("Password", exact=True).fill("wrong")
        page.get_by_role("button", name="Sign in").click()
        assert page.get_by_role("alert").is_visible()
        page.get_by_label("Password", exact=True).fill("browser-synthetic-passphrase")
        page.get_by_role("button", name="Sign in").click()
        page.wait_for_url(live_server + "/buses")
        assert page.get_by_role("heading", name="DEMO101").is_visible()
        cookies = context.cookies()
        assert len(cookies) == 1
        assert cookies[0]["httpOnly"]
        assert cookies[0]["sameSite"] == "Lax"
        assert cookies[0]["secure"] == live_server.startswith("https:")
        assert cookies[0]["name"] == (
            "smartfleet_dev_session"
            if live_server.startswith("https:")
            else "smartfleet_loopback_session"
        )
        assert page.locator(".brand svg").count() == 1
        page.get_by_label("Search buses").fill("DEMO102")
        page.get_by_role("button", name="Search", exact=True).click()
        assert page.get_by_role("heading", name="DEMO102").is_visible()
        assert page.locator(".bus-card").count() == 1
        page.get_by_label("Search buses").fill("")
        page.get_by_label("Status", exact=True).select_option("INACTIVE")
        page.wait_for_url("**/buses?**status=INACTIVE")
        assert page.get_by_role("button", name="Apply", exact=True).count() == 0
        assert page.get_by_role("heading", name="DEMO103").is_visible()
        page.get_by_role("navigation", name="Main navigation").get_by_role(
            "link", name="Buses", exact=True
        ).click()
        main = page.locator("main")
        header_before = page.locator(".app-header").bounding_box()
        nav_before = page.locator(".bottom-nav").bounding_box()
        main.evaluate("element => { element.scrollTop = element.scrollHeight; }")
        assert page.locator(".app-header").bounding_box() == header_before
        assert page.locator(".bottom-nav").bounding_box() == nav_before
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        assert (
            page.locator(".bottom-nav").bounding_box()["y"]
            >= main.bounding_box()["y"] + main.bounding_box()["height"] - 1
        )
        main.evaluate("element => { element.scrollTop = 0; }")
        artifact = ROOT / ".local" / "browser"
        artifact.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(artifact / f"stage1-buses-{width}.png"), full_page=True)
        for name, heading in (("Home", "Home"), ("Finance", "Finance"), ("More", "More")):
            page.get_by_role("navigation", name="Main navigation").get_by_role(
                "link", name=name, exact=True
            ).click()
            assert page.get_by_role("heading", name=heading, exact=True).is_visible()
        page.get_by_role("button", name="Sign out").click()
        page.wait_for_url("**/login")
        page.goto(live_server + "/buses")
        page.wait_for_url("**/login?**")
        assert not errors
        browser.close()
