from __future__ import annotations

import json
import logging
import re
import shutil
from collections import Counter
from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .dedup import deduplicate
from .http import HttpClient
from .llm import ModelClient
from .models import Analysis, Candidate, Evidence, Scores, utcnow
from .normalization import in_date_range, normalize
from .ranking import classify_rank, overall, select
from .report import render
from .research import deepen

logger = logging.getLogger(__name__)
PAPER_SOURCES = {"robotics_arxiv_daily", "huggingface_daily"}


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def config(root: Path, name: str):
    return yaml.safe_load((root / "config" / (name + ".yaml")).read_text(encoding="utf-8"))


def week_id(start: date) -> str:
    year, week, _ = start.isocalendar()
    return f"{year}-W{week:02d}"


def validate_week(week: str):
    if not re.fullmatch(r"\d{4}-W\d{2}", week):
        raise ValueError("week must be YYYY-WXX")
    date.fromisocalendar(int(week[:4]), int(week[6:]), 1)
    return week


def store_items(path: Path, items: list[Candidate]):
    write_json(path, [Candidate.model_validate(c.model_dump()).model_dump(mode="json") for c in items])


def load_items(path: Path) -> list[Candidate]:
    return [Candidate.model_validate(item) for item in load_json(path)]


def collect(root: Path, output: Path, start: date, end: date, client: HttpClient,
            supplement: Path | None = None, dry_run=False):
    from .collectors.feeds import collect_feed, collect_official, collect_releases
    from .collectors.papers import collect_hf, collect_robotics

    if start > end:
        raise ValueError("start must be <= end")
    if (end - start).days > 31:
        raise ValueError("V0.1 limits a run to 32 calendar days; split longer intervals")
    week = week_id(start)
    collectors = {"robotics_arxiv_daily": collect_robotics, "huggingface_daily": collect_hf,
                  "rss": collect_feed, "atom": collect_feed, "github_releases": collect_releases,
                  "official_html": collect_official}
    manifest = {"schema_version": "0.1", "week": week, "run_time": utcnow().isoformat(),
                "date_range": {"start": start.isoformat(), "end": end.isoformat()}, "dry_run": dry_run,
                "offline": client.offline, "sources_attempted": [], "sources_success": [],
                "sources_failed": [], "source_results": {}, "warnings": [], "status": "collecting",
                "model_usage": {"calls": 0, "cache_hits": 0, "input_tokens": 0, "output_tokens": 0,
                                "estimated_cost_usd": None}, "editorial_imports": 0}
    if start.isoweekday() != 1 or end.isoweekday() != 7 or (end - start).days != 6:
        manifest["warnings"].append("日期范围不是完整自然周；周标识按起始日 ISO 周命名")
    if client.offline:
        manifest["warnings"].append("离线缓存重放；不是重新查询来源的覆盖验证")
    raw = []
    for source in config(root, "sources")["sources"]:
        if not source.get("enabled", True):
            continue
        name = source["name"]
        manifest["sources_attempted"].append(name)
        logger.info("source start name=%s", name)
        try:
            if source["type"] not in collectors:
                raise ValueError("unsupported collector type")
            records = collectors[source["type"]](client, start, end, source)
            raw.extend(records)
            manifest["sources_success"].append(name)
            manifest["source_results"][name] = {"status": "success", "items": len(records),
                                                "url": source["url"], "category": source["category"],
                                                "notes": source.get("notes", ""),
                                                "collector_stats": source.get("_stats", {}),
                                                "warnings": source.get("_warnings", [])}
            manifest["warnings"].extend(f"{name}：{w}" for w in source.get("_warnings", []))
            if not records:
                manifest["warnings"].append(f"{name}：返回 0 条区间内信息，覆盖仍需人工检查")
            logger.info("source success name=%s items=%d", name, len(records))
        except Exception as exc:
            # Only sanitized domain/status strings or exception classes enter logs.
            from .http import SourceError

            error = str(exc) if isinstance(exc, SourceError) else type(exc).__name__
            manifest["sources_failed"].append(name)
            manifest["source_results"][name] = {"status": "failed", "error": error,
                                                "url": source["url"], "category": source["category"]}
            manifest["warnings"].append(f"{name}：采集失败（{error}）")
            logger.warning("source failed name=%s error=%s", name, error)
    if supplement:
        records = load_items(supplement)
        raw.extend(records)
        manifest["sources_attempted"].append("manual_primary_supplement")
        manifest["sources_success"].append("manual_primary_supplement")
        manifest["source_results"]["manual_primary_supplement"] = {
            "status": "manual_import", "items": len(records), "file": supplement.name}
    normalized = [normalize(c) for c in raw if in_date_range(c.published_at, start, end)]
    merged = deduplicate(normalized)
    ranked = classify_rank(merged, config(root, "scoring"), config(root, "watchlist"))
    manifest.update(raw_items=len(raw), normalized_items=len(normalized), deduplicated_items=len(merged),
                    candidate_items=sum(c.status == "candidate" for c in ranked),
                    watch_items=sum(c.status == "watch" for c in ranked), selected_items=0,
                    papers_selected=0, news_selected=0, education_selected=0, open_source_selected=0,
                    http_requests=client.requests, http_cache_hits=client.cache_hits, status="collected")
    filtered_count = len(raw) - len(normalized)
    if filtered_count:
        manifest["warnings"].append(f"{filtered_count} 条发现记录首次发表日期不在区间，已排除本周新增池")
    # Save exact public responses used by this run, without headers or secrets.
    write_json(output / "data" / "raw" / (week + "-responses.json"), list(client.accessed.values()))
    store_items(output / "data" / "raw" / (week + ".json"), raw)
    store_items(output / "data" / "normalized" / (week + ".json"), merged)
    store_items(output / "data" / "candidates" / (week + ".json"), ranked)
    write_json(output / "runs" / (week + ".json"), manifest)
    logger.info("items collected=%d filtered=%d deduplicated=%d", len(raw), filtered_count, len(merged))
    return manifest


class ReviewEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    analysis: Analysis | None = None
    scores: Scores | None = None
    relevant: bool = True
    tags: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def apply_reviews(items: list[Candidate], path: Path, scoring: dict) -> int:
    raw = load_json(path)
    entries = [ReviewEntry.model_validate(r) for r in raw]
    ids = {item.id: item for item in items}
    if len({e.id for e in entries}) != len(entries):
        raise ValueError("duplicate editorial review IDs")
    for entry in entries:
        if entry.id not in ids:
            raise ValueError("review references unknown candidate: " + entry.id)
        item = ids[entry.id]
        data = item.model_dump()
        data["evidence"] = [e.model_dump() for e in item.evidence + entry.evidence]
        if len({e["id"] for e in data["evidence"]}) != len(data["evidence"]):
            raise ValueError("duplicate evidence IDs in editorial import")
        if entry.analysis:
            if entry.analysis.origin == "api_model":
                raise ValueError("editorial imports must declare codex_review or human_review origin")
            data["analysis"] = entry.analysis.model_dump()
        if entry.scores:
            data.update(entry.scores.model_dump())
            data["scoring_method"] = "editorial_evidence_review"
        if entry.tags:
            data["tags"] = entry.tags
        data["notes"] += entry.notes
        validated = Candidate.model_validate(data)
        item.__dict__.update(validated.__dict__)
        item.overall_score = overall(item, scoring)
        item.status = "candidate" if entry.relevant and item.overall_score >= scoring["threshold"] else "excluded"
    return len(entries)


def quality_gate(items: list[Candidate], manifest: dict, scoring: dict):
    if not PAPER_SOURCES.intersection(manifest["sources_success"]):
        raise ValueError("all primary paper sources failed; see run manifest, draft blocked")
    relevant = [c for c in items if c.status in {"candidate", "selected", "analyzed"}]
    if len(relevant) < scoring["minimum_items"] or sum(c.source_type == "paper" for c in relevant) < scoring[
            "minimum_papers"]:
        raise ValueError("insufficient relevant data for a credible weekly; see run manifest")
    if not any(c.abstract or any(e.kind in {"paper_full_text", "paper_abstract"} for e in c.evidence)
               for c in relevant if c.source_type == "paper"):
        raise ValueError("paper evidence unavailable; title-only weekly is blocked")


