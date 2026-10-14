"""Read-only Help navigation, expanders, search and viewport checks."""
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    output=Path('backups/step5-ui')
    output.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe',headless=True)
        for width,height in ((390,844),(1440,1000)):
            page=browser.new_page(viewport={'width':width,'height':height})
            page.goto('http://localhost:8501/')
            page.locator('[data-testid=stBottom]').get_by_text('More',exact=True).click()
            page.get_by_text('Help & Guide',exact=True).click()
            page.get_by_text('Welcome to SmartFleet',exact=True).wait_for()
            search=page.get_by_label('Search guides')
            search.fill('Business Balance')
            search.press('Enter')
            question=page.get_by_text('How do I understand Business Balance?',exact=True)
            question.click()
            page.get_by_text("Open Finance > Balances. Business Balance Now shows today's recorded business cash position.",exact=False).wait_for()
            page.screenshot(path=str(output/f'help_balance_{width}.png'))
            search.fill('xyznoresult')
            search.press('Enter')
            page.get_by_text('No matching guides. Try another word or choose All categories.',exact=True).wait_for()
            search.fill('')
            search.press('Enter')
            page.get_by_text('How do I record Thursday/Sunday cashing?',exact=True).wait_for()
            assert page.locator('[data-testid=stException]').count()==0
            assert page.evaluate('document.documentElement.scrollWidth')<=width+2
            print(f'Help navigation/search/expansion/empty-state/restore at {width}px PASS')
            page.close()
        browser.close()


if __name__=='__main__':
    main()
