import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

pytestmark = [pytest.mark.integration, pytest.mark.browser]


@pytest.mark.parametrize("width,height", [(375, 667), (390, 844), (1366, 900)])
def test_cashing_and_expense_real_entry(stage2_server, width, height):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.environ.get("SMARTFLEET_BROWSER_CHANNEL"))
        page = browser.new_page(viewport={"width": width, "height": height})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(stage2_server + "/login")
        page.get_by_label("Username").fill("browser-owner")
        page.get_by_label("Password", exact=True).fill("browser-synthetic-passphrase")
        page.get_by_role("button", name="Sign in").click()
        page.goto(stage2_server + "/record-cashing?date=2026-10-08")
        assert page.locator("form.cashing-entry").count() == 1
        assert page.locator(".cashing-bus:visible").count() == 0
        page.get_by_label("Buses", exact=True).select_option(label=["DEMO101", "DEMO102"])
        page.get_by_label("Adjust buses", exact=True).check()
        assert page.locator(".cashing-bus:visible").count() == 2
        page.get_by_label("Same normal amount for selected buses").check()
        page.get_by_label("Amount per bus (K)").fill("1800")
        assert page.get_by_label("DEMO101 amount (K)").is_hidden()
        page.get_by_label("Reason", exact=True).fill("Browser cashing")
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        artifacts = Path(".local/browser")
        artifacts.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(artifacts / f"stage3-cashing-{width}.png"), full_page=True)
        page.get_by_role("button", name="Submit", exact=True).click()
        page.wait_for_url(stage2_server + "/record-cashing?date=2026-10-08")
        assert page.get_by_role("status").get_by_text("Cashing saved.").is_visible()
        assert page.locator("#bus_ids option:checked").count() == 0
        page.goto(stage2_server + "/record-expense")
        page.get_by_label("Expense date", exact=True).fill("2026-10-01")
        page.get_by_label("Category", exact=True).select_option(label="Bus - Maintenance")
        page.get_by_label("Amount (K)", exact=True).fill("4000")
        page.get_by_label("Expense title", exact=True).fill("Tyres")
        page.get_by_label("Paid to", exact=True).fill("Synthetic supplier")
        page.get_by_label("Receipt/reference", exact=True).fill("SYNTHETIC-001")
        page.get_by_label("Reason", exact=True).fill("Browser expense")
        page.get_by_role("button", name="Save", exact=True).click()
        page.wait_for_url(stage2_server + "/record-expense")
        assert page.get_by_role("status").get_by_text("Expense saved.").is_visible()
        assert page.get_by_label("Amount (K)", exact=True).input_value() == ""
        page.goto(stage2_server + "/expenses")
        assert page.get_by_role("heading", name="Tyres", exact=True).is_visible()
        page.get_by_role("link", name="Delete", exact=True).click()
        page.get_by_label("Correction reason").fill("Cancel browser test")
        page.get_by_role("checkbox").check()
        page.get_by_role("button", name="Delete", exact=True).click()
        page.wait_for_url(stage2_server + "/expenses")
        assert page.get_by_role("heading", name="Tyres", exact=True).count() == 0
        assert not errors
        browser.close()
