import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from tests.integration.test_stage4 import (
    reporting_data as reporting_data,
)  # shared realistic fixture

pytestmark = [pytest.mark.integration, pytest.mark.browser]


@pytest.mark.parametrize("width,height", [(375, 667), (390, 844), (1366, 900)])
def test_dashboard_charts_balances_tabs_and_periods(stage2_server, reporting_data, width, height):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.environ.get("SMARTFLEET_BROWSER_CHANNEL"))
        page = browser.new_page(viewport={"width": width, "height": height})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(stage2_server + "/login")
        page.get_by_label("Username").fill("browser-owner")
        page.get_by_label("Password", exact=True).fill("browser-synthetic-passphrase")
        page.get_by_role("button", name="Sign in").click()
        page.wait_for_url(stage2_server + "/")
        page.wait_for_function("window.Chart && Chart.getChart('bars')")
        assert page.locator(".metrics .metric").count() == 3
        assert page.get_by_text("Total Revenue", exact=True).is_visible()
        assert page.get_by_text("Total Expenses", exact=True).is_visible()
        assert page.locator('.metric-value[data-value="-3600.00"]').is_visible()
        chart = page.evaluate("""() => {
            const b=Chart.getChart('bars'), l=Chart.getChart('timeline');
            return {cost:b.data.datasets[1].data[0], min:b.scales.y.min,
                bases:b.data.datasets.map((_,i)=>b.getDatasetMeta(i).data[0].base),
                zero:b.scales.y.getPixelForValue(0),negative:l.scales.y.min,
                expenseTop:b.getDatasetMeta(1).data[0].y,
                revenueTop:b.getDatasetMeta(0).data[0].y,
                pixels:[...b.ctx.getImageData(0,0,b.width,b.height).data].filter((v,i)=>i%4===3 && v>0).length};
        }""")
        assert chart["cost"] == 6300 and chart["min"] == 0
        assert all(abs(v - chart["zero"]) < 1 for v in chart["bases"])
        assert chart["expenseTop"] < chart["revenueTop"] < chart["zero"]
        assert chart["negative"] < 0 and chart["pixels"] > 1000
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        artifacts = Path(".local/browser")
        artifacts.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(artifacts / f"stage4-home-{width}.png"), full_page=True)
        page.locator("main").evaluate("e=>{e.scrollTop=e.scrollHeight}")
        page.get_by_role("navigation", name="Main navigation").get_by_role(
            "link", name="Finance", exact=True
        ).click()
        page.get_by_role("navigation", name="Finance sections").get_by_role(
            "link", name="Balances", exact=True
        ).click()
        assert page.get_by_text("Business Balance Now", exact=True).is_visible()
        assert page.get_by_text("Money Received", exact=True).count() == 1
        assert page.get_by_text("Money Paid Out", exact=True).count() == 1
        top = page.locator(".balance-now").bounding_box()
        picker = page.locator(".period-picker").bounding_box()
        assert top["y"] + top["height"] <= picker["y"]
        page.get_by_label("Custom", exact=True).check()
        page.get_by_label("Custom period", exact=True).select_option("dates")
        page.get_by_label("Start date", exact=True).fill("2026-10-01")
        page.get_by_label("End date", exact=True).fill("2026-10-10")
        page.get_by_role("button", name="Apply period").click()
        assert page.locator(".balance-now .metric-value").get_attribute("data-value") == "-3600.00"
        assert (
            page.locator(".metrics.two .metric-value").nth(0).get_attribute("data-value")
            == "3600.00"
        )
        assert (
            page.locator(".metrics.two .metric-value").nth(1).get_attribute("data-value")
            == "6700.00"
        )
        header = page.locator(".app-header").bounding_box()
        tabs = page.locator(".section-heading").bounding_box()
        nav = page.locator(".bottom-nav").bounding_box()
        page.locator("main").evaluate("e=>{e.scrollTop=e.scrollHeight}")
        assert header == page.locator(".app-header").bounding_box()
        assert tabs == page.locator(".section-heading").bounding_box()
        assert nav == page.locator(".bottom-nav").bounding_box()
        page.goto(stage2_server + "/bus-accounts")
        page.wait_for_function("window.Chart && Chart.getChart('bars')")
        registration = page.locator(".table-scroll tbody a").first
        registration.click()
        page.wait_for_function("window.Chart && Chart.getChart('bars')")
        assert page.get_by_text("Costs by category", exact=True).is_visible()
        assert page.evaluate("Chart.getChart('bars').data.datasets[1].data[0]") == 6300
        assert not errors
        browser.close()
