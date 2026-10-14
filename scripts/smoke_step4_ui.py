"""Read-only desktop/mobile browser checks; never submit live money forms."""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    output=Path('backups/step4-ui')
    output.mkdir(exist_ok=True)
    results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe',headless=True)
        for width,height in [(390,844),(1440,1000)]:
            context=browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1)
            page=context.new_page()
            for route in ('','buses','finance','record_expense','record_servicing','reports'):
                page.goto('http://localhost:8501/'+route)
                page.locator('[data-testid="stAppViewContainer"]').wait_for()
                page.wait_for_timeout(2200)
                page.locator('[data-testid="stBottom"]').wait_for(timeout=30000)
                page.wait_for_function("document.querySelectorAll('[data-testid=stSkeleton]').length === 0",timeout=30000)
                assert page.locator('[data-testid="stException"]').count()==0, route
                page.screenshot(path=str(output/f'{route or "home"}_{width}.png'),full_page=True)
                sizes=page.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
                assert sizes['scroll']<=width+2,(route,sizes)
                if route=='':
                    chart=page.locator('.st-key-home_financial_chart')
                    chart.wait_for()
                    metrics=chart.evaluate('(e)=>({width:e.clientWidth,scroll:e.scrollWidth})')
                    chart.locator('canvas, svg').first.wait_for(timeout=30000)
                    chart.scroll_into_view_if_needed()
                    page.screenshot(path=str(output/f'chart_{width}.png'))
                    if width==390:
                        assert metrics['scroll']>metrics['width']+100,metrics
                        chart.evaluate('(e)=>e.scrollLeft=100')
                        assert chart.evaluate('(e)=>e.scrollLeft')>0
                    canvas=chart.locator('canvas').first
                    if canvas.count():
                        assert canvas.evaluate('(c)=>{let a=c.getContext("2d").getImageData(0,0,c.width,c.height).data;return a.some((v,i)=>i%4===3&&v>0)}')
                    symbols=chart.locator('g.mark-symbol.role-mark path')
                    assert symbols.count()>0, 'Chart point symbols missing'
                    symbols.first.hover(force=True)
                    page.locator('#vg-tooltip-element').wait_for(state='visible',timeout=10000)
                    results.append({'viewport':width,'tooltips':'PASS'})
                    results.append({'viewport':width,'chart':metrics})
                results.append({'viewport':width,'route':route or 'home','status':'PASS'})
            context.close()
        browser.close()
    (output/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))


if __name__=='__main__':
    main()
