import os
from pathlib import Path

import psycopg
import pytest
from playwright.sync_api import sync_playwright

pytestmark = [pytest.mark.integration, pytest.mark.browser]


@pytest.mark.parametrize("width,height", [(375, 667), (390, 844), (1366, 900)])
def test_invoice_exceptions_reset_blank_validation_and_receipt(
    stage2_server, stage2_database, width, height
):
    owner, _ = stage2_database
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
        assert page.get_by_label("Standard", exact=True).is_checked()
        assert page.locator('input[type="number"]:visible').count() == 0
        assert page.locator("select:visible").count() == 0
        assert page.locator('[name="bus_ids"]').count() == 0
        assert page.locator(".invoice-row").count() == 3
        assert page.locator("#invoice-total").inner_text() == "K 5,400.00"
        assert page.get_by_label("Reason", exact=True).count() == 0
        folder = Path(".local/browser")
        folder.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(folder / f"cashing-standard-{width}.png"), full_page=True)
        page.get_by_label("Adjusted Buses", exact=True).check()
        assert page.locator(".adjust-trigger:visible").count() == 3
        page.get_by_label("Adjust DEMO101", exact=True).check()
        assert page.locator("[data-adjust-fields]:visible").count() == 1
        page.get_by_role("button", name="Submit Cashing", exact=True).click()
        assert page.get_by_label("DEMO101 actual normal amount (K)").evaluate(
            "e=>e.validity.valueMissing"
        )
        with psycopg.connect(**owner) as connection:
            assert (
                connection.execute("SELECT count(*) FROM remittance_collections").fetchone()[0] == 0
            )
        page.get_by_label("DEMO101 actual normal amount (K)").fill("1e3")
        assert page.locator("#invoice-total").inner_text() == "K 4,600.00"
        page.get_by_label("Adjust DEMO101", exact=True).uncheck()
        assert page.locator("#invoice-total").inner_text() == "K 5,400.00"
        assert page.locator("[data-adjust-fields]:visible").count() == 0
        page.get_by_label("Adjust DEMO101", exact=True).check()
        page.get_by_label("DEMO101 actual normal amount (K)").fill("0")
        first = page.locator(".cashing-choice").filter(has=page.get_by_text("DEMO101", exact=True))
        first.get_by_label("Classification", exact=True).select_option(
            "CONFIRMED_UNPAID_OBLIGATION"
        )
        first.get_by_label("Reason if different", exact=True).fill("Driver will pay later")
        first.get_by_label("Responsible person (confirmed unpaid)").fill("Synthetic driver")
        page.get_by_label("Adjust DEMO102", exact=True).check()
        page.get_by_label("DEMO102 actual normal amount (K)").fill("2000")
        second = page.locator(".cashing-choice").filter(has=page.get_by_text("DEMO102", exact=True))
        second.get_by_label("Classification", exact=True).select_option("SURPLUS")
        second.get_by_label("Reason if different", exact=True).fill("Extra received")
        assert page.locator("#invoice-total").inner_text() == "K 3,800.00"
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        page.screenshot(path=str(folder / f"cashing-adjusted-{width}.png"), full_page=True)
        page.get_by_role("button", name="Submit Cashing", exact=True).click()
        page.wait_for_url("**/receipt")
        assert page.get_by_role("heading", name="Recorded Cashing", exact=True).is_visible()
        assert page.locator(".invoice-total").inner_text().endswith("K 3,800.00")
        page.reload()
        with psycopg.connect(**owner) as connection:
            assert connection.execute(
                "SELECT count(*),sum(amount) FROM financial_transactions"
            ).fetchone() == (1, 3800)
            assert (
                connection.execute(
                    "SELECT sum(outstanding_amount) FROM cashing_obligations"
                ).fetchone()[0]
                == 1800
            )
        page.get_by_role("link", name="Record another", exact=True).click()
        assert page.get_by_label("Standard", exact=True).is_checked()
        assert page.locator('[name="adjust_ids"]:checked').count() == 0
        assert page.get_by_label("Comment (optional)").input_value() == ""
        assert not errors
        browser.close()
