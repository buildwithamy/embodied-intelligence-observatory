"""Small public feed, official HTML and GitHub release collectors.

Network errors intentionally propagate to the per-source pipeline boundary. A
valid empty feed is different from a failed request or changed page structure.
"""

from __future__ import annotations

import hashlib
import html
import logging
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from embodied_observatory.models import Candidate, Evidence
from embodied_observatory.normalization import normalize_url

log = logging.getLogger(__name__)


def _text(value: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()


def _date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return parsedate_to_datetime(value).date()
        except (ValueError, TypeError, OverflowError):
            return None


def _allowed(text: str, source: dict) -> bool:
    lower = text.casefold()
    for group in ("keywords", "education_keywords"):
        words = source.get(group, [])
        if words and not any(word.casefold() in lower for word in words):
            return False
    return True


def _candidate(
    title: str, url: str, day: date, summary: str, source: dict, kind: str, authors: list[str] | None = None
) -> Candidate:
    canonical = normalize_url(url)
    identifier = hashlib.sha256((kind + canonical).encode()).hexdigest()[:20]
    return Candidate(
        title=title,
        url=url,
        canonical_url=canonical,
        published_at=day,
        source_type=source["category"],
        sources=[source["name"]],
        source_urls=[source["url"]],
        authors=authors or [],
        organizations=source.get("organizations", []),
        raw_summary=summary,
        evidence=[
            Evidence(
                id=identifier,
                url=url,
                source=source["name"],
                kind=kind,
                text=f"Published: {day.isoformat()}\n{title}\n{summary}".strip(),
            )
        ],
    )


def collect_feed(client, start: date, end: date, source: dict) -> list[Candidate]:
    """Parse RSS 2.0 or Atom using the publisher's original calendar date."""
    root = ET.fromstring(client.get_text(source["url"]))
    atom = "{http://www.w3.org/2005/Atom}"
    is_atom = root.tag == atom + "feed"
    if not is_atom and root.tag != "rss":
        raise ValueError(f"Unsupported feed root: {root.tag}")
    if not is_atom and root.find("channel") is None:
        raise ValueError("RSS response is missing its channel")
    entries = root.findall(atom + "entry") if is_atom else root.findall("./channel/item")
    result = []
    for entry in entries:
        if is_atom:
            title = _text(entry.findtext(atom + "title"))
            links = [
                el.attrib.get("href", "")
                for el in entry.findall(atom + "link")
                if el.attrib.get("rel", "alternate") == "alternate"
            ]
            link = links[0] if links else ""
            day = _date(entry.findtext(atom + "published") or entry.findtext(atom + "updated"))
            summary = _text(entry.findtext(atom + "content") or entry.findtext(atom + "summary"))
            authors = [_text(a.findtext(atom + "name")) for a in entry.findall(atom + "author")]
        else:
            title, link = _text(entry.findtext("title")), (entry.findtext("link") or "").strip()
            day = _date(entry.findtext("pubDate") or entry.findtext("{http://purl.org/dc/elements/1.1/}date"))
            summary = _text(
                entry.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
                or entry.findtext("description")
            )
            author = _text(
                entry.findtext("{http://purl.org/dc/elements/1.1/}creator") or entry.findtext("author")
            )
            authors = [author] if author else []
        if not day or not title or not link:
            log.warning("Skipping feed entry without valid date/title/link: %s", source["name"])
            continue
        if (
            start <= day <= end
            and _allowed(title + " " + summary, source)
            and _allowed(title, {"keywords": source.get("title_keywords", [])})
        ):
            result.append(
                _candidate(
                    title, urljoin(source["url"], link), day, summary, source, "official_feed", authors
                )
            )
    return result


def collect_releases(client, start: date, end: date, source: dict) -> list[Candidate]:
    """Read all release pages; drafts and explicitly marked prereleases are excluded.

    GitHub orders releases by creation, which can differ from publication. Do
    not stop on an old item. Exhaustion or a configured page limit is explicit.
    """
    base = source["url"].split("?", 1)[0]
    limit = int(source.get("max_pages", 20))
    result, seen = [], set()
    for page in range(1, limit + 1):
        rows = client.get_json(f"{base}?per_page=100&page={page}")
        if not isinstance(rows, list):
            raise ValueError("GitHub Releases response must be a list")
        for row in rows:
            if row.get("draft") or row.get("prerelease"):
                continue
            day = _date(row.get("published_at"))
            url = row.get("html_url", "")
            if not day or not url or not start <= day <= end or url in seen:
                continue
            seen.add(url)
            name = row.get("name") or row.get("tag_name")
            if not name:
                log.warning("Skipping unnamed release: %s", source["name"])
                continue
            title = f"{source.get('project', source['name'])} {name}"
            summary = (row.get("body") or "").strip()
            item = _candidate(title, url, day, summary, source, "github_release")
            item.github_url = "https://github.com/" + source["repo"]
            result.append(item)
        if len(rows) < 100:
            return result
    raise ValueError(f"GitHub pagination limit {limit} reached; coverage incomplete")


class _OfficialHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.meta: dict[str, str] = {}
        self.parts: list[str] = []
        self.heading: list[str] = []
        self.body: list[str] = []
        self._anchor = None
        self._heading = False
        self._body_depth = 0
        self._ignore = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style"}:
            self._ignore += 1
        if tag == "meta":
            self.meta[(attrs.get("name") or attrs.get("property") or "").casefold()] = attrs.get(
                "content", ""
            )
        if tag == "a":
            self._anchor = [attrs.get("href", ""), []]
        if tag == "h1":
            self._heading = True
        if self._body_depth and tag not in {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }:
            self._body_depth += 1
        elif tag == "article" or any(
            x in attrs.get("class", "")
            for x in ["TRS_Editor", "v_news_content", "entry-content", "article-body"]
        ):
            self._body_depth = 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self._ignore = max(0, self._ignore - 1)
        if tag == "a" and self._anchor is not None:
            self.links.append((self._anchor[0], _text(" ".join(self._anchor[1]))))
            self._anchor = None
        if tag == "h1":
            self._heading = False
        if self._body_depth:
            self._body_depth -= 1

    def handle_data(self, value):
        if self._ignore:
            return
        self.parts.append(value)
        if self._anchor is not None:
            self._anchor[1].append(value)
        if self._heading:
            self.heading.append(value)
        if self._body_depth:
            self.body.append(value)


def collect_official(client, start: date, end: date, source: dict) -> list[Candidate]:
    """Education ministry dated lists; verify publication date in each article.

    URL dates only reduce detail requests, never establish publication facts.
    Government lists have no stable public archive API; this deliberately small
    collector is a supplement, with historical coverage bounded by visible lists.
    """
    listing = _OfficialHTML()
    listing.feed(client.get_text(source["url"]))
    pattern = source.get("link_pattern", r"/\d{6}/t(\d{8})_\d+\.html$")
    links = {}
    for href, title in listing.links:
        url = urljoin(source["url"], href)
        if urlsplit(url).netloc != urlsplit(source["url"]).netloc:
            continue
        match = re.search(pattern, url)
        if match:
            links[url] = (title, match)
    if not links:
        raise ValueError("Official listing has no expected dated article links; structure may have changed")
    result, failures = [], []
    for url, (listed_title, match) in links.items():
        url_day = datetime.strptime(match.group(1), "%Y%m%d").date()
        if not start.replace(day=1) <= url_day <= end:
            continue
        try:
            parsed = _OfficialHTML()
            parsed.feed(client.get_text(url))
            full = _text(" ".join(parsed.parts))
            body = _text(" ".join(parsed.body)) or full
            title = parsed.meta.get("articletitle") or _text(" ".join(parsed.heading)) or listed_title
            published = next(
                (
                    parsed.meta[k]
                    for k in ["pubdate", "publishdate", "date", "article:published_time"]
                    if parsed.meta.get(k)
                ),
                "",
            )
            day = _date(published)
            if day is None:
                dateline = re.search(r"(20\d{2}-\d{2}-\d{2})\s*(?:来源|[\u3000 ]*来源)", full)
                day = _date(dateline.group(1)) if dateline else None
            if day is None:
                raise ValueError("No verifiable publication date in official article")
            if start <= day <= end and _allowed(title + " " + body, source):
                result.append(_candidate(title, url, day, body, source, "official_body"))
        except Exception as exc:
            failures.append(f"{url}: {type(exc).__name__}")
            log.warning("Official article failed: %s (%s)", url, type(exc).__name__)
    if failures:
        # Never silently report a partially read official source as complete.
        raise ValueError("Official detail coverage incomplete: " + "; ".join(failures))
    return result
