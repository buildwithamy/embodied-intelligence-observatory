"""Editorial issue schema and reusable static issue build, separate from collectors."""
from __future__ import annotations

import hashlib
import html
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .major_events import MajorEvent
from .models import Candidate, utcnow
from .pipeline import config, load_items, load_json, validate_week, write_json


class EditorialModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Signal(EditorialModel):
    title: str
    fact: str
    meaning: str
    refs: list[str] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class Story(EditorialModel):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    title: str
    deck: str
    refs: list[str] = Field(min_length=1)
    why_now: str
    applications: list[str]
    education: str
    questions: list[str] = Field(max_length=3)
    limits: str
    paragraphs: list[str] = Field(default_factory=list, max_length=2)


class EditorialFigure(EditorialModel):
    src: str = Field(pattern=r"^[a-z0-9-]+\.svg$")
    mobile_src: str | None = Field(default=None, pattern=r"^[a-z0-9-]+\.svg$")
    alt: str = Field(min_length=1)
    caption: str = Field(min_length=1)
    refs: list[str] = Field(min_length=1)


class Impact(EditorialModel):
    scenario: str
    signal: str
    capability: str
    gap: str
    refs: list[str] = Field(min_length=1)


class MatrixRow(EditorialModel):
    technology: str
    refs: list[str] = Field(min_length=1)
    relations: dict[str, str]
    rationale: str

    @model_validator(mode="after")
    def qualitative_only(self):
        if not set(self.relations.values()).issubset({"直接研究", "潜在关联", "—"}):
            raise ValueError("matrix must use qualitative relations, never maturity scores")
        return self


class ResearchQuestion(EditorialModel):
    title: str
    question: str
    reproduce: str
    refs: list[str] = Field(min_length=1)


class LearningConcept(EditorialModel):
    concept: str
    explanation: str
    curriculum: str
    prerequisites: str
    exercise: str
    refs: list[str] = Field(min_length=1)
    resource_indices: list[int] = Field(default_factory=list)


class IssueEditorial(EditorialModel):
    schema_version: str = "0.3"
    week: str
    headline: str
    cover_title_lines: list[str] = Field(default_factory=list, max_length=3)
    cover_label: str = "本期封面"
    cover_link_text: str = "读本期重点"
    thesis: str
    signals: list[Signal] = Field(min_length=3, max_length=3)
    quick_read: list[Signal] = Field(min_length=1, max_length=15)
    stories: list[Story] = Field(min_length=1, max_length=15)
    impacts: list[Impact] = Field(min_length=1)
    matrix_columns: list[str]
    matrix: list[MatrixRow]
    research: list[ResearchQuestion] = Field(min_length=2, max_length=3)
    paper_ids: list[str] = Field(min_length=4, max_length=8)
    paper_takeaways: dict[str, str]
    paper_notes: dict[str, str] = Field(default_factory=dict)
    learning: list[LearningConcept] = Field(min_length=1, max_length=3)
    monthly_comparison: str
    methodology: str
    cover_figure: EditorialFigure | None = None
    story_figures: dict[str, EditorialFigure] = Field(default_factory=dict)
    event_briefs: dict[str, str] = Field(default_factory=dict)


def escape(text):
    return html.escape(str(text), quote=True)


