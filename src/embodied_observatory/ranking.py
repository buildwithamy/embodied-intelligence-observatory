import re

from .models import Candidate


def matches(text: str, term: str) -> bool:
    if term.isascii() and " " not in term:
        return bool(re.search(r"\b" + re.escape(term) + r"\w*\b", text, re.I))
    return term.casefold() in text.casefold()


def overall(candidate: Candidate, config: dict) -> float:
    weights = config["weights"]
    if abs(sum(weights.values()) - 1) > 1e-6 or any(v < 0 for v in weights.values()):
        raise ValueError("scoring weights must be nonnegative and sum to 1")
    return round(sum(getattr(candidate, name) * weight for name, weight in weights.items()), 3)


def classify_rank(items: list[Candidate], scoring: dict, watchlist: dict) -> list[Candidate]:
    result = []
    for item in items:
        text = " ".join([item.title, item.abstract, item.raw_summary, *item.organizations])
        relevant = any(matches(text, term) for term in scoring["relevance_terms"])
        # Trusted robotics release feeds already have a direct connection to the domain.
        relevant = relevant or item.source_type == "open_source"
        big = item.source_type in watchlist["always_review_categories"] or (
            any(matches(text, term) for term in watchlist["event_terms"])
            and any(matches(text, org) for org in watchlist["organizations"]))
        big = big or (item.source_type == "education" and any(
            matches(text, term) for term in watchlist["education_major_terms"]))
        item.big_news = big
        item.categories = [item.source_type]
        item.tags = [tag for tag, terms in scoring["tag_terms"].items()
                     if any(matches(text, term) for term in terms)]
        if not relevant:
            item.status = "watch" if big else "excluded"
            item.notes.append("规则预筛未确认直接具身关联；大新闻标记进入二次复核" if big else "规则预筛未匹配具身关联")
            result.append(item)
            continue
        item.scoring_method = "heuristic_provisional"
        item.technical_score = 3 if item.source_type in {"paper", "technology", "open_source"} else 2
        item.industry_score = 3 if item.source_type == "industry" else 2
        item.education_score = 4 if item.source_type in {"education", "policy"} else 2
        item.reproducibility_score = 3 if item.github_url else 1
        item.evidence_score = 4 if item.evidence else 1
        item.overall_score = overall(item, scoring)
        item.status = "candidate" if item.overall_score >= scoring["threshold"] else "watch"
        result.append(item)
    return sorted(result, key=lambda c: (-c.overall_score, c.id))


def select(items: list[Candidate], scoring: dict) -> list[Candidate]:
    counts = {}
    selected = []
    for item in sorted(items, key=lambda c: (-c.overall_score, c.id)):
        if item.status not in {"candidate", "selected", "analyzed"}:
            continue
        category = item.source_type
        if counts.get(category, 0) >= scoring["limits"][category]:
            continue
        counts[category] = counts.get(category, 0) + 1
        item.status = "analyzed" if item.analysis else "selected"
        selected.append(item)
    return selected
