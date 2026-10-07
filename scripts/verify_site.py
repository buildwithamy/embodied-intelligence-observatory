"""Local browser acceptance: real rendering, collapsible notes and responsive overflow."""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CHROME = Path.home() / "AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe"


def verify():
    output = ROOT / "docs/screenshots"
    output.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as engine:
        browser = engine.chromium.launch(executable_path=str(CHROME), headless=True)
        for label, viewport in (("desktop", {"width": 1440, "height": 1000}),
                                ("mobile", {"width": 390, "height": 844})):
            page = browser.new_page(viewport=viewport, device_scale_factor=1,
                                    is_mobile=label == "mobile", has_touch=label == "mobile")
            errors = []
            failed = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("requestfailed", lambda request: failed.append(request.url))
            page.goto((ROOT / "site/index.html").as_uri(), wait_until="networkidle")
            for picture in page.locator('main img').all():
                picture.scroll_into_view_if_needed()
                picture.evaluate('(x) => x.decode()')
            page.evaluate("scrollTo({top: 0, behavior: 'instant'})")
            page.screenshot(path=str(output / f"2026-W40-{label}.png"))
            page.screenshot(path=str(output / f"2026-W40-{label}-full.png"), full_page=True)
            assert page.locator('.hero-signal').count() == 3
            assert page.locator('.top-story').count() == 5
            assert page.locator('.paper-card').count() == 6
            assert page.locator('.paper-card details[open]').count() == 0
            assert page.locator('.method-section details[open]').count() == 0
            assert page.locator('main > section').count() == 10
            assert page.locator('svg').count() >= 2
            dimensions = page.evaluate("""() => ({width: innerWidth,
                pageWidth: document.documentElement.scrollWidth,
                heroBottom: document.querySelector('.hero').getBoundingClientRect().bottom,
                coverImage: document.querySelector('.cover-figure img').getBoundingClientRect().toJSON(),
                lastSignalFactBottom: document.querySelector('.hero-signal:last-child p').getBoundingClientRect().bottom,
                signalTitles: [...document.querySelectorAll('.hero-signal h3')].map(x => ({
                    title: x.innerText, y: x.getBoundingClientRect().top}))})""")
            assert dimensions['pageWidth'] <= dimensions['width'], dimensions
            assert max(s['y'] for s in dimensions['signalTitles']) < viewport['height'], dimensions
            assert dimensions['lastSignalFactBottom'] <= viewport['height'], dimensions
            if label == 'mobile':
                matrix = page.locator('.matrix-scroll')
                assert matrix.evaluate('(x) => x.scrollWidth > x.clientWidth')
                matrix.evaluate('(x) => x.scrollLeft = 120')
                assert matrix.evaluate('(x) => x.scrollLeft') > 0
            for section in ('timeline', 'impact', 'research', 'learning', 'story-homes', 'story-world-model-loop'):
                page.locator('#' + section).screenshot(path=str(output / f'2026-W40-{label}-{section}.png'),
                    style='.section-nav,.reading-progress,.skip-link{visibility:hidden}')
            page.locator('.paper-card details summary').first.click()
            assert page.locator('.paper-card details[open]').count() == 1
            assert page.get_by_text('作者报告的结果', exact=True).first.is_visible()
            page.locator('.method-section > details > summary').click()
            assert page.locator('.source-index').is_visible()
            page.locator('.internal-audit > summary').click()
            assert page.locator('.internal-audit pre').is_visible()
            assert not errors and not failed, (errors, failed)
            assert page.locator('.cover-figure img').evaluate('(x) => x.complete && x.naturalWidth > 0')
            for picture in page.locator('.story-figure img').all():
                assert picture.evaluate('(x) => x.complete && x.naturalWidth > 0')
                selected_src = picture.evaluate('(x) => x.currentSrc')
                assert ('-mobile.svg' in selected_src) == (label == 'mobile')
            page.locator('.industry-register > summary').click()
            assert page.locator('.industry-grid').is_visible()
            results.append({'viewport': label, 'dimensions': dimensions,
                            'console_errors': errors, 'failed_requests': failed,
                            'paper_details': 'passed', 'methodology_details': 'passed',
                            'original_figures': '3 loaded', 'industry_details': 'passed'})
            page.close()
        page = browser.new_page()
        page.goto((ROOT / 'site/weekly/2026-W40/index.html').as_uri(), wait_until='networkidle')
        assert page.locator('h1').inner_text().replace('\n', '') == json.loads(
            (ROOT / 'data/editorial/2026-W40-v03.json').read_text(encoding='utf-8'))['headline']
        assert page.locator('.hero').evaluate('(x) => getComputedStyle(x).display') != 'none'
        assert page.locator('body').evaluate('(x) => getComputedStyle(x).backgroundColor') == 'rgb(243, 241, 232)'
        responsive_checks = []
        for width in (320, 768, 1280):
            page.set_viewport_size({'width': width, 'height': 1000})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert page.locator('.cover-figure img').is_visible()
            responsive_checks.append({'width': width, 'page_width': page.evaluate('document.documentElement.scrollWidth'),
                                      'cover_visible': True})
        browser.close()
    target = ROOT / 'runs/2026-W40-browser-verification.json'
    target.write_text(json.dumps({'mode': 'local_file_chromium', 'results': results,
                                  'detail_page_assets': 'passed', 'additional_viewports': responsive_checks},
                                 ensure_ascii=False, indent=2), encoding='utf-8')
    print(target.read_text(encoding='utf-8'))


if __name__ == '__main__':
    verify()
