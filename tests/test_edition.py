"""Meaningful editorial gates: historical evidence, memory retention, review and write isolation."""
import hashlib
import shutil
from datetime import date, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from embodied_observatory.cli import main
from embodied_observatory.edition import (
    EditorialFigure,
    IssueContext,
    IssueEditorial,
    MatrixRow,
    build_edition,
)
from embodied_observatory.major_events import (
    MajorEvent,
    audit_import,
    load_events,
    merge_memory,
    select_memory,
    window,
)
from embodied_observatory.pipeline import config, load_items, load_json, write_json

ROOT = Path(__file__).resolve().parents[1]
START, END = date(2026, 9, 28), date(2026, 10, 4)
# W40 editorial data quotes third-party articles in full; the public repository leaves it out.
requires_w40 = pytest.mark.skipif(
    not all((ROOT / p).exists() for p in ("data/editorial/2026-W40-v03.json", "data/major_events.json")),
    reason="W40 回放数据含第三方原文，未放入公开仓库",
)


def synthetic_event(event_date=START, importance="S", **updates):
    # This source and body are explicit fixtures, never used as public issue content.
    payload = dict(id="synthetic-test-event", title="Synthetic test event", event_date=event_date,
                   last_updated=event_date, first_seen="2026-10-06T01:00:00Z", importance=importance,
                   summary="Synthetic test statement", why_it_matters="Synthetic editorial relevance",
                   what_changed_since_last_issue="Test fixture only", categories=["industry"],
                   confirmed=True, sources=[dict(title="Fixture source", url="https://example.com/fixture",
                                                published_at=event_date, body="Explicit synthetic fixture evidence")])
    payload.update(updates)
    return MajorEvent.model_validate(payload)


@pytest.mark.parametrize("age,importance,reason,expected", [
    (0, "B", "", "Weekly New"), (6, "B", "", "Weekly New"), (7, "B", "", None),
    (29, "A", "", "Recent Major"), (30, "A", "", None),
    (44, "A", "still material with documented rationale", "Persistent Major"), (45, "A", "still material", None),
    (59, "S", "background to present deployments", "Persistent Major"), (60, "S", "still material", None),
])
def test_time_bands(age, importance, reason, expected):
    event = synthetic_event(END - timedelta(days=age), importance, continuation_reason=reason)
    assert window(event, START, END, config(ROOT, "edition")) == expected


def test_future_update_and_unconfirmed_cannot_enter_historical_issue():
    original = synthetic_event()
    future = dict(title="Future fixture update", url="https://example.com/future",
                  published_at=date(2026, 10, 5), body="Explicit future test fixture source")
    updated = MajorEvent.model_validate({**original.model_dump(), "last_updated": future["published_at"],
                                        "sources": [*original.model_dump()["sources"], future]})
    assert window(updated, START, END, config(ROOT, "edition")) is None
    assert window(original.model_copy(update={"confirmed": False}), START, END, config(ROOT, "edition")) is None
    with pytest.raises(ValidationError, match="dated primary sources"):
        MajorEvent.model_validate({**original.model_dump(), "last_updated": "2026-10-03"})


def test_memory_keeps_first_seen_and_original_evidence():
    original = synthetic_event()
    latest = synthetic_event(first_seen="2026-10-07T01:00:00Z")
    assert merge_memory([original], [latest])[0].first_seen == original.first_seen
    with pytest.raises(ValueError, match="duplicate event ID"):
        merge_memory([], [original, original])
    with pytest.raises(ValueError, match="regressed"):
        merge_memory([original], [synthetic_event(START - timedelta(days=1))])


@requires_w40
def test_unreviewed_references_and_fake_matrix_scores_rejected():
    issue = IssueEditorial.model_validate(load_json(ROOT / "data/editorial/2026-W40-v03.json"))
    issue.signals[0].refs = ["event:unconfirmed-fixture"]
    with pytest.raises(ValueError, match="unreviewed"):
        IssueContext([], []).validate(issue, config(ROOT, "resources")["resources"], config(ROOT, "edition")["scenarios"])
    with pytest.raises(ValidationError, match="qualitative"):
        MatrixRow(technology="Fixture", refs=["paper:test"], relations={"industry": "8.5"}, rationale="Fixture")