def analyze(root: Path, output: Path, week: str, client: HttpClient, *, use_llm=False,
            reviews: Path | None = None, research=True):
    validate_week(week)
    manifest = load_json(output / "runs" / (week + ".json"))
    items = load_items(output / "data" / "candidates" / (week + ".json"))
    scoring = config(root, "scoring")
    model = ModelClient(root, output / ".cache" / "analysis", root / ".cache" / "analysis")
    if use_llm and (not model.key or not model.model):
        raise ValueError("--llm requires OPENAI_API_KEY and OPENAI_MODEL")
    if use_llm and client.offline:
        raise ValueError("--offline cannot make model API calls; use editorial import or omit --llm")
    if reviews:
        manifest["editorial_imports"] = apply_reviews(items, reviews, scoring)
        manifest["editorial_file"] = reviews.name
    if use_llm:
        for item in items:
            if item.status == "excluded" and not item.big_news:
                continue
            try:
                result = model.classify(item)
                updated = Candidate.model_validate({**item.model_dump(), **result.scores.model_dump(),
                                                    "source_type": result.source_type, "tags": result.tags,
                                                    "scoring_method": "api_model_evidence_review"})
                item.__dict__.update(updated.__dict__)
                item.overall_score = overall(item, scoring)
                item.status = "candidate" if result.relevant and item.overall_score >= scoring["threshold"] else (
                    "watch" if item.big_news else "excluded")
                item.notes.append(result.rationale)
            except Exception as exc:
                item.status = "watch"
                manifest["warnings"].append(f"{item.id}：模型分类失败（{type(exc).__name__}），保留待审")
    selected = select(items, scoring)
    for item in selected:
        if research and not item.analysis:
            deepen(item, client)
        if use_llm and not item.analysis:
            try:
                item.analysis = model.analyze(item)
                Candidate.model_validate(item.model_dump())
                item.status = "analyzed"
            except Exception as exc:
                item.analysis = None
                manifest["warnings"].append(f"{item.id}：解读失败（{type(exc).__name__}），不能视为深读")
    counts = Counter(c.source_type for c in selected)
    reviewed = sum(c.analysis is not None and c.analysis.fact_check == "pass" for c in selected)
    manifest.update(selected_items=len(selected), papers_selected=counts["paper"],
                    news_selected=counts["industry"] + counts["technology"],
                    education_selected=counts["education"] + counts["policy"],
                    open_source_selected=counts["open_source"], analyzed_items=reviewed,
                    model_usage=model.usage(), status="analyzed", analysis_time=utcnow().isoformat(),
                    big_news_review_queue=[c.id for c in items if c.big_news and c.status in {"watch", "excluded"}])
    manifest["candidate_items_after_analysis"] = sum(
        c.status in {"candidate", "selected", "analyzed"} for c in items)
    if reviewed < len(selected):
        manifest["warnings"].append(f"{len(selected) - reviewed} 个入选线索未完成事实审核解读；仅作待审线索")
    store_items(output / "data" / "candidates" / (week + ".json"), items)
    write_json(output / "runs" / (week + ".json"), manifest)
    logger.info("LLM calls=%d selected=%d analyzed=%d", model.calls, len(selected), reviewed)
    try:
        quality_gate(items, manifest, scoring)
    except ValueError:
        manifest["status"] = "blocked_insufficient_data"
        write_json(output / "runs" / (week + ".json"), manifest)
        raise
    return manifest


def report(root: Path, output: Path, week: str):
    validate_week(week)
    manifest = load_json(output / "runs" / (week + ".json"))
    items = load_items(output / "data" / "candidates" / (week + ".json"))
    scoring = config(root, "scoring")
    quality_gate(items, manifest, scoring)
    selected = sorted([c for c in items if c.status in {"selected", "analyzed"}],
                      key=lambda c: (-c.overall_score, c.id))
    if not selected:
        raise ValueError("run analyze before report")
    text = render(selected, items, manifest, config(root, "resources")["resources"])
    path = output / "drafts" / (week + ".md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    manifest["status"] = "draft_ready_for_review"
    manifest["draft_path"] = str(path)
    write_json(output / "runs" / (week + ".json"), manifest)
    logger.info("report generated path=%s", path)
    return manifest


def publish(root: Path, week: str, reviewed: bool):
    validate_week(week)
    if not reviewed:
        raise ValueError("publish requires --reviewed after reading draft and checking sources")
    from .edition import build_edition

    issue = root / 'data/editorial' / (week + '-v04.json')
    if not issue.exists():
        issue = root / 'data/editorial' / (week + '-v03.json')
    build_edition(root, root, week, issue, archive=True)
    return root / 'reports' / week[:4] / (week + '.md')


def clear_cache(root: Path):
    target = (root / ".cache").resolve()
    if target.parent != root.resolve() or target.name != ".cache" or target.is_symlink():
        raise ValueError("cache target must stay inside project root")
    if target.exists():
        shutil.rmtree(target)