class IssueContext:
    def __init__(self, events: list[tuple[MajorEvent, str]], papers: list[Candidate]):
        self.events = {"event:" + e.id: e for e, _ in events}
        self.bands = {"event:" + e.id: band for e, band in events}
        self.papers = {"paper:" + c.arxiv_id: c for c in papers if c.arxiv_id and c.analysis
                       and c.analysis.fact_check == "pass"}
        self.timeline_refs = set(self.events)
        self.industry_refs = set(self.events)

    def get(self, ref):
        if ref in self.events:
            return self.events[ref]
        if ref in self.papers:
            return self.papers[ref]
        raise ValueError("unknown or unreviewed issue reference: " + ref)

    def urls(self, refs):
        rows = {}
        for ref in refs:
            item = self.get(ref)
            if isinstance(item, MajorEvent):
                for source in item.sources:
                    rows[source.url] = source.title
            else:
                rows[item.url] = item.title
        return rows

    def factual_paragraphs(self, refs):
        return [self.get(ref).summary if isinstance(self.get(ref), MajorEvent)
                else self.get(ref).analysis.main_results for ref in refs]

    def validate(self, issue: IssueEditorial, resources: list[dict], scenarios: list[str]):
        groups = [*issue.signals, *issue.quick_read, *issue.stories, *issue.impacts, *issue.matrix,
                  *issue.research, *issue.learning]
        for item in groups:
            for ref in item.refs:
                self.get(ref)
        if issue.cover_title_lines and "".join(issue.cover_title_lines) != issue.headline:
            raise ValueError("cover title line breaks must preserve headline")
        for paper in issue.paper_ids:
            self.get("paper:" + paper)
        if len(set(issue.paper_ids)) != len(issue.paper_ids):
            raise ValueError("duplicate reading-list paper")
        if set(issue.paper_takeaways) != set(issue.paper_ids):
            raise ValueError("every reading-list paper requires one takeaway")
        if not set(issue.paper_notes).issubset(issue.paper_ids):
            raise ValueError("reading note requires a selected paper")
        if len({s.id for s in issue.stories}) != len(issue.stories):
            raise ValueError("duplicate top story ID")
        story_refs = {s.id: set(s.refs) for s in issue.stories}
        for story_id, figure in issue.story_figures.items():
            if story_id not in story_refs or not set(figure.refs).issubset(story_refs[story_id]):
                raise ValueError("figure must cite its own story evidence")
        for figure in [*issue.story_figures.values(), *([issue.cover_figure] if issue.cover_figure else [])]:
            for ref in figure.refs:
                self.get(ref)
        if not set(issue.event_briefs).issubset({e.id for e in self.events.values()}):
            raise ValueError("timeline brief requires a confirmed event")
        for item in issue.learning:
            if any(i < 0 or i >= len(resources) for i in item.resource_indices):
                raise ValueError("unknown learning resource")
        for impact in issue.impacts:
            if impact.scenario not in scenarios:
                raise ValueError("unknown application scenario: " + impact.scenario)
        for row in issue.matrix:
            if set(row.relations) != set(issue.matrix_columns):
                raise ValueError("matrix columns must match row relations")


def source_label(url: str, title: str) -> str:
    known = {
        "helix-2-5": "Figure 家庭评测", "cooperatively-safe": "Digit 5 发布说明",
        "agility-and-fort": "FORT 合作公告", "application-center": "Atlas 工厂训练",
        "robot-hands": "Atlas 新手部", "/231.html": "长隆项目公告", "/234.html": "门店项目公告",
        "skild-crosses": "Skild 经营披露", "v3.0.0-EA": "Isaac Lab 3.0 EA",
        "isaac-ros-5-0": "Isaac ROS 5.0", "gbDetailed": "国家标准信息",
        "2609.39685": "RoboCoach", "2609.38059": "WorldLine", "2609.38886": "HIDE / SEEK",
        "2609.38087": "CrossBFM", "2609.35690": "APPL", "2609.36012": "机器人 ICL 综述",
    }
    return next((label for key, label in known.items() if key in url),
                title if len(title) <= 28 else urlsplit(url).hostname or "原始来源")


def source_links(context: IssueContext, refs: list[str]) -> str:
    return " ".join(f'<a href="{escape(url)}" title="{escape(title)}" aria-label="{escape(title)}" '
                    f'target="_blank" rel="noopener">{escape(source_label(url, title))} ↗</a>'
                    for url, title in context.urls(refs).items())


def figure_html(figure: EditorialFigure, asset_prefix: str, *, cover=False) -> str:
    mobile = (f'<source media="(max-width: 600px)" srcset="{escape(asset_prefix + figure.mobile_src)}">'
              if figure.mobile_src else "")
    return (f'<figure class="{"cover-figure" if cover else "story-figure"}">'
            f'<picture>{mobile}<img src="{escape(asset_prefix + figure.src)}" alt="{escape(figure.alt)}" '
            f'width="760" height="{550 if cover else (330 if figure.src == "helix-results.svg" else 365)}" '
            f'loading="{"eager" if cover else "lazy"}" decoding="async"></picture>'
            f'<figcaption>{escape(figure.caption)}'
            f'<a href="{escape(asset_prefix + figure.src)}" target="_blank" rel="noopener" '
            f'aria-label="查看大图：{escape(figure.alt)}">查看大图 ↗</a></figcaption></figure>')


