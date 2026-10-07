"""Inline src/art/*.svg into src/page.html and write ../index.html.

The source SVGs keep their C2PA content credentials; the inline copies drop
that metadata so the page stays light.
"""
import pathlib
import re

SRC = pathlib.Path(__file__).resolve().parent


def inline(match):
    svg = (SRC / "art" / (match.group(1) + ".svg")).read_text(encoding="utf-8")
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg)
    svg = re.sub(r"<metadata>.*?</metadata>", "", svg, flags=re.S)
    svg = re.sub(r'\s+xmlns:c2pa="[^"]*"', "", svg)
    return svg.strip()


page = re.sub(r"\{\{svg:([\w-]+)\}\}", inline, (SRC / "page.html").read_text(encoding="utf-8"))
assert "{{" not in page
(SRC.parent / "index.html").write_text(page, encoding="utf-8", newline="\n")
print("built", len(page))
