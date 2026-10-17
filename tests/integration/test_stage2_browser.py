import os
from pathlib import Path
from uuid import uuid4

import pytest
from playwright.sync_api import sync_playwright

pytestmark = [pytest.mark.integration, pytest.mark.browser]


@pytest.mark.parametrize("width,height", [(375, 667), (390, 844), (1366, 900)])
def test_fleet_account_and_schedule_journey(stage2_server, width, height):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.environ.get("SMARTFLEET_BROWSER_CHANNEL"))
        page = browser.new_page(viewport={"width": width, "height": height})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(stage2_server + "/login")
        page.get_by_label("Username").fill("browser-owner")
        page.get_by_label("Password", exact=True).fill("browser-synthetic-passphrase")
        page.get_by_role("button", name="Sign in").click()
        page.get_by_role("navigation", name="Main navigation").get_by_role(
            "link", name="Buses"
        ).click()
        page.get_by_role("navigation", name="Fleet sections").get_by_role(
            "link", name="Drivers"
        ).click()
        page.get_by_role("link", name="Add driver", exact=True).click()
        page.get_by_role("button", name="Save", exact=True).click()
        assert page.url.endswith("/manage/driver-new")
        driver = "Browser Driver " + uuid4().hex[:6]
        page.get_by_label("Driver name", exact=True).fill(driver)
        page.get_by_label("Employment starts").fill("2026-10-01")
        page.get_by_label("Reason", exact=True).fill("Browser synthetic driver")
        page.get_by_role("button", name="Save", exact=True).click()
        page.wait_for_url(stage2_server + "/drivers")
        assert page.get_by_role("heading", name=driver).is_visible()
        page.get_by_role("navigation", name="Fleet sections").get_by_role(
            "link", name="Buses", exact=True
        ).click()
        page.get_by_role("link", name="Add bus", exact=True).click()
        registration = "B" + uuid4().hex[:7].upper()
        page.get_by_label("Registration number").fill(registration)
        page.get_by_label("Date acquired").fill("2026-10-01")
        page.get_by_label("Driver", exact=True).select_option(label=driver)
        page.get_by_label("Seating capacity").fill("26")
        page.get_by_label("Reason", exact=True).fill("Browser synthetic bus")
        page.get_by_role("button", name="Save", exact=True).click()
        page.wait_for_url(stage2_server + "/buses")
        card = page.locator(".bus-card").filter(has_text=registration)
        card.get_by_role("link", name="Details").click()
        page.get_by_role("link", name="Edit bus", exact=True).click()
        page.get_by_label("Model", exact=True).fill("Updated synthetic model")
        page.get_by_label("Reason", exact=True).fill("Browser correction")
        page.get_by_role("button", name="Save", exact=True).click()
        page.wait_for_url(stage2_server + "/buses")
        assert (
            page.locator(".bus-card")
            .filter(has_text=registration)
            .get_by_text("Updated synthetic model / 26 seats")
            .is_visible()
        )
        page.get_by_role("navigation", name="Main navigation").get_by_role(
            "link", name="More", exact=True
        ).click()
        assert page.get_by_role("link", name="Accounts", exact=True).count() == 0
        # The owner-only compatibility URL remains tested, but is no longer a menu action.
        page.goto(stage2_server + "/accounts")
        cash = page.locator(".register-row").filter(
            has=page.get_by_role("heading", name="Cash", exact=True)
        )
        cash.get_by_role("link", name="Edit starting balance").click()
        page.get_by_label("Starting balance (K)").fill("4000.25")
        page.get_by_label("Reason", exact=True).fill("Browser starting balance")
        page.get_by_role("button", name="Save", exact=True).click()
        page.wait_for_url(stage2_server + "/accounts")
        assert page.get_by_text("K 4,000.25", exact=True).count() == 2
        page.get_by_role("navigation", name="Main navigation").get_by_role(
            "link", name="More", exact=True
        ).click()
        page.get_by_role("link", name="Business Presets", exact=True).click()
        page.get_by_role("link", name="Schedule", exact=True).click()
        tuesday = page.locator("details").filter(has=page.locator("summary", has_text="Tuesday"))
        tuesday.locator("summary").click()
        tuesday.get_by_label("Collection day", exact=True).check()
        tuesday.get_by_label("Monday", exact=True).check()
        thursday = page.locator("details").filter(has=page.locator("summary", has_text="Thursday"))
        thursday.get_by_label("Monday", exact=True).uncheck()
        page.get_by_label("Effective from", exact=True).fill("2026-10-19")
        page.get_by_label("Reason", exact=True).fill("Browser add Tuesday")
        page.get_by_role("button", name="Save schedule", exact=True).click()
        assert page.get_by_role("status").get_by_text("Schedule saved.", exact=True).is_visible()
        assert (
            page.request.get(stage2_server + "/presets/schedule/coverage?date=2026-10-20").json()[
                "collection_type"
            ]
            == "TUESDAY"
        )
        assert (
            page.request.get(stage2_server + "/presets/schedule/coverage?date=2026-10-08").json()[
                "coverage_start"
            ]
            == "2026-10-05"
        )
        header, nav = page.locator(".app-header"), page.locator(".bottom-nav")
        before = (header.bounding_box(), nav.bounding_box())
        page.locator("main").evaluate("e => { e.scrollTop=e.scrollHeight; }")
        assert (header.bounding_box(), nav.bounding_box()) == before
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        artifact = Path(".local/browser")
        artifact.mkdir(exist_ok=True, parents=True)
        page.locator("main").evaluate("e => { e.scrollTop=0; }")
        page.screenshot(path=str(artifact / f"stage2-schedule-{width}.png"), full_page=True)
        assert not errors
        browser.close()