def svg_themes(papers: list[Candidate]) -> str:
    terms = {"世界模型": {"World Model"}, "记忆与技能": {"Memory", "Skill Composition", "Planning"},
             "跨本体": {"Humanoid", "Cross-Embodiment"}, "学习框架": {"Education", "In-Context Learning"}}
    counts = {name: sum(bool(set(c.tags).intersection(tags)) for c in papers) for name, tags in terms.items()}
    maximum = max(counts.values(), default=1) or 1
    bars = []
    for i, (name, count) in enumerate(counts.items()):
        y = 28 + i * 49
        bars.append(f'<text x="0" y="{y + 17}" class="svg-label">{name}</text>'
                    f'<rect x="125" y="{y}" width="{240 * count / maximum}" height="24" rx="2"/>'
                    f'<text x="385" y="{y + 17}" class="svg-label">{count}</text>')
    return (f'<svg viewBox="0 0 420 236" role="img" aria-label="本期{len(papers)}篇精选论文的主题数量，可多标签重叠">'
            + "".join(bars) + '</svg><p class="caption">精选样本内计数，可多标签重叠；不是行业热度或增长率。</p>')


def svg_flow():
    return '''<svg viewBox="0 0 670 188" role="img" aria-label="技术进展通过验证环节进入应用和教学">
    <defs><marker id="flow-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6"/></marker></defs>
    <g class="flow-lines" marker-end="url(#flow-arrow)"><path d="M158 42 H260"/><path d="M158 100 H260"/><path d="M158 158 H260"/>
    <path d="M406 100 H503 V48 H520"/><path d="M503 100 V152 H520"/></g>
    <g class="flow-nodes"><rect x="1" y="18" width="157" height="48"/><rect x="1" y="76" width="157" height="48"/><rect x="1" y="134" width="157" height="48"/>
    <rect x="260" y="65" width="146" height="70"/><rect x="520" y="24" width="146" height="48"/><rect x="520" y="128" width="146" height="48"/></g>
    <g class="svg-label" text-anchor="middle"><text x="79" y="48">世界模型 / 记忆</text><text x="79" y="106">仿真 / 跨本体</text><text x="79" y="164">产品 / 场景评测</text>
    <text x="333" y="94">系统验证</text><text x="333" y="116" class="svg-small">可靠性 · 节拍 · 安全</text><text x="593" y="54">真实场景</text><text x="593" y="158">课程与能力训练</text></g></svg>'''


