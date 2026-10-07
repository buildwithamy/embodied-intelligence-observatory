"""Human-reviewed event memory, historical cutoffs, independent news audit."""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from datetime import date as CalendarDate
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import http_url, utcnow
from .pipeline import config, load_json, validate_week, write_json


class PrimarySource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1)
    url: str
    published_at: CalendarDate
    body: str = Field(min_length=20)
    retrieved_at: datetime = Field(default_factory=utcnow)
    date: str | None = None  # Accept source export with a redundant human-readable date.

    _url = field_validator("url")(http_url)


class MajorEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,100}$")
    title: str = Field(min_length=1)
    event_date: date
    first_seen: datetime = Field(default_factory=utcnow)
    last_updated: date
    importance: Literal["S", "A", "B"]
    status: Literal["new", "developing", "stable", "resolved", "archived"] = "new"
    summary: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)
    what_changed_since_last_issue: str = Field(min_length=1)
    categories: list[str] = Field(min_length=1)
    application_scenarios: list[str] = Field(default_factory=list)
    education_implications: list[str] = Field(default_factory=list)
    research_implications: list[str] = Field(default_factory=list)
    sources: list[PrimarySource] = Field(min_length=1)
    constraints: list[str] = Field(default_factory=list)
    confirmed: bool = False
    continuation_reason: str = ""

    @model_validator(mode="after")
    def dates_supported(self):
        if self.last_updated < self.event_date:
            raise ValueError("last_updated must not precede event date")
        source_dates = {s.published_at for s in self.sources}
        if self.event_date not in source_dates or self.last_updated not in source_dates:
            raise ValueError("event/update dates require dated primary sources")
        if self.first_seen.tzinfo is None:
            raise ValueError("first_seen requires timezone")
        return self


def window(event: MajorEvent, start: date, end: date, settings: dict) -> str | None:
    if not event.confirmed or event.status == "archived" or event.event_date > end:
        return None
    # Future sources cannot leak into an earlier issue through a long-lived memory.
    if event.last_updated > end or any(s.published_at > end for s in event.sources):
        return None
    age = (end - event.event_date).days
    if event.event_date >= start:
        return "Weekly New"
    if age < settings["windows"]["recent_days"] and event.importance in {"S", "A"}:
        return "Recent Major"
    if (age < settings["retention_days"][event.importance] and event.importance in {"S", "A"}
            and event.continuation_reason):
        return "Persistent Major"
    return None


def load_events(path: Path) -> list[MajorEvent]:
    return [MajorEvent.model_validate(item) for item in load_json(path)] if path.exists() else []


def merge_memory(existing: list[MajorEvent], incoming: list[MajorEvent]) -> list[MajorEvent]:
    merged = {e.id: e for e in existing}
    seen = set()
    for event in incoming:
        if event.id in seen:
            raise ValueError("duplicate event ID in import: " + event.id)
        seen.add(event.id)
        previous = merged.get(event.id)
        if previous:
            if previous.event_date != event.event_date or event.last_updated < previous.last_updated:
                raise ValueError("event identity or factual update date regressed: " + event.id)
            event = event.model_copy(update={"first_seen": previous.first_seen})
            # Reimports never silently discard the original evidence snapshots.
            sources = {s.url: s for s in previous.sources}
            sources.update({s.url: s for s in event.sources})
            event = MajorEvent.model_validate({**event.model_dump(), "sources": list(sources.values())})
        merged[event.id] = event
    return sorted(merged.values(), key=lambda e: (e.event_date, e.id))


def select_memory(events: list[MajorEvent], start: date, end: date, settings: dict):
    return [(event, band) for event in events if (band := window(event, start, end, settings))]


def audit_import(root: Path, output: Path, week: str, event_files: list[Path], audit_files: list[Path]):
    validate_week(week)
    from datetime import date as calendar_date

    start = calendar_date.fromisocalendar(int(week[:4]), int(week[6:]), 1)
    end = start + timedelta(days=6)
    incoming = [event for path in event_files for event in load_events(path)]
    events = merge_memory(load_events(root / "data/major_events.json"), incoming)
    settings = config(root, "edition")
    selected = select_memory(events, start, end, settings)
    decisions = []
    for event in events:
        band = window(event, start, end, settings)
        historical = event.last_updated <= end and all(s.published_at <= end for s in event.sources)
        if band:
            decisions.append({"id": event.id, "action": "continue", "window": band,
                              "reason": event.continuation_reason or "within editorial time window"})
        elif historical and event.confirmed and event.status != "archived":
            event.status = "archived"
            decisions.append({"id": event.id, "action": "archive", "reason": "retention expired or no continuation rationale"})
        else:
            decisions.append({"id": event.id, "action": "exclude", "reason": "unconfirmed, archived or after cutoff"})
    snapshot = [load_json(path) for path in audit_files]
    current_source_urls = {s.url for e, _ in selected for s in e.sources}
    ordinary = set()
    old_candidates = root / "data/candidates" / (week + ".json")
    if old_candidates.exists():
        for candidate in load_json(old_candidates):
            ordinary.update(candidate.get("source_urls", []) + [candidate["url"]])
    domain_aliases = {"industry": "companies", "technology": "product"}
    covered = set()
    for e, _ in selected:
        covered.update(domain_aliases.get(category, category) for category in e.categories)
    # Evidence of an attempted audit belongs in explicit audit exports, not inferred search coverage.
    audit = {
        "week": week, "run_time": utcnow().isoformat(), "mode": "manual_primary_source_audit",
        "date_range": {"start": (end - timedelta(days=29)).isoformat(), "end": end.isoformat()},
        "domains_required": settings["audit_domains"], "event_domains_with_confirmed_results": sorted(covered),
        "domains_without_confirmed_event": [d for d in settings["audit_domains"] if d not in covered],
        "audit_records": snapshot,
        "confirmed_events": [e.id for e, _ in selected],
        "event_snapshot": [e.model_dump(mode="json") for e, _ in selected],
        "memory_decisions": decisions,
        "manual_review_queue": [{"id": e.id, "reason": "not collected by ordinary weekly sources"}
                                for e, _ in selected if not {s.url for s in e.sources}.intersection(ordinary)],
        "manual_review_outcomes": [{"id": e.id, "decision": "confirmed_primary_source_review"}
                                   for e, _ in selected if not {s.url for s in e.sources}.intersection(ordinary)],
        "unconfirmed_review_queue": [e.id for e in incoming if not e.confirmed],
        "excluded_by_time_or_retention": [e.id for e in incoming if not window(e, start, end, settings)],
        "primary_source_count": len(current_source_urls),
        "audit_input_hashes": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in audit_files},
        "limits": ["人工独立审计，不承诺全网覆盖。无已确认事件不等于该领域无进展。",
                   "事实来自原文；重要性、应用与教育启示为编辑判断。未建立上一期/月度完整基线。"],
    }
    write_json(output / "data/major_events.json", [e.model_dump(mode="json") for e in events])
    write_json(output / "runs" / (week + "-major-news-audit.json"), audit)
    return audit
