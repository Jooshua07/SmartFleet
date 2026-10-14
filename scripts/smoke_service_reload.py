"""Disposable generated fixture: changed and newly exported services reload."""
from pathlib import Path
import subprocess
import sys
import tempfile

from playwright.sync_api import sync_playwright


def main():
    root=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='reload_',dir=root/'backups') as folder:
        directory=Path(folder)
        service=directory/'reload_fixture_service.py'
        app=directory/'fixture_app.py'
        # These are disposable test fixtures, never application or database edits.
        service.write_text("def value():\n    return 'initial'\n",encoding='utf-8')
        app.write_text("import streamlit as st\nfrom reload_fixture_service import value\nst.write(value())\n",encoding='utf-8')
        with (directory/'server.log').open('w',encoding='utf-8') as log:
            server=subprocess.Popen([sys.executable,'-m','streamlit','run',str(app),
                '--server.address','127.0.0.1','--server.port','8503','--server.headless','true',
                '--server.fileWatcherType','poll','--server.runOnSave','true'],cwd=root,
                stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            try:
                with sync_playwright() as p:
                    browser=p.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe',headless=True)
                    try:
                        page=browser.new_page()
                        # Retry startup through Playwright's wait without long blocking sleeps.
                        from time import monotonic, sleep
                        deadline=monotonic()+20
                        while True:
                            try:
                                page.goto('http://localhost:8503',timeout=2000)
                                break
                            except Exception:
                                if server.poll() is not None or monotonic()>deadline:
                                    raise
                                sleep(.2)
                        page.get_by_text('initial',exact=True).wait_for()
                        page.wait_for_timeout(2000)
                        service.write_text("def value():\n    return 'changed dependency'\n",encoding='utf-8')
                        page.get_by_text('changed dependency',exact=True).wait_for(timeout=15000)
                        service.write_text("def value():\n    return 'changed dependency'\ndef added_value():\n    return 'new export loaded'\n",encoding='utf-8')
                        page.get_by_text('changed dependency',exact=True).wait_for()
                        page.wait_for_timeout(1500)
                        app.write_text("import streamlit as st\nfrom reload_fixture_service import added_value\nst.write(added_value())\n",encoding='utf-8')
                        page.get_by_text('new export loaded',exact=True).wait_for(timeout=15000)
                        assert page.locator('[data-testid=stException]').count()==0
                        print('Polling reload: changed dependency and newly exported function loaded without restart PASS')
                    finally:
                        browser.close()
            finally:
                server.terminate()
                server.wait(timeout=10)


if __name__=='__main__':
    main()
