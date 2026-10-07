"""Export the current weekly webpage as one continuous, searchable PDF page."""
import json
import math
from pathlib import Path

import fitz
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CHROME = Path.home() / 'AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe'
OUTPUT = ROOT / 'output/pdf/具身智能观察-2026-W40-网页长页.pdf'
QA = ROOT / 'tmp/pdfs/2026-W40-long-page'


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as engine:
        browser = engine.chromium.launch(executable_path=str(CHROME), headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto((ROOT / 'site/weekly/2026-W40/index.html').as_uri(), wait_until='networkidle')
        # Screen media preserves the current website instead of its simplified print theme.
        page.emulate_media(media='screen', reduced_motion='reduce')
        page.add_style_tag(content='''
            html { scroll-behavior: auto !important; }
            .section-nav { position: static !important; }
            .reading-progress, .skip-link { display: none !important; }
            *, *::before, *::after {
                animation: none !important; transition: none !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }
            .internal-audit { display: none !important; }
        ''')
        page.evaluate("document.querySelectorAll('details:not(.internal-audit)').forEach(d => d.open = true)")
        page.evaluate('document.fonts.ready')
        for picture in page.locator('main img').all():
            picture.scroll_into_view_if_needed()
            picture.evaluate('(x) => x.decode()')
        page.evaluate("scrollTo({top: 0, behavior: 'instant'})")
        size = page.evaluate('({width: innerWidth, height: document.documentElement.scrollHeight, scrollWidth: document.documentElement.scrollWidth})')
        assert size['width'] == size['scrollWidth'], size
        assert not errors, errors
        title = page.locator('h1').inner_text().replace('\n', '')
        # Four extra CSS pixels guard against fractional layout rounding at the footer.
        height = math.ceil(size['height']) + 4
        page.pdf(path=str(OUTPUT), width=f"{size['width']}px", height=f'{height}px',
                 print_background=True, display_header_footer=False,
                 margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'},
                 prefer_css_page_size=False, tagged=True, outline=True)
        headings = page.locator('h2').all_inner_texts()
        browser.close()

    with fitz.open(OUTPUT) as document:
        assert len(document) == 1, f'Expected one long page, got {len(document)}'
        sheet = document[0]
        text = sheet.get_text()
        compact = ''.join(text.split())
        assert ''.join(title.split()) in compact, 'Cover title absent from PDF text'
        for heading in headings:
            assert ''.join(heading.split()) in compact, f'Missing section: {heading}'
        assert '每周读几条消息' in compact, 'Footer missing'
        assert '作者报告的结果' in compact, 'Expanded paper notes missing'
        assert '来源与核验详情' in compact, 'Sources missing'
        sheet.get_pixmap(matrix=fitz.Matrix(0.28, 0.28), alpha=False).save(QA / 'overview.png')
        previews = []
        for label, top, bottom in (
            ('cover', 0, 800),
            ('middle', sheet.rect.height * 0.42, sheet.rect.height * 0.42 + 800),
            ('papers', sheet.rect.height * 0.69, sheet.rect.height * 0.69 + 1000),
            ('footer', sheet.rect.height - 900, sheet.rect.height),
        ):
            target = QA / f'{label}.png'
            sheet.get_pixmap(matrix=fitz.Matrix(1, 1),
                             clip=fitz.Rect(0, top, sheet.rect.width, bottom), alpha=False).save(target)
            previews.append(str(target))
        report = {'file': str(OUTPUT), 'pages': len(document), 'bytes': OUTPUT.stat().st_size,
                  'page_points': list(sheet.rect), 'source_css_pixels': size,
                  'text_characters': len(text), 'sections_verified': headings,
                  'paper_notes': 'expanded', 'sources': 'expanded', 'preview_images': previews}
    (QA / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
