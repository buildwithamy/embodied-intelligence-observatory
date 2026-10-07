import hashlib
import json
import logging
import os
from pathlib import Path

import httpx
from pydantic import BaseModel, ConfigDict, Field

from .models import Analysis, Candidate, Scores

logger = logging.getLogger(__name__)


class Classification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    relevant: bool
    source_type: str
    tags: list[str]
    rationale: str
    scores: Scores


class FactCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdict: str = Field(pattern="^(pass|needs_review|fail)$")
    notes: list[str]


class ModelClient:
    def __init__(self, root: Path, cache: Path, read_cache: Path | None = None):
        self.root, self.cache, self.read_cache = root, cache, read_cache or cache
        self.key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("OPENAI_MODEL", "")
        self.endpoint = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.calls = self.cache_hits = self.input_tokens = self.output_tokens = 0

    def run(self, prompt_name: str, payload: dict, schema: type[BaseModel]):
        prompt = (self.root / "prompts" / (prompt_name + ".md")).read_text(encoding="utf-8")
        body = {"model": self.model, "messages": [
            {"role": "system", "content": prompt + "\nReturn JSON matching this schema:\n" +
             json.dumps(schema.model_json_schema(), ensure_ascii=False)},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
            "response_format": {"type": "json_object"}}
        key = hashlib.sha256(json.dumps({"endpoint": self.endpoint, "body": body},
                                        sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        path = self.read_cache / (key + ".json")
        if path.exists():
            self.cache_hits += 1
            return schema.model_validate_json(path.read_text(encoding="utf-8"))
        if not self.key or not self.model:
            raise ValueError("--llm requires OPENAI_API_KEY and OPENAI_MODEL")
        self.calls += 1
        # Deliberately no automatic model retry: avoid unpredictable duplicate billing.
        try:
            response = httpx.post(self.endpoint + "/chat/completions", json=body,
                                  headers={"Authorization": "Bearer " + self.key}, timeout=90)
            response.raise_for_status()
            data = response.json()
            usage = data.get("usage", {})
            self.input_tokens += usage.get("prompt_tokens", 0)
            self.output_tokens += usage.get("completion_tokens", 0)
            validated = schema.model_validate_json(data["choices"][0]["message"]["content"])
        except Exception as exc:
            raise RuntimeError("model request or schema failed: " + type(exc).__name__) from None
        self.cache.mkdir(parents=True, exist_ok=True)
        (self.cache / (key + ".json")).write_text(validated.model_dump_json(indent=2), encoding="utf-8")
        return validated

    def classify(self, candidate: Candidate) -> Classification:
        return self.run("classify", evidence_payload(candidate), Classification)

    def analyze(self, candidate: Candidate) -> Analysis:
        kind = "paper" if candidate.source_type == "paper" else (
            "education" if candidate.source_type in {"education", "policy"} else (
                "industry" if candidate.source_type == "industry" else "technology"))
        analysis = self.run(kind + "_analysis", evidence_payload(candidate), Analysis)
        # Trusted wrapper sets origin, the model cannot mislabel itself as a human review.
        analysis.origin = "api_model"
        analysis.fact_check = "needs_review"
        validated = Candidate.model_validate({**candidate.model_dump(), "analysis": analysis.model_dump()})
        check = self.run("fact_check", {"evidence": evidence_payload(candidate),
                                       "analysis": validated.analysis.model_dump()}, FactCheck)
        analysis.fact_check, analysis.fact_check_notes = check.verdict, check.notes
        return analysis

    def usage(self):
        return {"calls": self.calls, "cache_hits": self.cache_hits, "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens, "estimated_cost_usd": None,
                "cost_note": "模型费率随供应商及模型变化；以账单为准，未配置费率不猜测成本"}


def evidence_payload(candidate: Candidate) -> dict:
    evidence = sorted(candidate.evidence, key=lambda e: e.kind != "paper_full_text")
    return {"id": candidate.id, "title": candidate.title, "source_type": candidate.source_type,
            "published_at": candidate.published_at.isoformat(), "authors": candidate.authors,
            "evidence": [{"id": e.id, "url": e.url, "source": e.source, "kind": e.kind,
                          "text": e.text[:30000]} for e in evidence]}