@requires_w40
def test_figure_source_paths_and_evidence_cannot_escape_the_story():
    with pytest.raises(ValidationError):
        EditorialFigure(src="../outside.svg", alt="Fixture", caption="Fixture", refs=["paper:test"])
    issue = IssueEditorial.model_validate(load_json(ROOT / "data/editorial/2026-W40-v03.json"))
    issue.story_figures['homes'].refs = ['paper:2609.38087']
    context = IssueContext(select_memory(load_events(ROOT / "data/major_events.json"), START, END,
                                        config(ROOT, "edition")),
                           load_items(ROOT / "data/candidates/2026-W40.json"))
    with pytest.raises(ValueError, match="own story evidence"):
        context.validate(issue, config(ROOT, "resources")["resources"], config(ROOT, "edition")["scenarios"])


def test_audit_archives_expired_events_and_records_missing_collector_review(tmp_path):
    shutil.copytree(ROOT / "config", tmp_path / "config")
    events = tmp_path / "fixtures.json"
    fixture = synthetic_event(END - timedelta(days=10), "B")
    write_json(events, [fixture.model_dump(mode="json"), synthetic_event().model_dump(mode="json") | {"id": "second-fixture"}])
    audit_source = tmp_path / "fixture-audit.json"
    write_json(audit_source, {"source": "synthetic offline checks only"})
    result = audit_import(tmp_path, tmp_path, "2026-W40", [events], [audit_source])
    assert result["confirmed_events"] == ["second-fixture"]
    assert result["manual_review_queue"][0]["id"] == result["manual_review_outcomes"][0]["id"]
    assert any(e.status == "archived" for e in load_events(tmp_path / "data/major_events.json"))
    assert result["event_snapshot"][0]["sources"][0]["body"]


def test_local_rebuild_and_dry_run_preserve_formal_outputs(editorial_workspace, monkeypatch):
    from embodied_observatory.editorial_gate import approve_selection

    tmp_path = editorial_workspace
    # Offline replay of the checked-in real issue; no fixture is published as news.
    issue_file = tmp_path / 'data/editorial/2026-W40-v04.json'
    approve_selection(tmp_path, '2026-W40', tmp_path / 'runs/2026-W40/editorial_selection.yaml',
                      issue_file, 'synthetic_test_reviewer', True)
    result = build_edition(tmp_path, tmp_path, "2026-W40", issue_file, archive=True)
    active = [e for e in load_json(tmp_path/'runs/2026-W40/major_event_snapshot.json') if e['status'] != 'archived']
    assert result["major_events"] == len(active) and result["selected_papers"] == 6
    assert result["windows"]["recent_major"] == ["2026-08-06", "2026-10-04"]
    assert not (tmp_path / "latest.md").exists()
    assert len(result['visual_assets']) == 1
    for visual in result['visual_assets']:
        assert hashlib.sha256((tmp_path / 'site/assets' / visual['file']).read_bytes()).hexdigest() == visual['sha256']
        if visual['mobile_file']:
            assert hashlib.sha256((tmp_path / 'site/assets' / visual['mobile_file']).read_bytes()).hexdigest() == visual['mobile_sha256']
    archive = (tmp_path / 'reports/2026/2026-W40.md').read_text(encoding='utf-8')
    assert 'AMD 拟收购 World Labs' in archive
    home = (tmp_path / "site/index.html").read_text(encoding="utf-8")
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(home, "html.parser")
    for details in soup.find_all("details"):
        details.decompose()
    main_text = soup.get_text()
    assert "body-" not in main_text and "full_text" not in main_text and "confidence" not in main_text
    assert "{{" not in home
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.rglob("*") if p.is_file()}
    dry = tmp_path.parent / (tmp_path.name + "-dry")
    monkeypatch.setattr("embodied_observatory.cli.tempfile.mkdtemp", lambda **kwargs: str(dry))
    assert main(["--root", str(tmp_path), "edition", "--week", "2026-W40", "--issue-file",
                 str(issue_file), "--archive", "--dry-run"]) == 0
    after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after
    assert (dry / "site/index.html").exists() and not (dry / "reports").exists()
    assert main(["--root", str(tmp_path), "major-audit", "--week", "2026-W40", "--events",
                 str(ROOT / "data/editorial/v03_industry_events.json"),
                 str(ROOT / "data/editorial/v03_tech_education_events.json"), "--audits",
                 str(ROOT / "data/research/v03_industry_audit.json"),
                 str(ROOT / "data/research/v03_tech_education_audit.json"), "--dry-run"]) == 0
    assert before == {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in tmp_path.rglob("*") if p.is_file()}
    assert (dry / "data/major_events.json").exists()
    assert load_items(tmp_path / "data/candidates/2026-W40.json")
