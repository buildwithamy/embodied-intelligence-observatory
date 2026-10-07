"""Build the site: every issue page, the home page with the issue list, and README's issue block.

Usage: python site/build.py
Reads site/issues.toml; writes site/issues/<slug>/index.html, site/index.html and the
part of README.md between the issues markers.
"""
import html
import pathlib
import re
import runpy
import tomllib

SITE = pathlib.Path(__file__).resolve().parent
README = SITE.parent / "README.md"
START, END = "<!-- issues:start -->", "<!-- issues:end -->"


def esc(text):
    return html.escape(text, quote=False)


def inline_svg(path):
    svg = path.read_text(encoding="utf-8")
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg)
    svg = re.sub(r"<metadata>.*?</metadata>", "", svg, flags=re.S)
    return re.sub(r'\s+xmlns:c2pa="[^"]*"', "", svg).strip()


def heading(issue):
    label = f' · {issue["label"]}' if issue.get("label") else ""
    return f'第 {issue["no"]} 期{label} · {issue["window"]}'


def latest_card(issue):
    art = inline_svg(SITE / "issues" / issue["slug"] / issue["art"])
    points = "".join(f"<li><i>{esc(k)}</i><span>{esc(v)}</span></li>" for k, v in issue["highlights"])
    return (f'<div class="sh"><h2>最新一期</h2></div>'
            f'<a class="latest" href="issues/{issue["slug"]}/">'
            f'<div class="art" aria-hidden="true">{art}</div>'
            f'<div><div class="meta">{esc(heading(issue))}</div>'
            f'<h3>{esc(issue["title"])}</h3><p class="subt">{esc(issue["subtitle"])}</p>'
            f'<p class="lede">{esc(issue["summary"])}</p><ul class="hl">{points}</ul>'
            f'<span class="cta">阅读第 {issue["no"]} 期 →</span></div></a>')


def issue_rows(data):
    rows = []
    upcoming = data.get("next")
    if upcoming:
        rows.append(f'<div class="row next"><span class="num">{upcoming["no"]:02d}</span>'
                    f'<span class="tx"><b>制作中</b><small>下一期</small></span>'
                    f'<span class="win">{upcoming["window"]}</span></div>')
    for issue in data["issues"]:
        tag = f'<span class="tag">{esc(issue["label"])}</span>' if issue.get("label") else ""
        rows.append(f'<a class="row" href="issues/{issue["slug"]}/"><span class="num">{issue["no"]:02d}</span>'
                    f'<span class="tx"><b>{esc(issue["title"])}</b><small>{esc(issue["subtitle"])}</small></span>'
                    f'<span class="win">{issue["window"]}</span>{tag}</a>')
    return "".join(rows)


def readme_block(data):
    base, latest = data["site"]["base"], data["issues"][0]
    url = f'{base}issues/{latest["slug"]}/'
    folder = SITE / "issues" / latest["slug"]
    image = "cover.jpg" if (folder / "cover.jpg").exists() else "og.png"
    lines = [START, "", "## 最新一期", "", f"**{heading(latest)}**", "",
             f'### {latest["title"]}：{latest["subtitle"]}', "",
             f'[![第 {latest["no"]} 期首屏]({folder.relative_to(SITE.parent).as_posix()}/{image})]({url})', "",
             latest["summary"], "", "| 栏目 | 要点 |", "|---|---|",
             *(f"| {k} | {v} |" for k, v in latest["highlights"]), "",
             f'**[在线阅读第 {latest["no"]} 期 →]({url})**', "", "## 全部期刊", "",
             "| 期号 | 时间窗口 | 主题 |", "|---|---|---|"]
    for issue in data["issues"]:
        label = f'（{issue["label"]}）' if issue.get("label") else ""
        lines.append(f'| [第 {issue["no"]} 期{label}]({base}issues/{issue["slug"]}/) | {issue["window"]} '
                     f'| {issue["title"]}：{issue["subtitle"]} |')
    if data.get("next"):
        lines += ["", f'下一期：第 {data["next"]["no"]} 期，{data["next"]["window"]}，制作中。']
    return "\n".join(lines + ["", END])


def main():
    data = tomllib.loads((SITE / "issues.toml").read_text(encoding="utf-8"))
    for issue in data["issues"]:
        runpy.run_path(str(SITE / "issues" / issue["slug"] / "src" / "build.py"))
    page = (SITE / "home.html").read_text(encoding="utf-8")
    latest = data["issues"][0]
    values = {"{{base}}": data["site"]["base"], "{{repo}}": data["site"]["repo"],
              "{{og_image}}": f'{data["site"]["base"]}issues/{latest["slug"]}/og.png',
              "{{latest}}": latest_card(latest), "{{issues}}": issue_rows(data)}
    for key, value in values.items():
        page = page.replace(key, value)
    assert "{{" not in page, "unfilled placeholder in home.html"
    (SITE / "index.html").write_text(page, encoding="utf-8", newline="\n")
    text = README.read_text(encoding="utf-8")
    start, end = text.index(START), text.index(END) + len(END)
    README.write_text(text[:start] + readme_block(data) + text[end:], encoding="utf-8", newline="\n")
    print("built home page and README issue list:", len(data["issues"]), "issue(s)")


main()
