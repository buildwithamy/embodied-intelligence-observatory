import json
from datetime import date
from pathlib import Path

import pytest

from embodied_observatory.cli import main
from embodied_observatory.models import Candidate, Evidence
from embodied_observatory.pipeline import analyze, collect, load_json, publish, report, write_json

ROOT = Path(__file__).resolve().parents[1]


class FakeHttp:
    offline = False
    requests = cache_hits = 0
    accessed = {}


def fixtures():
    # Explicitly synthetic test fixtures. No live request or real-run claim.
    return [Candidate(title=f"Robot learning synthetic fixture {i}",
                      url=f"https://arxiv.org/abs/2609.9000{i}", arxiv_id=f"2609.9000{i}",
                      published_at=date(2026, 9, 29), source_type="paper", sources=["robotics_arxiv_daily"],
                      abstract="Robot learning with reproducible policy training.", github_url="https://github.com/test/test",
                      evidence=[Evidence(id=f"test-{i}", url=f"https://arxiv.org/abs/2609.9000{i}",
                                         source="arxiv", kind="paper_abstract", text="Robot policy test evidence.")])
            for i in range(3)]


def fake_source(monkeypatch, fail=False):
    from embodied_observatory.collectors import feeds, papers

    monkeypatch.setattr('embodied_observatory.discovery.search_rss', lambda *a: [])
    def get(*args):
        if fail:
            raise RuntimeError("test failure")
        return fixtures()
    monkeypatch.setattr(papers, "collect_robotics", get)
    monkeypatch.setattr(papers, "collect_hf", get)
    for method in ("collect_feed", "collect_releases", "collect_official"):
        monkeypatch.setattr(feeds, method, lambda *a: [])


def test_integration_and_publish_gate(tmp_path, monkeypatch):
    fake_source(monkeypatch)
    manifest = collect(ROOT, tmp_path, date(2026, 9, 28), date(2026, 10, 4), FakeHttp())
    assert manifest["raw_items"] == 6 and manifest["deduplicated_items"] == 3
    analyze(ROOT, tmp_path, "2026-W40", FakeHttp(), research=False)
    report(ROOT, tmp_path, "2026-W40")
    draft = (tmp_path / "drafts/2026-W40.md").read_text(encoding="utf-8")
    assert "05｜教育与人才培养" in draft and "未完成证据解读" in draft
    assert not (tmp_path / "latest.md").exists()
    with pytest.raises(ValueError):
        publish(tmp_path, "2026-W40", False)


def test_all_paper_sources_fail_blocks_draft(tmp_path, monkeypatch):
    fake_source(monkeypatch, fail=True)
    collect(ROOT, tmp_path, date(2026, 9, 28), date(2026, 10, 4), FakeHttp())
    with pytest.raises(ValueError, match="all primary paper sources failed"):
        analyze(ROOT, tmp_path, "2026-W40", FakeHttp(), research=False)
    assert load_json(tmp_path / "runs/2026-W40.json")["status"] == "blocked_insufficient_data"
    assert not (tmp_path / "drafts/2026-W40.md").exists()


def test_dry_run_does_not_touch_root(tmp_path, monkeypatch, capsys):
    import shutil

    fake_source(monkeypatch)
    shutil.copytree(ROOT / "config", tmp_path / "config")
    shutil.copytree(ROOT / "prompts", tmp_path / "prompts")
    (tmp_path / "latest.md").write_text("sentinel", encoding="utf-8")
    assert main(["--root", str(tmp_path), "weekly", "--start", "2026-09-28", "--end", "2026-10-04",
                 "--dry-run", "--skip-research"]) == 0
    assert (tmp_path / "latest.md").read_text(encoding="utf-8") == "sentinel"
    assert not (tmp_path / "drafts").exists() and not (tmp_path / "runs").exists()
    result = json.loads(capsys.readouterr().out)
    assert result["dry_run"] and Path(result["output"]).exists()


def test_analysis_import_requires_existing_evidence(tmp_path, monkeypatch):
    fake_source(monkeypatch)
    collect(ROOT, tmp_path, date(2026, 9, 28), date(2026, 10, 4), FakeHttp())
    review = tmp_path / "bad-review.json"
    write_json(review, [{"id": "unknown", "relevant": False}])
    with pytest.raises(ValueError, match="unknown candidate"):
        analyze(ROOT, tmp_path, "2026-W40", FakeHttp(), reviews=review, research=False)
