"""Sync the authorized color theme without republishing or changing editorial selection."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / 'templates/weekly.css'
    css = source.read_text(encoding='utf-8')
    colors = {
        'var(--green)': 'var(--accent-strong)', 'var(--lime)': 'var(--surface-card)',
        'var(--rust)': 'var(--accent)', '#849273': 'var(--index)', '#81926f': 'var(--index)',
        '#99b257': 'var(--accent)', '#e8ecdc': 'var(--surface-soft)', '#9aab8a': 'var(--index)',
        '#d6ddc9': 'var(--line)', '#b77452': 'var(--accent)', '#a5b695': 'var(--accent)',
        '#e9ede1': 'var(--surface-soft)', '#c3d5be': '#ded7cd', '#c8dda4': '#d9b8a3',
        '#8dbb87': 'var(--accent)', '#e0e9d1': 'var(--surface-card)', '#6e885b': 'var(--muted)',
        '#ecefdf': 'var(--surface-soft)', '#9ba998': 'var(--muted)', '#466a42': 'var(--accent)',
        '#e7ebdf': 'var(--surface-card)',
    }
    for old, new in colors.items():
        css = css.replace(old, new)
    css = css.replace('.flow-figure { background: var(--accent-strong);',
                      '.flow-figure { background: var(--surface-dark);')
    css = css.replace('.flow-figure h3 { font:', '.flow-figure h3 { color: var(--paper); font:')
    svg_filter = '.story-figure img[src$=".svg"] { filter: sepia(.78) saturate(.55); }'
    if svg_filter not in css:
        css = css.replace('.story-figure img { border: 1px solid var(--line); }',
                          '.story-figure img { border: 1px solid var(--line); }\n' + svg_filter)
    source.write_text(css, encoding='utf-8')
    for destination in ('site/assets/weekly.css', 'site/previews/2026-W40-v04/assets/weekly.css',
                        'output/v04-preview/site/assets/weekly.css'):
        path = ROOT / destination
        if path.parent.exists():
            path.write_bytes(source.read_bytes())
            print(destination)
    for destination in ('templates/weekly.html', 'site/index.html', 'site/weekly/2026-W40/index.html',
                        'site/previews/2026-W40-v04/index.html',
                        'site/previews/2026-W40-v04/weekly/2026-W40/index.html',
                        'output/v04-preview/site/index.html',
                        'output/v04-preview/site/weekly/2026-W40/index.html'):
        path = ROOT / destination
        if path.exists():
            html = path.read_text(encoding='utf-8')
            updated = html.replace('weekly.css"', 'weekly.css?theme=parchment-1"')
            if updated != html:
                path.write_text(updated, encoding='utf-8')


if __name__ == '__main__':
    main()