def render_html(issue: IssueEditorial, context: IssueContext, resources: list[dict], audit: dict,
                template: str, asset_prefix: str) -> str:
    papers = [context.papers["paper:" + aid] for aid in issue.paper_ids]
    unique_sources = set(context.urls(list(context.events) + ["paper:" + aid for aid in issue.paper_ids]))
    ref_stories = {ref: story.id for story in issue.stories for ref in story.refs}
    signals = ""
    for i, s in enumerate(issue.signals, 1):
        target = next(("#story-" + ref_stories[r] for r in s.refs if r in ref_stories), "#quick")
        signals += (f'<article class="hero-signal"><span class="signal-no">0{i}</span><div>'
                    f'<a href="{target}" class="signal-title"><h3>{escape(s.title)} <span>↗</span></h3></a>'
                    f'<p>{escape(s.fact)}</p><p class="signal-meaning">{escape(s.meaning)}</p></div></article>')
    quick = "".join(f'<article class="quick-item"><span class="quick-number">{i:02}</span><div>'
                    f'<div class="eyebrow">{escape(" / ".join(s.tags))}</div><h3>{escape(s.title)}</h3>'
                    f'<p>{escape(s.fact)}</p><p class="muted">{escape(s.meaning)}</p>'
                    f'<div class="source-inline">{source_links(context, s.refs)}</div></div></article>'
                    for i, s in enumerate(issue.quick_read, 1))
    labels = {"industry": "产业", "product": "产品", "models": "模型", "open_source": "开源", "technology": "平台",
              "capital": "资本", "policy": "政策 / 标准", "education": "教育", "new": "首次纳入",
              "developing": "跟踪中", "stable": "持续观察", "resolved": "已结束", "archived": "归档"}
    timeline = "".join(f'<li class="timeline-item"><time datetime="{e.event_date}">{e.event_date.strftime("%m.%d")}</time>'
                       f'<span class="timeline-dot"></span><div><div class="eyebrow">{escape(labels.get(e.categories[0], e.categories[0]))} · '
                       f'{e.importance} · {escape(labels[e.status])} · {context.bands[ref]}</div><h3>{escape(e.title)}</h3>'
                       f'<p>{escape(issue.event_briefs.get(e.id, e.summary))}</p><div class="source-inline">{source_links(context, [ref])}</div></div></li>'
                       for ref, e in sorted(context.events.items(), key=lambda pair: pair[1].event_date)
                       if ref in context.timeline_refs)
    stories = []
    for i, story in enumerate(issue.stories, 1):
        facts = "".join(f'<p>{escape(p)}</p>' for p in (story.paragraphs or context.factual_paragraphs(story.refs)))
        apps = "".join(f'<li>{escape(p)}</li>' for p in story.applications)
        questions = "".join(f'<li>{escape(p)}</li>' for p in story.questions)
        stories.append(f'<article id="story-{story.id}" class="top-story"><div class="story-index">{i:02}</div>'
                       f'<div class="story-body"><h3>{escape(story.title)}</h3><p class="story-deck">{escape(story.deck)}</p>'
                       f'{facts}{figure_html(issue.story_figures[story.id], asset_prefix) if story.id in issue.story_figures else ""}'
                       f'<p class="why-now">{escape(story.why_now)}</p>'
                       f'<div class="implication-grid"><div><h4>应用建议</h4><ul>{apps}</ul></div>'
                       f'<div><h4>教学建议</h4><p>{escape(story.education)}</p></div></div>'
                       f'<details class="research-note"><summary>值得继续研究的问题</summary><ul>{questions}</ul></details>'
                       f'<aside class="limits"><strong>读这条消息时留意</strong><p>{escape(story.limits)}</p></aside>'
                       f'<div class="source-inline">{source_links(context, story.refs)}</div></div></article>')
    impact = "".join(f'<article class="impact-item"><h3>{escape(item.scenario)}</h3><p>{escape(item.signal)}</p>'
                     f'<div><span>可能改善</span><p>{escape(item.capability)}</p></div>'
                     f'<div><span>部署缺口</span><p>{escape(item.gap)}</p></div>'
                     f'<div class="source-inline">{source_links(context, item.refs)}</div></article>' for item in issue.impacts)
    matrix_head = "".join(f'<th scope="col">{escape(c)}</th>' for c in issue.matrix_columns)
    matrix_rows = ""
    for row in issue.matrix:
        cells = "".join(f'<td class="relation-{0 if value == "—" else (2 if value == "直接研究" else 1)}">'
                        f'<abbr title="{escape(value)}">{"●" if value == "直接研究" else ("○" if value == "潜在关联" else "—")}</abbr></td>'
                        for value in (row.relations[c] for c in issue.matrix_columns))
        matrix_rows += f'<tr><th scope="row">{escape(row.technology)}</th>{cells}</tr>'
    matrix_notes = "".join(f'<li><strong>{escape(row.technology)}</strong>：{escape(row.rationale)}</li>' for row in issue.matrix)
    industry_refs = [ref for ref, e in context.events.items() if ref in context.industry_refs and set(e.categories).intersection(
        {"industry", "product", "capital", "models", "open_source", "technology"})]
    featured_refs = {ref for s in issue.stories for ref in s.refs}
    industry_refs.sort(key=lambda ref: (ref in featured_refs, -context.events[ref].event_date.toordinal()))
    industry = "".join(f'<article class="industry-item"><div class="eyebrow">{context.bands[ref]} · {e.event_date}</div>'
                       f'<h3>{escape(e.title)}</h3><p>{escape(issue.event_briefs.get(e.id, e.summary))}</p>'
                       f'<div class="source-inline">{source_links(context, [ref])}</div></article>'
                       for ref in industry_refs for e in [context.events[ref]])
    research = "".join(f'<article><span class="eyebrow">QUESTION 0{i}</span><h3>{escape(q.title)}</h3>'
                       f'<p>{escape(q.question)}</p><p><strong>值得复查</strong> {escape(q.reproduce)}</p>'
                       f'<div class="source-inline">{source_links(context, q.refs)}</div></article>'
                       for i, q in enumerate(issue.research, 1))
    reading = []
    for paper in papers:
        a = paper.analysis
        link = f'<a href="{escape(paper.url)}" target="_blank" rel="noopener">Paper ↗</a>'
        for label, url in (("Project", paper.project_url), ("Code", paper.github_url)):
            if url:
                link += f' <a href="{escape(url)}" target="_blank" rel="noopener">{label} ↗</a>'
        reading.append(f'<article class="paper-card"><div class="eyebrow">{escape(" / ".join(paper.tags))}</div>'
                       f'<h3>{escape(a.chinese_title)}</h3><p class="english-title">{escape(paper.title)}</p>'
                       f'<p>{escape(issue.paper_takeaways[paper.arxiv_id])}</p>'
                       f'<p class="muted">{escape(issue.paper_notes.get(paper.arxiv_id, a.why_it_matters))}</p>'
                       f'<div class="paper-links">{link}</div><details><summary>展开精读笔记</summary>'
                       f'<h4>研究问题</h4><p>{escape(a.research_question)}</p><h4>方法</h4><p>{escape(a.method)}</p>'
                       f'<h4>作者报告的结果</h4><p>{escape(a.main_results)}</p><h4>局限与待验证问题</h4>'
                       f'<p>{escape(a.limitations)}</p></details></article>')
    learning = []
    for item in issue.learning:
        learning_resources = "".join(f'<a href="{escape(resources[i]["url"])}" target="_blank" rel="noopener">'
                                     f'{escape(resources[i]["title"])} ↗</a>' for i in item.resource_indices)
        learning.append(f'<article><h3>{escape(item.concept)}</h3><p>{escape(item.explanation)}</p>'
                        f'<p><strong>课程位置</strong> {escape(item.curriculum)}</p>'
                        f'<p><strong>前置能力</strong> {escape(item.prerequisites)}</p>'
                        f'<div class="exercise"><span>小练习</span><p>{escape(item.exercise)}</p></div>'
                        f'<div class="source-inline">{learning_resources} {source_links(context, item.refs)}</div></article>')
    source_index = "".join(f'<li><a href="{escape(url)}" target="_blank" rel="noopener">{escape(title)} ↗</a></li>'
                           for url, title in context.urls(list(context.events) + ["paper:" + a for a in issue.paper_ids]).items())
    summary = {"major_events": len(context.events), "papers": len(papers), "scenarios": len(issue.impacts),
               "primary_sources": len(unique_sources), "study_concepts": len(issue.learning)}
    coverage = (f'<div><strong>{summary["major_events"]:02}</strong><span>重大进展</span></div>'
                f'<div><strong>{summary["papers"]:02}</strong><span>值得精读</span></div>'
                f'<div><strong>{summary["scenarios"]:02}</strong><span>场景信号</span></div>'
                f'<div><strong>{summary["primary_sources"]:02}</strong><span>一手入口</span></div>')
    internal = escape(json.dumps({"major_news_audit": {k: v for k, v in audit.items()
                                                     if k not in {"audit_records", "event_snapshot"}},
                                 "paper_review": [{"id": c.id, "read_depth": c.analysis.read_depth,
                                                   "origin": c.analysis.origin, "confidence": c.analysis.confidence}
                                                  for c in papers]}, ensure_ascii=False, indent=2))
    headline = "".join(f'<span>{escape(line)}</span>' for line in issue.cover_title_lines) or escape(issue.headline)
    replacements = {"ASSETS": asset_prefix, "WEEK": escape(issue.week), "HEADLINE": headline,
                    "THESIS": escape(issue.thesis), "SIGNALS": signals, "COVERAGE": coverage, "QUICK": quick,
                    "TIMELINE": timeline, "STORIES": "".join(stories), "IMPACT": impact, "FLOW": svg_flow(),
                    "MATRIX_HEAD": matrix_head, "MATRIX_ROWS": matrix_rows, "MATRIX_NOTES": matrix_notes,
                    "INDUSTRY": industry, "THEME": svg_themes(papers), "RESEARCH": research,
                    "PAPERS": "".join(reading), "LEARNING": "".join(learning), "SOURCES": source_index,
                    "METHODOLOGY": escape(issue.methodology), "MONTH_COMPARE": escape(issue.monthly_comparison),
                    "INTERNAL": internal,
                    "COVER_FIGURE": figure_html(issue.cover_figure, asset_prefix, cover=True) if issue.cover_figure else "",
                    "COVER_LABEL": escape(issue.cover_label), "COVER_LINK_TEXT": escape(issue.cover_link_text),
                    "COVER_HREF": next(("#story-" + ref_stories[r] for r in issue.cover_figure.refs
                                        if r in ref_stories), "#quick") if issue.cover_figure else "#quick",
                    "PAPER_COUNT": str(len(papers)), "QUICK_COUNT": str(len(issue.quick_read)),
                    "LEARNING_COUNT": str(len(issue.learning)), "INDUSTRY_COUNT": str(len(industry_refs)),
                    "VERSION": escape(issue.schema_version),
                    "STORIES_NOTE": ('收购协议、模型发布，<br>与机器人开发工具。' if issue.schema_version == '0.4'
                                     else '公司评测、部署现场，<br>还有两项研究。')}
    start = date.fromisocalendar(int(issue.week[:4]), int(issue.week[6:]), 1)
    end = start + timedelta(days=6)
    replacements.update({"WEEK_RANGE": f"{start:%m.%d}—{end:%m.%d}",
                         "YEAR": str(start.year),
                         "MONTH_RANGE": f"{end - timedelta(days=59 if issue.schema_version == '0.4' else 29):%m.%d}—{end:%m.%d}"})
    # Replace only tokens in the original template; user strings cannot inject template placeholders.
    import re

    return re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: replacements[m.group(1)], template)


