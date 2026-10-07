"""Check the V0.4 preview/formal site without changing the publication."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CHROME = Path.home() / 'AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe'


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('--page', type=Path, default=ROOT / 'site/previews/2026-W40-v04/index.html')
    args = cli.parse_args()
    output = ROOT / 'docs/screenshots'
    results = []
    with sync_playwright() as engine:
        browser = engine.chromium.launch(executable_path=str(CHROME), headless=True)
        for label, width, height in [('desktop', 1440, 1000), ('mobile', 390, 844), ('small', 320, 1000)]:
            page = browser.new_page(viewport={'width': width, 'height': height})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(args.page.resolve().as_uri(), wait_until='networkidle')
            for picture in page.locator('main img').all():
                picture.scroll_into_view_if_needed()
                picture.evaluate('(x)=>x.decode()')
            page.evaluate("scrollTo({top:0,behavior:'instant'})")
            page.screenshot(path=str(output / f'2026-W40-v04-{label}.png'))
            page.locator('#stories').screenshot(path=str(output / f'2026-W40-v04-{label}-stories.png'),
                style='.section-nav,.reading-progress,.skip-link{visibility:hidden}')
            assert page.locator('.top-story').count() == 5
            assert page.locator('.top-story').first.locator('h3').inner_text().startswith('AMD 拟收购')
            assert page.locator('.paper-card').count() == 6
            assert page.locator('.paper-card details[open]').count() == 0
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
            assert not errors, errors
            page.locator('.paper-card details summary').first.click()
            assert page.get_by_text('作者报告的结果', exact=True).first.is_visible()
            assert page.locator('.cover-figure img').evaluate('(x)=>x.naturalWidth>0')
            page.evaluate("scrollTo({top:0,behavior:'instant'})")
            last = page.locator('.hero-signal').last.locator('p').first.evaluate('(x)=>x.getBoundingClientRect().bottom')
            if width != 320:
                assert last <= height, last
            results.append({'viewport': label, 'width': width, 'overflow': False,
                            'console_errors': errors, 'last_hero_fact_bottom': last, 'amd_first': True})
            page.close()
        browser.close()
    target = ROOT / 'runs/2026-W40/v04-browser-verification.json'
    target.write_text(json.dumps({'page': str(args.page), 'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(target.read_text(encoding='utf-8'))


if __name__ == '__main__':
    main()
