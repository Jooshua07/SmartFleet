import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

pytestmark = [pytest.mark.integration, pytest.mark.browser]


@pytest.mark.parametrize("width,height", [(375, 667), (390, 844), (1366, 900)])
def test_servicing_reports_reminders_backups_help_journey(
    stage2_server, stage2_app, tmp_path, width, height
):
    stage2_app.config["PRIVATE_BACKUP_ROOT"] = tmp_path
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.environ.get("SMARTFLEET_BROWSER_CHANNEL"))
        page = browser.new_page(viewport={"width": width, "height": height}, accept_downloads=True)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(stage2_server + "/login")
        page.get_by_label("Username").fill("browser-owner")
        page.get_by_label("Password", exact=True).fill("browser-synthetic-passphrase")
        page.get_by_role("button", name="Sign in").click()
        page.goto(stage2_server + "/more")
        for label in ("Record Servicing", "Reports", "Backups", "Reminders", "Help & Guide"):
            assert page.get_by_role("link", name=label, exact=True).count() == 1
        page.get_by_role("link", name="Record Servicing", exact=True).click()
        page.get_by_label("Bus", exact=True).select_option(label="DEMO101")
        page.get_by_label("Actual completion date").fill("2026-10-09")
        page.get_by_label("Labour (K)").fill("200.25")
        page.get_by_label("Transport (K)").fill("50.10")
        page.get_by_label("Other costs (K)").fill("49.65")
        assert page.locator("#servicing-total").inner_text() == "Total: K 300.00"
        page.get_by_role("button", name="Save", exact=True).click()
        assert page.get_by_label("Labour (K)").input_value() == "200.25"
        page.get_by_label("Actual payment date").fill("2026-10-10")
        page.get_by_label("Reason", exact=True).fill("Browser servicing")
        page.get_by_role("button", name="Save", exact=True).click()
        assert page.get_by_role("status").get_by_text("Servicing saved.", exact=True).is_visible()
        assert page.get_by_label("Labour (K)").input_value() == "0"
        page.get_by_role("link", name="Servicing history & schedules").click()
        page.get_by_role("link", name="Correct", exact=True).click()
        assert page.get_by_label("Labour (K)").input_value() == "200.25"
        page.get_by_label("Other costs (K)").fill("59.65")
        page.get_by_label("Reason", exact=True).fill("Receipt correction")
        page.get_by_role("button", name="Save", exact=True).click()
        assert page.get_by_text("K 310.00", exact=True).count() == 1
        for path in ("/reminders", "/reports", "/backups", "/help"):
            page.goto(stage2_server + path)
            assert page.locator("main h1").is_visible()
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
            # The existing app shell pins header/nav by scrolling main, not CSS position:fixed.
            header = page.locator(".app-header").bounding_box()
            navigation = page.locator(".bottom-nav").bounding_box()
            page.locator("main").evaluate("e=>e.scrollTop=e.scrollHeight")
            assert page.locator(".app-header").bounding_box() == header
            assert page.locator(".bottom-nav").bounding_box() == navigation
        page.get_by_label("Search", exact=True).fill("servicing")
        page.get_by_role("button", name="Search", exact=True).click()
        page.get_by_text("How do I record completed servicing?", exact=True).click()
        assert page.get_by_text(
            "Enter labour, transport and other costs separately.", exact=False
        ).is_visible()
        page.goto(stage2_server + "/reports")
        with page.expect_download() as download:
            page.get_by_role("link", name="Complete workbook", exact=True).click()
        assert download.value.suggested_filename.endswith(".xlsx")
        folder = Path(".local/browser")
        folder.mkdir(parents=True, exist_ok=True)
        page.locator("main").evaluate("e=>e.scrollTop=0")
        page.screenshot(path=str(folder / f"stage6-reports-{width}.png"), full_page=True)
        page.goto(stage2_server + "/backups")
        page.get_by_role("button", name="Create backup").click()
        assert (
            page.get_by_role("status")
            .get_by_text("Backup created and archive checked.", exact=True)
            .is_visible()
        )
        with page.expect_download() as download:
            page.get_by_role("link", name="Download", exact=True).click()
        assert download.value.suggested_filename.endswith(".dump")
        assert not errors
        browser.close()
