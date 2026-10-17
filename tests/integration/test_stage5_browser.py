import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from tests.integration.test_stage5 import money_data as money_data

pytestmark = [pytest.mark.integration, pytest.mark.browser]


@pytest.mark.parametrize("width,height", [(375, 667), (390, 844), (1366, 900)])
def test_stage5_money_and_simplified_forms(stage2_server, money_data, width, height):
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=os.environ.get("SMARTFLEET_BROWSER_CHANNEL"))
        page = browser.new_page(viewport={"width": width, "height": height})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(stage2_server + "/login")
        page.get_by_label("Username").fill("browser-owner")
        page.get_by_label("Password", exact=True).fill("browser-synthetic-passphrase")
        page.get_by_role("button", name="Sign in").click()
        page.goto(stage2_server + "/more")
        assert page.get_by_role("link", name="Accounts", exact=True).count() == 0
        assert page.get_by_role("link", name="Record Expense", exact=True).is_visible()
        page.get_by_role("link", name="Loans", exact=True).click()
        assert page.get_by_role("heading", name="Loans", exact=True).is_visible()
        page.goto(stage2_server + "/buses")
        page.get_by_label("Status", exact=True).select_option("INACTIVE")
        page.wait_for_url("**status=INACTIVE")
        assert page.get_by_role("heading", name="DEMO103", exact=True).is_visible()
        assert page.locator(".bus-card").count() == 1
        for view in ("collections", "expenses", "balances"):
            page.goto(stage2_server + "/finance?view=" + view)
            assert page.locator(".quick-actions").count() == 0
            assert page.get_by_role("link", name="Accounts", exact=True).count() == 0
        page.goto(stage2_server + "/record-expense")
        assert page.get_by_label("Paid from", exact=True).count() == 0
        assert page.get_by_label("Bus", exact=True).is_hidden()
        page.get_by_label("Bus Specific", exact=True).check()
        assert page.get_by_label("Bus", exact=True).is_visible()
        page.get_by_label("Bus", exact=True).select_option(label="DEMO101")
        page.get_by_label("General", exact=True).check()
        assert page.get_by_label("Bus", exact=True).is_hidden()
        page.goto(stage2_server + "/record-cashing?date=2026-10-08")
        assert page.get_by_label("Paid into", exact=True).count() == 0
        page.get_by_label("Buses", exact=True).select_option(label="DEMO101")
        card = page.locator(".cashing-bus:visible")
        assert card.count() == 1
        assert card.evaluate("e=>getComputedStyle(e).borderTopStyle") == "solid"
        assert "|" not in page.locator("#bus_ids").inner_text()
        page.goto(stage2_server + "/money/advance")
        page.get_by_label("Amount (K)", exact=True).fill("200")
        page.get_by_label("Date", exact=True).fill("2026-10-10")
        page.get_by_role("button", name="Save", exact=True).click()
        assert page.get_by_label("Amount (K)", exact=True).input_value() == "200"
        page.get_by_label("Reason", exact=True).fill("Browser advance")
        page.get_by_role("button", name="Save", exact=True).click()
        assert page.get_by_role("status").get_by_text("Record saved.", exact=True).is_visible()
        assert page.get_by_label("Amount (K)", exact=True).input_value() == ""
        page.goto(stage2_server + "/money/salary")
        page.get_by_label("Salary year", exact=True).fill("2026")
        page.get_by_label("Salary month", exact=True).select_option("10")
        page.get_by_label("Date", exact=True).fill("2026-10-10")
        page.get_by_role("button", name="Preview salary", exact=True).click()
        assert page.get_by_role("region", name="Salary preview").is_visible()
        page.get_by_label("Reason", exact=True).fill("Browser salary")
        page.get_by_role("button", name="Save", exact=True).click()
        page.goto(stage2_server + f"/driver-money/{money_data['employment']}")
        assert page.get_by_text("Net paid K 1800.00", exact=False).is_visible()
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        folder = Path(".local/browser")
        folder.mkdir(exist_ok=True, parents=True)
        page.screenshot(path=str(folder / f"stage5-payroll-{width}.png"), full_page=True)
        assert not errors
        browser.close()
