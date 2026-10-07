from datetime import date

import pytest

from embodied_observatory.collectors.feeds import collect_feed, collect_official, collect_releases

START, END = date(2026, 9, 28), date(2026, 10, 4)


class FakeClient:
    def __init__(self, responses):
        self.responses, self.calls = responses, []

    def get_text(self, url):
        self.calls.append(url)
        response = self.responses[url]
        if isinstance(response, Exception):
            raise response
        return response

    get_json = get_text


def source(**kwargs):
    return {"name": "official", "url": "https://example.org/feed", "category": "technology", **kwargs}


def test_rss_dates_boundaries_and_provenance():
    xml = """<rss><channel>
    <item><title>A robot</title><link>https://example.org/a?utm_source=rss</link>
    <pubDate>Mon, 28 Sep 2026 00:00:00 +0900</pubDate><description>Official claim</description></item>
    <item><title>B robot</title><link>https://example.org/b</link>
    <pubDate>Sun, 04 Oct 2026 23:59:00 -0400</pubDate></item>
    <item><title>Too early</title><link>https://example.org/c</link><pubDate>2026-09-27</pubDate></item>
    <item><title>Missing date</title><link>https://example.org/d</link></item>
    </channel></rss>"""
    items = collect_feed(FakeClient({"https://example.org/feed": xml}), START, END, source())
    assert [x.published_at for x in items] == [START, END]
    assert items[0].canonical_url == "https://example.org/a"
    assert "Official claim" in items[0].evidence[0].text
    assert items[0].evidence[0].url == items[0].url
    assert items[0].retrieved_at.tzinfo is not None


def test_atom_namespaces_and_alternate_link():
    xml = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Robot class</title>
    <link rel="self" href="https://example.org/api"/><link href="/class"/>
    <published>2026-09-30T12:00:00Z</published><updated>2026-10-06T10:00:00Z</updated>
    <summary>Teaching robot control</summary><author><name>Lab</name></author></entry></feed>"""
    item = collect_feed(FakeClient({"https://example.org/feed": xml}), START, END, source())[0]
    assert item.url == "https://example.org/class"
    assert item.published_at == date(2026, 9, 30)
    assert item.authors == ["Lab"]


def test_education_requires_both_subject_and_teaching():
    xml = """<rss><channel>
    <item><title>Robot research</title><link>https://example.org/a</link><pubDate>2026-09-30</pubDate></item>
    <item><title>General course</title><link>https://example.org/b</link><pubDate>2026-09-30</pubDate></item>
    <item><title>Robot control course</title><link>https://example.org/c</link><pubDate>2026-09-30</pubDate></item>
    </channel></rss>"""
    items = collect_feed(
        FakeClient({"https://example.org/feed": xml}),
        START,
        END,
        source(category="education", keywords=["robot"], education_keywords=["course"]),
    )
    assert [x.title for x in items] == ["Robot control course"]


def test_education_excludes_incidental_robot_mentions_in_broad_course():
    xml = """<rss><channel><item><title>Guide to the space economy</title>
    <description>A course mentions robot missions in one chapter.</description>
    <link>https://example.org/space</link><pubDate>2026-09-30</pubDate></item></channel></rss>"""
    args = source(
        category="education", keywords=["robot"], title_keywords=["robot"], education_keywords=["course"]
    )
    assert collect_feed(FakeClient({"https://example.org/feed": xml}), START, END, args) == []


def test_changed_or_malformed_feed_is_failure_not_empty_success():
    with pytest.raises(ValueError):
        collect_feed(FakeClient({"https://example.org/feed": "<html/>"}), START, END, source())
    with pytest.raises(Exception):
        collect_feed(FakeClient({"https://example.org/feed": "<rss"}), START, END, source())
    assert (
        collect_feed(FakeClient({"https://example.org/feed": "<rss><channel/></rss>"}), START, END, source())
        == []
    )


def release(day, number, **kwargs):
    return {
        "name": f"v{number}",
        "published_at": day,
        "html_url": f"https://github.com/org/repo/releases/tag/v{number}",
        "body": "Added robot control",
        "draft": False,
        "prerelease": False,
        **kwargs,
    }


def test_releases_paginate_without_premature_date_cutoff():
    base = "https://api.github.com/repos/org/repo/releases"
    old = [release("2020-01-01T00:00:00Z", x) for x in range(100)]
    # GitHub creation order need not match published_at order.
    page2 = [
        release("2026-09-28T00:00:00Z", 101),
        release("2026-10-04T20:00:00Z", 102),
        release("2026-10-05T00:00:00Z", 103),
        release("2026-09-30T00:00:00Z", 104, draft=True),
        release("2026-09-30T00:00:00Z", 105, prerelease=True),
    ]
    client = FakeClient({base + "?per_page=100&page=1": old, base + "?per_page=100&page=2": page2})
    items = collect_releases(client, START, END, source(url=base, repo="org/repo", category="open_source"))
    assert len(client.calls) == 2
    assert len(items) == 2
    assert items[0].github_url == "https://github.com/org/repo"
    assert items[0].evidence[0].kind == "github_release"
    assert "Added robot control" in items[0].evidence[0].text


def test_release_api_error_and_page_limit_are_not_success():
    base = "https://api.github.com/repos/org/repo/releases"
    args = source(url=base, repo="org/repo", category="open_source", max_pages=1)
    with pytest.raises(ValueError, match="must be a list"):
        collect_releases(
            FakeClient({base + "?per_page=100&page=1": {"message": "rate limited"}}), START, END, args
        )
    with pytest.raises(ValueError, match="coverage incomplete"):
        collect_releases(
            FakeClient({base + "?per_page=100&page=1": [release("2020-01-01", x) for x in range(100)]}),
            START,
            END,
            args,
        )


def test_official_requires_detail_publication_date_not_path_date():
    base, article = "https://example.org/policy/", "https://example.org/policy/202609/t20260930_123.html"
    listing = '<li><a href="202609/t20260930_123.html">机器人专业</a></li>'
    detail = '<meta name="PubDate" content="2026-09-29"><h1>机器人专业教学建设</h1><div class="TRS_Editor">培养方案<br>课程要求</div>'
    client = FakeClient({base: listing, article: detail})
    items = collect_official(client, START, END, source(url=base, category="policy", keywords=["机器人"]))
    assert items[0].published_at == date(2026, 9, 29)
    assert items[0].raw_summary == "培养方案 课程要求"
    assert items[0].evidence[0].kind == "official_body"


def test_official_structure_and_detail_failures_are_visible():
    base, article = "https://example.org/policy/", "https://example.org/policy/202609/t20260930_123.html"
    with pytest.raises(ValueError, match="structure may have changed"):
        collect_official(FakeClient({base: "<h1>Changed</h1>"}), START, END, source(url=base))
    client = FakeClient(
        {base: '<a href="202609/t20260930_123.html">机器人课程</a>', article: "<h1>无日期</h1>"}
    )
    with pytest.raises(ValueError, match="coverage incomplete"):
        collect_official(client, START, END, source(url=base))


def test_no_undated_release_fallback_to_created_date():
    base = "https://api.github.com/repos/org/repo/releases"
    row = release(None, 1, created_at="2026-09-30T00:00:00Z")
    assert (
        collect_releases(
            FakeClient({base + "?per_page=100&page=1": [row]}),
            START,
            END,
            source(url=base, repo="org/repo", category="open_source"),
        )
        == []
    )
