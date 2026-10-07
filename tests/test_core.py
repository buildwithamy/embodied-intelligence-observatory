from datetime import date, datetime

import pytest
from pydantic import ValidationError

from embodied_observatory.dedup import deduplicate
from embodied_observatory.models import Analysis, Candidate, Evidence
from embodied_observatory.normalization import (
    in_date_range,
    normalize_arxiv_id,
    normalize_title,
    normalize_url,
)
from embodied_observatory.pipeline import validate_week, week_id
from embodied_observatory.ranking import classify_rank, overall


def candidate(**kwargs):
    return Candidate(title="Robot manipulation", url="https://arxiv.org/abs/2609.12345",
                     published_at=date(2026, 9, 29), source_type="paper", sources=["source_a"], **kwargs)


@pytest.mark.parametrize("raw,expected", [
    ("https://arxiv.org/pdf/2609.12345v2.pdf", "2609.12345"), ("2609.1234v11", "2609.1234"),
    ("arXiv:cs/9901001v3", "cs/9901001"), ("not-a-paper", "")])
def test_arxiv(raw, expected):
    assert normalize_arxiv_id(raw) == expected


def test_url_title():
    assert normalize_url("http://www.arxiv.org/pdf/2609.12345v2.pdf?utm_source=x") == (
        "https://arxiv.org/abs/2609.12345")
    assert normalize_url("https://EXAMPLE.org/path/?utm_source=x&b=2&a=1#ref") == (
        "https://example.org/path?a=1&b=2")
    assert normalize_title("  Ｒobot:   Learning! ") == "robot learning"


def test_dates_and_week():
    start, end = date(2026, 9, 28), date(2026, 10, 4)
    assert in_date_range(start, start, end) and in_date_range(end, start, end)
    assert not in_date_range("2026-09-27T23:59:59Z", start, end)
    with pytest.raises(ValueError):
        in_date_range(start, end, start)
    assert week_id(start) == "2026-W40"
    with pytest.raises(ValueError):
        validate_week("../../something")


def test_schema():
    with pytest.raises(ValidationError):
        candidate(technical_score=6)
    with pytest.raises(ValidationError):
        candidate(retrieved_at=datetime(2026, 9, 29))
    original = candidate()
    assert Candidate.model_validate_json(original.model_dump_json()) == original


def test_dedup_sources_and_versions():
    left = candidate(arxiv_id="2609.12345v1", evidence=[Evidence(id="a", url="https://arxiv.org/abs/2609.12345",
                     source="source_a", kind="paper_abstract", text="A robot method.")])
    right = left.model_copy(update={"arxiv_id": "2609.12345v2", "sources": ["source_b"],
                                   "url": "https://huggingface.co/papers/2609.12345", "abstract": "Longer summary"})
    merged = deduplicate([left, right])
    assert len(merged) == 1
    assert set(merged[0].sources) == {"source_a", "source_b"}
    assert len(merged[0].source_urls) == 2
    assert merged[0].abstract == "Longer summary"
    assert merged[0].arxiv_id == "2609.12345"
    # Same title but different paper IDs are distinct scientific publications.
    other = right.model_copy(update={"arxiv_id": "2609.54321", "url": "https://arxiv.org/abs/2609.54321"})
    assert len(deduplicate([left, other])) == 2


def test_analysis_unknown_evidence():
    data = dict(chinese_title="机器人操作", research_question="问题", method="方法", main_results="作者报告",
                why_it_matters="观察", limitations="未验证", evidence_refs=["missing"],
                claim_refs={k: ["missing"] for k in ("research_question", "method", "main_results")},
                origin="human_review", read_depth="abstract")
    with pytest.raises(ValidationError):
        candidate(analysis=Analysis(**data))


def test_scores_and_watchlist():
    scoring = {"weights": {"technical_score": .3, "industry_score": .2, "education_score": .1,
                           "reproducibility_score": .15, "evidence_score": .25},
               "relevance_terms": ["robot"], "tag_terms": {"Manipulation": ["manipulation"]}, "threshold": 2.45}
    watchlist = {"always_review_categories": ["policy"], "event_terms": ["launch"],
                 "organizations": ["NVIDIA"], "education_major_terms": ["degree"]}
    rows = classify_rank([candidate()], scoring, watchlist)
    assert rows[0].overall_score == overall(rows[0], scoring)
    policy = candidate().model_copy(update={"source_type": "policy", "title": "Generic national policy"})
    assert classify_rank([policy], scoring, watchlist)[0].status == "watch"
    bad = {**scoring, "weights": {"evidence_score": 2}}
    with pytest.raises(ValueError):
        overall(candidate(), bad)
