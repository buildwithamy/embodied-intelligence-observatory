from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def http_url(value: str) -> str:
    from urllib.parse import urlsplit

    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("A public HTTP(S) URL without credentials is required")
    return value


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    url: str
    source: str = Field(min_length=1)
    kind: str = "official_statement"
    text: str = Field(min_length=1)
    retrieved_at: datetime = Field(default_factory=utcnow)

    _url = field_validator("url")(http_url)


class Scores(BaseModel):
    model_config = ConfigDict(extra="forbid")
    technical_score: float = Field(default=0, ge=0, le=5)
    industry_score: float = Field(default=0, ge=0, le=5)
    education_score: float = Field(default=0, ge=0, le=5)
    reproducibility_score: float = Field(default=0, ge=0, le=5)
    evidence_score: float = Field(default=0, ge=0, le=5)


class Analysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chinese_title: str = Field(min_length=1)
    research_question: str = Field(min_length=1)
    method: str = Field(min_length=1)
    main_results: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)
    limitations: str = Field(min_length=1)
    confidence: Literal["low", "medium", "high"] = "low"
    evidence_refs: list[str] = Field(min_length=1)
    # Field-level provenance separates source-backed claims from editorial comments.
    claim_refs: dict[str, list[str]]
    fact_check: Literal["pass", "needs_review", "fail"] = "needs_review"
    fact_check_notes: list[str] = Field(default_factory=list)
    origin: Literal["api_model", "codex_review", "human_review"]
    read_depth: Literal["abstract", "full_text", "official_body"]

    @model_validator(mode="after")
    def claims_have_evidence(self):
        for field in ("research_question", "method", "main_results"):
            refs = self.claim_refs.get(field, [])
            if not refs or not set(refs).issubset(self.evidence_refs):
                raise ValueError(f"Missing evidence for {field}")
        return self


class Candidate(Scores):
    model_config = ConfigDict(extra="forbid")
    id: str = ""
    title: str = Field(min_length=1)
    url: str
    canonical_url: str = ""
    published_at: date
    retrieved_at: datetime = Field(default_factory=utcnow)
    source_type: Literal["paper", "industry", "technology", "open_source", "education", "policy"]
    sources: list[str] = Field(min_length=1)
    source_urls: list[str] = Field(default_factory=list)
    authors: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    arxiv_id: str = ""
    doi: str = ""
    github_url: str = ""
    project_url: str = ""
    abstract: str = ""
    raw_summary: str = ""
    analysis: Analysis | None = None
    overall_score: float = Field(default=0, ge=0, le=5)
    status: Literal["collected", "excluded", "candidate", "watch", "selected", "analyzed"] = "collected"
    evidence: list[Evidence] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    community_popularity: int = Field(default=0, ge=0)
    discovery_dates: list[date] = Field(default_factory=list)
    big_news: bool = False
    scoring_method: str = "unscored"

    _url = field_validator("url")(http_url)

    @field_validator("canonical_url", "github_url", "project_url")
    @classmethod
    def optional_url(cls, value):
        return http_url(value) if value else value

    @field_validator("retrieved_at")
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None:
            raise ValueError("retrieved_at requires timezone")
        return value

    @model_validator(mode="after")
    def validate_analysis(self):
        if self.analysis and not set(self.analysis.evidence_refs).issubset({e.id for e in self.evidence}):
            raise ValueError("Analysis references unknown evidence")
        if self.analysis:
            kinds = {e.kind for e in self.evidence if e.id in self.analysis.evidence_refs}
            if self.analysis.read_depth == "full_text" and "paper_full_text" not in kinds:
                raise ValueError("full_text analysis requires original full-text evidence")
            if self.analysis.read_depth == "official_body" and "official_body" not in kinds:
                raise ValueError("official_body analysis requires original body evidence")
        return self