def render_markdown(issue: IssueEditorial, context: IssueContext, resources: list[dict], image_prefix="../site/assets/") -> str:
    start = date.fromisocalendar(int(issue.week[:4]), int(issue.week[6:]), 1)
    end = start + timedelta(days=6)
    rows = ["# Embodied Intelligence Weekly", "", f"具身智能周刊 · {issue.week} · V{issue.schema_version} 编辑审阅版", "",
            f"周窗口：{start}～{end}；回溯窗口：{end - timedelta(days=59 if issue.schema_version == '0.4' else 29)}～{end}。", "",
            "## 本期一句话", "", issue.headline, "", issue.thesis, ""]
    if issue.cover_figure:
        rows += [f"![{issue.cover_figure.alt}]({image_prefix}{issue.cover_figure.src})", "", issue.cover_figure.caption, ""]
    for signal in issue.signals:
        rows += [f"### {signal.title}", "", signal.fact, "", signal.meaning, ""]
        rows += [f"- [{title}]({url})" for url, title in context.urls(signal.refs).items()]
        rows.append("")
    rows += ["## 10 分钟速读", ""]
    for signal in issue.quick_read:
        rows += [f"### {signal.title}", "", signal.fact, "", signal.meaning, ""]
        rows += [f"- [{title}]({url})" for url, title in context.urls(signal.refs).items()]
        rows.append("")
    rows += ["## 近期重大事件", "", "| 日期 | 事件 | 级别 / 状态 / 窗口 |", "|---|---|---|"]
    for ref, e in sorted(context.events.items(), key=lambda pair: pair[1].event_date):
        if ref not in context.timeline_refs:
            continue
        rows.append(f"| {e.event_date} | [{e.title}]({e.sources[0].url}) | {e.importance} / {e.status} / {context.bands[ref]} |")
    rows += ["", issue.monthly_comparison, "", "## Top Stories", ""]
    for story in issue.stories:
        rows += ["### " + story.title, "", story.deck, "", *(story.paragraphs or context.factual_paragraphs(story.refs)), ""]
        if story.id in issue.story_figures:
            figure = issue.story_figures[story.id]
            rows += [f"![{figure.alt}]({image_prefix}{figure.src})", "", figure.caption, ""]
        rows += [story.why_now, "", "**到应用现场（编辑判断）**", ""]
        rows += ["- " + a for a in story.applications]
        rows += ["", "**放进课堂（编辑建议）** " + story.education, "", "**继续追问**", ""]
        rows += ["- " + q for q in story.questions]
        rows += ["", "**读这条消息时留意** " + story.limits, "", "**Sources**", ""]
        rows += [f"- [{title}]({url})" for url, title in context.urls(story.refs).items()]
        rows.append("")
    rows += ["## Impact Radar", ""]
    for item in issue.impacts:
        rows += ["### " + item.scenario, "", item.signal, "", "可能改善：" + item.capability, "",
                 "部署缺口：" + item.gap, ""]
        rows += [f"- [{title}]({url})" for url, title in context.urls(item.refs).items()]
        rows.append("")
    rows += ["### 技术 × 场景", "", "表示本期信息显示的潜在关联程度，不代表商业成熟度。●直接研究，○潜在关联，—无本期支持。", "",
             "| 技术 | " + " | ".join(issue.matrix_columns) + " |", "|---|" + "---|" * len(issue.matrix_columns)]
    for row in issue.matrix:
        rows.append("| " + row.technology + " | " + " | ".join(row.relations[c] for c in issue.matrix_columns) + " |")
    rows += ["", "<details>", "<summary>关联判断依据</summary>", ""]
    rows += ["- **" + row.technology + "**：" + row.rationale for row in issue.matrix]
    rows += ["", "</details>"]
    rows += ["", "## Industry / Product / Open Source", ""]
    for ref, e in context.events.items():
        if ref not in context.industry_refs:
            continue
        rows += [f"- **{e.title}**（{e.event_date}，{context.bands[ref]}）：{e.why_it_matters}"]
    rows += ["", "## Research Radar", ""]
    for question in issue.research:
        rows += ["### " + question.title, "", question.question, "", "值得复查：" + question.reproduce, ""]
        rows += [f"- [{title}]({url})" for url, title in context.urls(question.refs).items()]
        rows.append("")
    rows += ["## Papers Worth Reading", ""]
    for aid in issue.paper_ids:
        c = context.papers["paper:" + aid]
        a = c.analysis
        rows += ["### " + a.chinese_title, "", c.title, "", issue.paper_takeaways[aid], "",
                 issue.paper_notes.get(aid, a.why_it_matters), "",
                 " · ".join(f"[{label}]({url})" for label, url in
                            (("Paper", c.url), ("Project", c.project_url), ("Code", c.github_url)) if url), "",
                 "<details>", "<summary>展开精读笔记</summary>", "", "**研究问题** " + a.research_question, "",
                 "**方法** " + a.method, "", "**作者报告的结果** " + a.main_results, "",
                 "**局限与Research Note** " + a.limitations, "", "</details>", ""]
    rows += ["## Learning Corner", ""]
    for item in issue.learning:
        rows += ["### " + item.concept, "", item.explanation, "", "课程位置：" + item.curriculum, "",
                 "前置能力：" + item.prerequisites, "", "练习：" + item.exercise, ""]
        rows += [f"- [{resources[i]['title']}]({resources[i]['url']})（持续学习资源）" for i in item.resource_indices]
        rows += [f"- [{title}]({url})" for url, title in context.urls(item.refs).items()]
        rows.append("")
    rows += ["## Sources / Methodology", "", "<details>", "<summary>来源与核验详情</summary>", "", issue.methodology, ""]
    rows += [f"- [{title}]({url})" for url, title in context.urls(list(context.events) + ["paper:" + a for a in issue.paper_ids]).items()]
    rows += ["", f"内部核验与来源失败记录见runs/{issue.week}-major-news-audit.json与V0.1 manifest。", "", "</details>", ""]
    return "\n".join(rows)


