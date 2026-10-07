import hashlib
import re
import unicodedata
from datetime import date, datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import Candidate


def normalize_arxiv_id(value: str) -> str:
    match = re.search(r"(?<!\d)(\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?", value, re.I)
    return match.group(1).lower() if match else ""


def normalize_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    host = parsed.netloc.lower()
    if host in {"www.arxiv.org", "export.arxiv.org", "arxiv.org"}:
        aid = normalize_arxiv_id(parsed.path)
        if aid:
            return "https://arxiv.org/abs/" + aid
    query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}]
    return urlunsplit((parsed.scheme.lower(), host, parsed.path.rstrip("/"), urlencode(sorted(query)), ""))


def normalize_title(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.sub(r"[^\w\s]", " ", value).split())


def in_date_range(value: date | datetime | str, start: date, end: date) -> bool:
    if start > end:
        raise ValueError("start must be <= end")
    if isinstance(value, str):
        value = date.fromisoformat(value[:10])
    if isinstance(value, datetime):
        value = value.date()
    return start <= value <= end


def normalize(candidate: Candidate) -> Candidate:
    data = candidate.model_dump()
    data["arxiv_id"] = normalize_arxiv_id(candidate.arxiv_id or candidate.url)
    data["canonical_url"] = normalize_url(candidate.canonical_url or candidate.url)
    data["title"] = " ".join(candidate.title.split())
    data["sources"] = sorted(set(candidate.sources))
    data["source_urls"] = sorted(set(candidate.source_urls + [candidate.url]))
    key = data["arxiv_id"] or candidate.doi.lower() or data["canonical_url"] or normalize_title(candidate.title)
    data["id"] = "eio-" + hashlib.sha256(key.encode()).hexdigest()[:16]
    return Candidate.model_validate(data)
