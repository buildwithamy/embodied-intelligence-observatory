from .models import Candidate
from .normalization import normalize, normalize_title


def merge(left: Candidate, right: Candidate) -> Candidate:
    data = left.model_dump()
    for field in ("sources", "source_urls", "authors", "organizations", "tags", "categories", "notes",
                  "discovery_dates"):
        data[field] = list(dict.fromkeys(getattr(left, field) + getattr(right, field)))
    by_id = {e.id: e for e in left.evidence}
    for evidence in right.evidence:
        if evidence.id in by_id and evidence != by_id[evidence.id]:
            evidence = evidence.model_copy(update={"id": evidence.id + "-" + right.sources[0]})
        by_id[evidence.id] = evidence
    data["evidence"] = [e.model_dump() for e in by_id.values()]
    for field in ("abstract", "raw_summary"):
        if len(getattr(right, field)) > len(getattr(left, field)):
            data[field] = getattr(right, field)
    for field in ("arxiv_id", "doi", "github_url", "project_url"):
        data[field] = getattr(left, field) or getattr(right, field)
    data["published_at"] = min(left.published_at, right.published_at)
    data["community_popularity"] = max(left.community_popularity, right.community_popularity)
    return normalize(Candidate.model_validate(data))


def deduplicate(items: list[Candidate]) -> list[Candidate]:
    # Alias index handles a DOI-only record later enriched with arXiv metadata.
    groups: dict[int, Candidate] = {}
    aliases: dict[str, int] = {}
    for item in items:
        item = normalize(item)
        keys = ["url:" + item.canonical_url]
        if item.arxiv_id:
            keys.append("arxiv:" + item.arxiv_id)
        if item.doi:
            keys.append("doi:" + item.doi.lower().removeprefix("https://doi.org/"))
        # Different arXiv IDs must never merge on title alone.
        if not item.arxiv_id and not item.doi:
            day = "" if item.source_type == "paper" else item.published_at.isoformat() + ":"
            keys.append(item.source_type + ":title:" + day + normalize_title(item.title))
        matches = {aliases[k] for k in keys if k in aliases}
        group = min(matches) if matches else len(items) + len(aliases)
        combined = item
        for old in sorted(matches):
            combined = merge(groups.pop(old), combined)
        groups[group] = combined
        for alias, old in list(aliases.items()):
            if old in matches:
                aliases[alias] = group
        for key in keys:
            aliases[key] = group
    return sorted(groups.values(), key=lambda c: (c.published_at, c.id))