def copy_edit_provenance(root: Path, week: str, issue_digest: str, candidates_digest: str, *, version="0.3"):
    """Only attribute reviewed API edits to the exact inputs that were approved."""
    suffix = '-v04-copy-edit.json' if version == '0.4' else '-deepseek-polish.json'
    path = root / 'runs' / (week + suffix)
    if not path.exists():
        return None
    record = load_json(path)
    if record.get('status') != 'reviewed_applied':
        return None
    if (record.get('week') != week or record.get('issue_sha256') != issue_digest
            or record.get('candidates_sha256') != candidates_digest):
        raise ValueError('copy edit record does not match reviewed issue or paper analyses')
    calls = record.get('calls')
    if type(calls) is not int or calls < 1:
        raise ValueError('copy edit API call count must be a positive integer')
    return {key: record[key] for key in ('provider', 'model', 'calls', 'usage', 'status',
                                       'successful_calls', 'failed_calls', 'usage_complete') if key in record}


def build_edition(root: Path, output: Path, week: str, issue_file: Path, *, archive=False, dry_run=False,
                  selection_file: Path | None = None):
    validate_week(week)
    from .editorial_gate import validate_selection

    if dry_run and output.resolve() == root.resolve():
        raise ValueError('dry-run output must be isolated from the formal workspace')
    selection, groups, news, gate = validate_selection(root, week, selection_file, issue_file, preview=dry_run)
    issue = IssueEditorial.model_validate(load_json(issue_file))
    if issue.week != week:
        raise ValueError("editorial issue week mismatch")
    start = date.fromisocalendar(int(week[:4]), int(week[6:]), 1)
    end = start + timedelta(days=6)
    audit = {**gate, 'confirmed_events': [c.event_ref.removeprefix('event:') for c in news.values()
                                        if c.verification == 'confirmed' and c.event_ref]}
    memory = [MajorEvent.model_validate(e) for e in load_json(root / 'runs' / week / 'major_event_snapshot.json')]
    all_selected = {row.id for rows in groups.values() for row in rows}
    selected_refs = {news[ident].event_ref for ident in all_selected}
    events = [(e, 'Weekly New' if e.last_updated >= start else
               'Open Discovery' if e.last_updated >= end - timedelta(days=13) else 'Recent Major')
              for e in memory if e.confirmed and 'event:' + e.id in selected_refs]
    excluded_refs = {news[row['id']].event_ref for row in selection.get('exclude', []) if row['id'] in news}
    # Every supporting claim is retained only if its event is also selected, not merely present in memory.
    for e, _ in events:
        candidate = news[e.id] if e.id in news else next(c for c in news.values() if c.event_ref == 'event:' + e.id)
        e.importance = candidate.proposed_tier
    context = IssueContext(events, load_items(root / "data/candidates" / (week + ".json")))
    context.timeline_refs = {news[row.id].event_ref for row in groups['recent_major']}
    context.industry_refs = selected_refs - excluded_refs
    story_map = {s.id: s for s in issue.stories}
    issue.stories = [story_map[row.story_id] for row in sorted(groups['top_stories'], key=lambda r: r.order)]
    issue.story_figures = {key: value for key, value in issue.story_figures.items() if key in {s.id for s in issue.stories}}
    briefing_refs = {news[row.id].event_ref for row in groups['briefing']}
    issue.quick_read = [s for s in issue.quick_read if set(s.refs).intersection(briefing_refs)]
    if not issue.quick_read:
        raise ValueError('selected briefing has no reviewed editorial copy')
    issue.event_briefs = {key: value for key, value in issue.event_briefs.items() if 'event:' + key in context.events}
    resources = config(root, "resources")["resources"]
    context.validate(issue, resources, config(root, "edition")["scenarios"])
    issue_digest = hashlib.sha256(issue_file.read_bytes()).hexdigest()
    candidates_digest = hashlib.sha256((root / 'data/candidates' / (week + '.json')).read_bytes()).hexdigest()
    copy_edit = copy_edit_provenance(root, week, issue_digest, candidates_digest, version=issue.schema_version)
    visuals = [*issue.story_figures.values(), *([issue.cover_figure] if issue.cover_figure else [])]
    visual_files = {filename: (root / "templates/figures" / filename).read_bytes()
                    for figure in visuals for filename in [figure.src, figure.mobile_src] if filename}
    if audit["week"] != week:
        raise ValueError("major news audit week mismatch")
    if not set(context.events).issubset({"event:" + i for i in audit["confirmed_events"]}):
        raise ValueError("memory contains events absent from this issue audit")
    template = (root / "templates/weekly.html").read_text(encoding="utf-8")
    paths = {"home": output / "site/index.html", "issue": output / "site/weekly" / week / "index.html",
             "draft": output / "drafts" / (week + ("-v04.md" if issue.schema_version == '0.4' else "-v03.md"))}
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    paths["home"].write_text(render_html(issue, context, resources, audit, template, "assets/"), encoding="utf-8")
    paths["issue"].write_text(render_html(issue, context, resources, audit, template, "../../assets/"), encoding="utf-8")
    md = render_markdown(issue, context, resources)
    paths["draft"].write_text(md, encoding="utf-8")
    if archive and not dry_run:
        target = output / "reports" / week[:4] / (week + ".md")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_markdown(issue, context, resources, "../../site/assets/"), encoding="utf-8")
        paths["archive"] = target
    assets = output / "site/assets"
    assets.mkdir(parents=True, exist_ok=True)
    for filename in ("weekly.css", "weekly.js"):
        (assets / filename).write_bytes((root / "templates" / filename).read_bytes())
    for filename, content in visual_files.items():
        (assets / filename).write_bytes(content)
    manifest = {"schema_version": issue.schema_version, "week": week, "run_time": utcnow().isoformat(), "dry_run": dry_run,
                "windows": {"weekly": [start.isoformat(), end.isoformat()],
                            "discovery": [(end - timedelta(days=13)).isoformat(), end.isoformat()],
                            "recent_major": [(end - timedelta(days=59 if issue.schema_version == '0.4' else 29)).isoformat(), end.isoformat()]},
                "major_events": len(events), "selected_papers": len(issue.paper_ids), "top_stories": len(issue.stories),
                "impact_scenarios": len(issue.impacts), "learning_concepts": len(issue.learning),
                "status": "selection_preview" if dry_run else "local_editorial_approved",
                "model_api_calls": 0, "model_api_calls_scope": "this_build",
                "inherited_copy_edit_api_calls": copy_edit['calls'] if copy_edit else 0,
                "monthly_comparison_baseline": "not_available_first_retrospective_issue",
                "paths": {name: str(path) for name, path in paths.items()},
                "editorial_sha256": issue_digest,
                "editorial_gate": {"audit_sha256": gate['audit_sha256'],
                                   "selection_sha256": hashlib.sha256((selection_file or root / 'runs' / week / 'editorial_selection.yaml').read_bytes()).hexdigest(),
                                   "review": selection['review'], "mode": 'preview' if dry_run else 'approved'},
                "visual_assets": [{"file": f.src, "credit": "观察站原创 SVG", "refs": f.refs,
                                   "sha256": hashlib.sha256(visual_files[f.src]).hexdigest(),
                                   "mobile_file": f.mobile_src,
                                   "mobile_sha256": hashlib.sha256(visual_files[f.mobile_src]).hexdigest()
                                   if f.mobile_src else None} for f in visuals],
                "event_windows": dict(Counter(band for _, band in events))}
    if copy_edit:
        manifest['copy_edit'] = copy_edit
    write_json(output / "runs" / (week + ("-v04.json" if issue.schema_version == '0.4' else "-v03.json")), manifest)
    return manifest
