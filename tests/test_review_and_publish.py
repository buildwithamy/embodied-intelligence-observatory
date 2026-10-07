import json
import shutil
from datetime import date, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from embodied_observatory.http import HttpClient
from embodied_observatory.llm import ModelClient, evidence_payload
from embodied_observatory.models import Analysis, Candidate, Evidence
from embodied_observatory.pipeline import analyze, collect, load_items, publish, report, write_json

ROOT = Path(__file__).resolve().parents[1]


def make_paper(index):
    return Candidate(title=f"Robot fixture {index}", url=f"https://arxiv.org/abs/2609.8000{index}",
                     arxiv_id=f"2609.8000{index}", published_at=date(2026, 9, 29),
                     source_type="paper", sources=["robotics_arxiv_daily"],
                     abstract="Synthetic robot learning evidence", github_url="https://github.com/example/test",
                     evidence=[Evidence(id=f"a{index}", url=f"https://arxiv.org/abs/2609.8000{index}",
                                        source="test", text="Synthetic robot learning evidence", kind="paper_abstract")])


def analysis(eid, depth="abstract"):
    return Analysis(chinese_title="测试", research_question="问题", method="方法", main_results="作者报告",
                    why_it_matters="编辑判断", limitations="尚待验证", origin="human_review", read_depth=depth,
                    fact_check="pass", evidence_refs=[eid],
                    claim_refs={k: [eid] for k in ("research_question", "method", "main_results")})


def test_read_depth_requires_real_body():
    item = make_paper(0)
    data = {**item.model_dump(), "analysis": analysis("a0", "full_text").model_dump()}
    with pytest.raises(ValidationError, match="full-text evidence"):
        Candidate.model_validate(data)


def test_model_cache_payload_stable_across_retrieval_times():
    left, right = make_paper(0), make_paper(0)
    right.retrieved_at = left.retrieved_at + timedelta(days=1)
    right.evidence[0].retrieved_at = left.evidence[0].retrieved_at + timedelta(days=1)
    assert left.retrieved_at != right.retrieved_at
    assert evidence_payload(left) == evidence_payload(right)


def test_model_schema_cache_no_request(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")

    def post(url, **kwargs):
        import httpx

        return httpx.Response(200, json={"choices": [{"message": {"content": analysis("a0").model_dump_json()}}],
                                         "usage": {"prompt_tokens": 10, "completion_tokens": 20}},
                              request=httpx.Request("POST", url))
    monkeypatch.setattr("httpx.post", post)
    client = ModelClient(ROOT, tmp_path)
    client.run("paper_analysis", {"id": "a"}, Analysis)
    client.run("paper_analysis", {"id": "a"}, Analysis)
    assert client.calls == 1 and client.cache_hits == 1
    assert client.input_tokens == 10 and client.output_tokens == 20
    assert "test-secret" not in next(tmp_path.glob("*.json")).read_text(encoding="utf-8")


def test_reviewed_publish_in_temp_workspace(tmp_path, monkeypatch):
    from embodied_observatory.collectors import feeds, papers

    shutil.copytree(ROOT / "config", tmp_path / "config")
    shutil.copytree(ROOT / "prompts", tmp_path / "prompts")
    monkeypatch.setattr(papers, "collect_robotics", lambda *a: [make_paper(i) for i in range(3)])
    monkeypatch.setattr(papers, "collect_hf", lambda *a: [])
    for name in ("collect_feed", "collect_official", "collect_releases"):
        monkeypatch.setattr(feeds, name, lambda *a: [])
    client = HttpClient(tmp_path / ".cache/http", offline=True)
    collect(tmp_path, tmp_path, date(2026, 9, 28), date(2026, 10, 4), client)
    items = load_items(tmp_path / "data/candidates/2026-W40.json")
    reviews = tmp_path / "reviews.json"
    write_json(reviews, [{"id": c.id, "analysis": analysis(c.evidence[0].id).model_dump()} for c in items])
    analyze(tmp_path, tmp_path, "2026-W40", client, reviews=reviews, research=False)
    report(tmp_path, tmp_path, "2026-W40")
    # The old reviewed flag alone cannot bypass V0.4 discovery, audit and selection.
    with pytest.raises(FileNotFoundError, match='editorial_selection'):
        publish(tmp_path, "2026-W40", True)
    assert not (tmp_path / 'reports').exists() and not (tmp_path / 'latest.md').exists()
    manifest = json.loads((tmp_path / "runs/2026-W40.json").read_text(encoding="utf-8"))
    assert manifest["model_usage"]["calls"] == 0 and manifest["editorial_imports"] == 3
