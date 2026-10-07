"""Dated paper discovery; publication dates remain distinct from discovery dates.

robotics_arXiv_daily stores a cumulative JSON whose displayed date is arXiv's
*updated* date, and whose author column contains only the last author. Boundary
snapshots identify new IDs; arXiv Atom supplies actual publication metadata.
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from datetime import time as day_time
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from embodied_observatory.http import SourceError
from embodied_observatory.models import Candidate, Evidence
from embodied_observatory.normalization import normalize_arxiv_id, normalize_url

logger = logging.getLogger(__name__)
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"


def _warn(source: dict, message: str) -> None:
    source.setdefault("_warnings", []).append(message)
    logger.warning("%s: %s", source.get("name", "paper source"), message)


def _stats(source: dict, **values) -> None:
    source.setdefault("_stats", {}).update(values)


def _date(value) -> date:
    if not isinstance(value, str) or len(value) < 10:
        raise ValueError("missing publication date")
    return date.fromisoformat(value[:10])


def _text(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("expected a text field")
    return " ".join(value.split())


def _evidence(url: str, source: str, kind: str, text: str) -> Evidence:
    key = hashlib.sha256((url + kind + source + text).encode()).hexdigest()[:20]
    return Evidence(id="ev-" + key, url=url, source=source, kind=kind, text=text)


def _validate_range(start: date, end: date) -> None:
    if start > end:
        raise ValueError("start must be <= end")


def _snapshot(client, repository: str, path: str, sha: str) -> tuple[dict, str]:
    url = f"https://raw.githubusercontent.com/{repository}/{sha}/{path}"
    payload = client.get_json(url)
    if not isinstance(payload, dict) or not all(isinstance(v, dict) for v in payload.values()):
        raise SourceError("robotics snapshot schema changed: expected topic -> arXiv ID -> row")
    papers = {}
    for category, rows in payload.items():
        for key, row in rows.items():
            aid = normalize_arxiv_id(str(key))
            if not aid or not isinstance(row, str):
                raise SourceError("robotics snapshot contains an invalid ID or row")
            if aid not in papers:
                papers[aid] = {"row": row, "categories": [category]}
            elif category not in papers[aid]["categories"]:
                papers[aid]["categories"].append(category)
    return papers, url


def _row_metadata(row: str) -> dict:
    cells = row.strip().strip("|").split("|")
    if len(cells) < 5:
        raise ValueError("malformed robotics Markdown row")
    row_date = _date(cells[0].strip().strip("*"))
    title = cells[1].strip().strip("*")
    links = re.findall(r"\]\((https?://[^)]+)\)", cells[4])
    code = project = ""
    for link in links:
        link = normalize_url(link)
        if "github.com/" in link:
            code = link
        else:
            project = link
    return {"updated_at": row_date, "row_title": title,
            "github_url": code, "project_url": project}


def _arxiv_batch(client, ids: list[str], source: dict) -> dict[str, dict]:
    params = {"id_list": ",".join(ids), "max_results": len(ids)}
    url = source.get("arxiv_api_url", "https://export.arxiv.org/api/query") + "?" + urlencode(params)
    try:
        feed = ET.fromstring(client.get_text(url))
    except ET.ParseError as exc:
        raise SourceError("arXiv returned malformed Atom") from exc
    if feed.tag != ATOM + "feed":
        raise SourceError("arXiv returned an unexpected document")
    result = {}
    for entry in feed.findall(ATOM + "entry"):
        aid = normalize_arxiv_id(entry.findtext(ATOM + "id", ""))
        if aid not in ids:
            continue
        title = _text(entry.findtext(ATOM + "title", ""))
        summary = _text(entry.findtext(ATOM + "summary", ""))
        authors = [_text(a.findtext(ATOM + "name", "")) for a in entry.findall(ATOM + "author")]
        authors = [a for a in authors if a]
        try:
            published = _date(entry.findtext(ATOM + "published", ""))
        except ValueError:
            continue
        if not title or not authors or not summary:
            continue
        comments = entry.findtext(ARXIV + "comment", "")
        links = re.findall(r"https?://[^\s<>]+", comments)
        result[aid] = {"title": title, "abstract": summary, "authors": authors,
                       "published_at": published, "url": url, "comment_links": links}
    return result


def _arxiv_abs(client, aid: str) -> dict:
    """Verified arXiv HTML fallback: citation_date is first submission date.

    citation_online_date can instead be the last revision and must not be used.
    The abstract/title/complete citation_author metadata come from the same page.
    """
    url = "https://arxiv.org/abs/" + aid
    soup = BeautifulSoup(client.get_text(url), "html.parser")
    meta = {}
    for node in soup.find_all("meta"):
        name, content = node.get("name", ""), node.get("content", "")
        if name.startswith("citation_") and content:
            meta.setdefault(name, []).append(content)
    if normalize_arxiv_id(meta.get("citation_arxiv_id", [""])[0]) != aid:
        raise SourceError("arXiv abstract page ID mismatch")
    title = _text(meta.get("citation_title", [""])[0])
    abstract = _text(meta.get("citation_abstract", [""])[0])
    authors = []
    for name in meta.get("citation_author", []):
        parts = name.split(",", 1)
        authors.append(_text(parts[1] + " " + parts[0]) if len(parts) == 2 else _text(name))
    try:
        published = _date(meta.get("citation_date", [""])[0].replace("/", "-"))
    except ValueError as exc:
        raise SourceError("arXiv abstract page lacks original citation_date") from exc
    if not title or not abstract or not authors:
        raise SourceError("arXiv abstract page lacks complete paper metadata")
    return {"title": title, "abstract": abstract, "authors": authors,
            "published_at": published, "url": url, "comment_links": []}


def collect_robotics(client, start: date, end: date, source: dict) -> list[Candidate]:
    """IDs newly retained in the cumulative source during the UTC commit interval.

    No whole-history fallback is permitted if baseline or metadata are missing.
    Boundary comparison is valid for this source's cumulative append/update
    format; source removals and re-additions are explicitly outside this measure.
    """
    _validate_range(start, end)
    repository = source.get("repository", source.get("repo", "jiangranlv/robotics_arXiv_daily"))
    path = source.get("snapshot_path", "docs/cv-arxiv-daily.json")
    base = f"https://api.github.com/repos/{repository}/commits"
    since = datetime.combine(start, day_time.min, timezone.utc).isoformat().replace("+00:00", "Z")
    until = datetime.combine(end, day_time.max, timezone.utc).isoformat().replace("+00:00", "Z")
    commits, seen_shas = [], set()
    page_size = int(source.get("page_size", 100))
    if not 1 <= page_size <= 100:
        raise ValueError("GitHub page_size must be between 1 and 100")
    for page in range(1, int(source.get("max_pages", 30)) + 1):
        url = base + "?" + urlencode({"path": path, "since": since, "until": until,
                                      "per_page": page_size, "page": page})
        payload = client.get_json(url)
        if not isinstance(payload, list):
            raise SourceError("GitHub commit API schema changed")
        for commit in payload:
            try:
                sha = commit["sha"]
                stamp = _date(commit["commit"]["committer"]["date"])
            except (TypeError, KeyError, ValueError) as exc:
                raise SourceError("GitHub commit entry lacks SHA/date") from exc
            if sha in seen_shas:
                raise SourceError("GitHub commit pagination repeated a SHA")
            seen_shas.add(sha)
            if start <= stamp <= end:
                commits.append(commit)
        if len(payload) < page_size:
            break
    else:
        raise SourceError("GitHub commit pagination exceeded max_pages; refusing truncated coverage")
    _stats(source, commits_in_range=len(commits), raw_items=0)
    if not commits:
        _warn(source, f"No robotics source updates in {start}..{end}; no historical substitution")
        return []
    commits.sort(key=lambda c: c["commit"]["committer"]["date"])
    parents = commits[0].get("parents", [])
    if not parents:
        raise SourceError("robotics initial commit has no baseline; whole history is not treated as new")
    before, baseline_url = _snapshot(client, repository, path, parents[0]["sha"])
    after, snapshot_url = _snapshot(client, repository, path, commits[-1]["sha"])
    new_ids = sorted(set(after) - set(before))
    removed = len(set(before) - set(after))
    _stats(source, raw_items=len(new_ids), baseline_sha=parents[0]["sha"],
           snapshot_sha=commits[-1]["sha"], removed_ids=removed)
    if removed:
        _warn(source, f"Cumulative robotics source removed {removed} IDs; boundary additions exclude re-additions")
    rows, parsed_ids = {}, []
    for aid in new_ids:
        try:
            rows[aid] = _row_metadata(after[aid]["row"])
            parsed_ids.append(aid)
        except ValueError:
            _warn(source, f"Malformed robotics row skipped: {aid}")
    metadata = {}
    failures = 0
    batch_size = int(source.get("arxiv_batch_size", 50))
    if not 1 <= batch_size <= 100:
        raise ValueError("arxiv_batch_size must be between 1 and 100")
    for offset in range(0, len(parsed_ids), batch_size):
        if offset:
            # arXiv asks API clients to space requests by at least three seconds.
            time.sleep(float(source.get("arxiv_delay_seconds", 3)))
        ids = parsed_ids[offset:offset + batch_size]
        try:
            metadata.update(_arxiv_batch(client, ids, source))
        except (SourceError, OSError, ValueError) as exc:
            failures += 1
            _warn(source, f"arXiv metadata batch unavailable ({len(ids)} papers): {type(exc).__name__}")
    missing = set(parsed_ids) - set(metadata)
    fallback_limit = int(source.get("arxiv_fallback_limit", 20))
    if fallback_limit < 0:
        raise ValueError("arxiv_fallback_limit must be nonnegative")
    fallback_ids = sorted(missing)[:fallback_limit]
    fallback_recovered = 0
    for aid in fallback_ids:
        try:
            metadata[aid] = _arxiv_abs(client, aid)
            fallback_recovered += 1
        except (SourceError, OSError, ValueError):
            pass
    missing = set(parsed_ids) - set(metadata)
    _stats(source, metadata_fallback_attempted=len(fallback_ids),
           metadata_fallback_recovered=fallback_recovered)
    _stats(source, metadata_failed_batches=failures, metadata_missing_items=len(missing))
    if missing:
        _warn(source, f"Skipped {len(missing)} robotics IDs without verified publication date/authors/abstract")
    if new_ids and not metadata:
        raise SourceError("No robotics additions have verified arXiv metadata")
    name = source.get("name", "robotics_arxiv_daily")
    candidates = []
    for aid, paper in metadata.items():
        row = rows[aid]
        canonical = "https://arxiv.org/abs/" + aid
        note = (f"robotics源新增区间：{start}～{end}；表格日期{row['updated_at']}是arXiv修订日，"
                "发表日与完整作者来自arXiv API；累计快照ID差，不代表逐条首次抓取时间。")
        evidence = [_evidence(canonical, "arXiv", "paper_abstract", paper["abstract"]),
                    _evidence(snapshot_url, name, "source_discovery",
                              f"{aid} absent from {baseline_url}; present in {snapshot_url}. {note}")]
        if not start <= paper["published_at"] <= end:
            note += " 论文首次发表早于/晚于本期，属于本期来源新收录。"
        candidates.append(Candidate(
            title=paper["title"], url=canonical, canonical_url=canonical,
            published_at=paper["published_at"], source_type="paper", sources=[name],
            source_urls=[snapshot_url, baseline_url, paper["url"], canonical],
            authors=paper["authors"], arxiv_id=aid, abstract=paper["abstract"],
            raw_summary=after[aid]["row"], github_url=row["github_url"], project_url=row["project_url"],
            categories=after[aid]["categories"], evidence=evidence, notes=[note],
        ))
    _stats(source, collected_items=len(candidates))
    return candidates


def _hf_pages(client, url: str, source: dict):
    """The verified API returns a complete list; explicit cursor envelopes also work.

    Do not invent page parameters for the public list endpoint. A future envelope
    with nextCursor/next is followed, and unknown/truncated formats fail visibly.
    """
    seen = set()
    for _ in range(int(source.get("max_pages", 30))):
        if url in seen:
            raise SourceError("HF pagination loop")
        seen.add(url)
        data = client.get_json(url)
        if isinstance(data, list):
            yield data
            return
        if not isinstance(data, dict) or not isinstance(data.get("papers", data.get("items")), list):
            raise SourceError("HF Daily Papers API schema changed")
        yield data.get("papers", data.get("items"))
        next_url = data.get("next")
        cursor = data.get("nextCursor")
        if not next_url and not cursor:
            if data.get("hasMore"):
                raise SourceError("HF response indicates more records without a continuation")
            return
        if next_url:
            if not isinstance(next_url, str) or not next_url.startswith("https://huggingface.co/api/"):
                raise SourceError("HF supplied an unexpected continuation URL")
            url = next_url
        else:
            url = url.split("&cursor=", 1)[0] + "&" + urlencode({"cursor": cursor})
    raise SourceError("HF pagination exceeded max_pages")


def collect_hf(client, start: date, end: date, source: dict) -> list[Candidate]:
    """Collect daily recommendations, retaining first publication date separately."""
    _validate_range(start, end)
    endpoint = source.get("api_url", source.get("url", "https://huggingface.co/api/daily_papers"))
    name = source.get("name", "huggingface_daily_papers")
    candidates, failed_days, raw_count = {}, [], 0
    days_ok = 0
    for index in range((end - start).days + 1):
        day = start + timedelta(days=index)
        url = endpoint + "?" + urlencode({"date": day.isoformat()})
        try:
            # Materialize all pages before processing: a broken page cannot look
            # like a fully covered day in the run manifest.
            pages = list(_hf_pages(client, url, source))
        except (SourceError, OSError, ValueError) as exc:
            failed_days.append(day.isoformat())
            _warn(source, f"HF day {day} unavailable: {type(exc).__name__}")
            continue
        days_ok += 1
        for record in (r for page in pages for r in page):
            raw_count += 1
            try:
                if not isinstance(record, dict):
                    raise ValueError("invalid daily record")
                paper = record.get("paper", record)
                if not isinstance(paper, dict):
                    raise ValueError("invalid paper object")
                aid = normalize_arxiv_id(paper.get("id", ""))
                title = _text(paper.get("title", record.get("title", "")))
                abstract = _text(paper.get("summary", record.get("summary", "")))
                published = _date(paper.get("publishedAt"))
                authors = [a["name"] if isinstance(a, dict) else a for a in paper.get("authors", [])]
                authors = [a for a in authors if isinstance(a, str) and a.strip()]
                if not aid or not title or not authors or not abstract:
                    raise ValueError("incomplete paper metadata")
                submitted = paper.get("submittedOnDailyAt")
                if submitted and _date(submitted) != day:
                    # A dated endpoint returning another day is not acceptable
                    # as a fallback for an empty or future requested period.
                    _warn(source, f"HF date mismatch for {aid}: requested {day}, submitted {submitted}")
                    continue
                if published > day:
                    _warn(source, f"HF future publication date skipped: {aid} ({published} > {day})")
                    continue
                popularity = max(0, int(paper.get("upvotes", record.get("upvotes", 0)) or 0))
                hf_url = "https://huggingface.co/papers/" + aid
                canonical = "https://arxiv.org/abs/" + aid
                if aid in candidates:
                    current = candidates[aid]
                    current.discovery_dates = sorted(set(current.discovery_dates + [day]))
                    current.community_popularity = max(current.community_popularity, popularity)
                    current.source_urls = sorted(set(current.source_urls + [url]))
                    continue
                notes = [f"HF Daily推荐日期：{day}；published_at保存论文首次发表日，投票仅代表社区关注度。"]
                if not start <= published <= end:
                    notes.append("本期推荐的历史论文：不应描述为本周新发表论文。")
                evidence = [_evidence(hf_url, name, "paper_abstract", abstract),
                            _evidence(url, name, "source_discovery",
                                      f"Daily recommendation {day}; paper published {published}; id {aid}.")]
                candidates[aid] = Candidate(
                    title=title, url=canonical, canonical_url=canonical, published_at=published,
                    source_type="paper", sources=[name], source_urls=[url, hf_url, canonical],
                    authors=authors, arxiv_id=aid, abstract=abstract, raw_summary=abstract,
                    github_url=normalize_url(paper.get("githubRepo") or ""),
                    project_url=normalize_url(paper.get("projectPage") or ""),
                    community_popularity=popularity, discovery_dates=[day], evidence=evidence, notes=notes,
                )
            except (ValueError, TypeError, KeyError) as exc:
                _warn(source, f"Incomplete HF paper record skipped on {day}: {type(exc).__name__}")
    _stats(source, requested_days=(end - start).days + 1, successful_days=days_ok,
           failed_days=failed_days, raw_items=raw_count, collected_items=len(candidates))
    if not days_ok:
        raise SourceError("All requested HF Daily Papers dates failed")
    if raw_count and not candidates:
        raise SourceError("No requested HF records have valid dated paper metadata")
    if not candidates:
        _warn(source, f"No HF papers for requested dates {start}..{end}; no historical substitution")
    return list(candidates.values())
