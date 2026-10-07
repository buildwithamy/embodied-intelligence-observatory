"""Offline source fixtures focus on temporal provenance and incomplete coverage."""
from datetime import date
from urllib.parse import parse_qs, urlsplit

import pytest

from embodied_observatory.collectors.papers import collect_hf, collect_robotics
from embodied_observatory.http import SourceError

START, END = date(2026, 9, 28), date(2026, 10, 4)


def row(aid, title="Robot manipulation"):
    return f"|**2026-10-01**|**{title}**|Last Author Team|[{aid}](http://arxiv.org/abs/{aid})|null|"


def commit(sha, stamp, parent="baseline"):
    return {"sha": sha, "commit": {"committer": {"date": stamp}}, "parents": [{"sha": parent}]}


def atom(ids, published="2026-09-29"):
    entries = "".join(
        f"<entry><id>http://arxiv.org/abs/{aid}v2</id><title>Robot manipulation {aid}</title>"
        f"<published>{published}T12:00:00Z</published><updated>2026-10-01T00:00:00Z</updated>"
        "<summary>We study robotic manipulation with tactile feedback.</summary>"
        "<author><name>First Author</name></author><author><name>Last Author</name></author></entry>"
        for aid in ids
    )
    return f'<feed xmlns="http://www.w3.org/2005/Atom">{entries}</feed>'


class RoboticsClient:
    def __init__(self, baseline, final, commits=None, metadata_failure=False):
        self.baseline, self.final = baseline, final
        self.commits = commits if commits is not None else [commit("final", "2026-10-04T03:00:00Z")]
        self.metadata_failure = metadata_failure
        self.calls = []

    def get_json(self, url):
        self.calls.append(url)
        if "/commits?" in url:
            query = parse_qs(urlsplit(url).query)
            per_page, page = int(query["per_page"][0]), int(query["page"][0])
            return self.commits[(page - 1) * per_page:page * per_page]
        if "/baseline/" in url:
            return self.baseline
        return self.final

    def get_text(self, url):
        self.calls.append(url)
        if self.metadata_failure:
            raise SourceError("network unavailable")
        return atom(parse_qs(urlsplit(url).query)["id_list"][0].split(","))


def test_robotics_snapshot_diff_does_not_collect_history_or_category_move():
    baseline = {"VLA": {"2608.01234": row("2608.01234")}}
    final = {"VLA": {"2608.01234": row("2608.01234"), "2609.12345": row("2609.12345")},
             "Manipulation": {"2608.01234": row("2608.01234"), "2609.12345": row("2609.12345")}}
    source = {"arxiv_delay_seconds": 0}
    result = collect_robotics(RoboticsClient(baseline, final), START, END, source)
    assert [p.arxiv_id for p in result] == ["2609.12345"]
    assert result[0].authors == ["First Author", "Last Author"]
    assert result[0].published_at == date(2026, 9, 29)
    assert result[0].categories == ["VLA", "Manipulation"]
    assert "arXiv修订日" in result[0].notes[0]
    assert source["_stats"]["raw_items"] == 1


def test_robotics_commit_pagination_and_earliest_parent():
    commits = [commit("final", "2026-10-04T03:00:00Z", "middle"),
               commit("middle", "2026-09-28T03:00:00Z", "baseline")]
    client = RoboticsClient({"VLA": {}}, {"VLA": {"2609.12345": row("2609.12345")}}, commits)
    source = {"page_size": 1}
    result = collect_robotics(client, START, END, source)
    assert len(result) == 1
    assert any("page=3" in u for u in client.calls)
    assert source["_stats"]["baseline_sha"] == "baseline"


def test_robotics_no_updates_does_not_use_latest_history():
    client = RoboticsClient({}, {}, commits=[])
    source = {}
    assert collect_robotics(client, START, END, source) == []
    assert len(client.calls) == 1
    assert source["_warnings"]


def test_robotics_no_verified_metadata_fails_visibly():
    client = RoboticsClient({"VLA": {}}, {"VLA": {"2609.12345": row("2609.12345")}},
                            metadata_failure=True)
    source = {}
    with pytest.raises(SourceError, match="verified arXiv metadata"):
        collect_robotics(client, START, END, source)
    assert source["_stats"]["metadata_missing_items"] == 1


def test_arxiv_html_fallback_uses_original_date_and_full_authors():
    class HTMLFallbackClient(RoboticsClient):
        def get_text(self, url):
            if "/api/query" in url:
                raise SourceError("API unavailable")
            return '''<html><head>
              <meta name="citation_arxiv_id" content="2609.12345">
              <meta name="citation_title" content="Robot manipulation">
              <meta name="citation_abstract" content="We study tactile feedback.">
              <meta name="citation_author" content="Author, First">
              <meta name="citation_author" content="Author, Last">
              <meta name="citation_date" content="2026/09/29">
              <meta name="citation_online_date" content="2026/10/01">
            </head></html>'''
    client = HTMLFallbackClient({"VLA": {}}, {"VLA": {"2609.12345": row("2609.12345")}})
    source = {}
    result = collect_robotics(client, START, END, source)
    assert result[0].published_at == date(2026, 9, 29)
    assert result[0].authors == ["First Author", "Last Author"]
    assert source["_stats"]["metadata_fallback_recovered"] == 1
    assert source["_stats"]["metadata_missing_items"] == 0


def hf_record(aid="2609.12345", published="2026-09-29", submitted="2026-09-30", votes=8):
    return {"paper": {"id": aid, "title": "Robot tactile manipulation", "summary": "Tactile feedback study.",
                      "authors": [{"name": "First Author"}, {"name": "Second Author"}],
                      "publishedAt": published + "T00:00:00Z",
                      "submittedOnDailyAt": submitted + "T00:00:00Z", "upvotes": votes,
                      "githubRepo": "https://github.com/robot/study", "projectPage": "https://robot.example/"}}


class HFClient:
    def __init__(self, days):
        self.days, self.calls = days, []

    def get_json(self, url):
        self.calls.append(url)
        day = parse_qs(urlsplit(url).query)["date"][0]
        record = self.days.get(day, [])
        if isinstance(record, Exception):
            raise record
        if isinstance(record, dict) and "cursor_pages" in record:
            cursor = parse_qs(urlsplit(url).query).get("cursor", [""])[0]
            return record["cursor_pages"][cursor]
        return record


def test_hf_recommendation_is_not_publication_date():
    client = HFClient({"2026-09-30": [hf_record(published="2026-08-01")]})
    result = collect_hf(client, START, END, {})
    assert len(result) == 1
    assert result[0].published_at == date(2026, 8, 1)
    assert result[0].discovery_dates == [date(2026, 9, 30)]
    assert any("历史论文" in n for n in result[0].notes)
    assert result[0].community_popularity == 8
    assert result[0].authors == ["First Author", "Second Author"]


def test_hf_partial_day_failure_keeps_other_days_with_warning():
    source = {}
    client = HFClient({"2026-09-29": SourceError("timeout"), "2026-09-30": [hf_record()]})
    result = collect_hf(client, START, END, source)
    assert len(result) == 1
    assert source["_stats"]["failed_days"] == ["2026-09-29"]
    assert source["_stats"]["successful_days"] == 6
    assert source["_warnings"]


def test_hf_all_days_fail_raises():
    client = HFClient({"2026-09-28": SourceError("HTTP 503")})
    with pytest.raises(SourceError, match="All requested"):
        collect_hf(client, START, START, {})


def test_hf_explicit_cursor_pages_and_dedup():
    record = hf_record()
    source = {}
    client = HFClient({"2026-09-30": {"cursor_pages": {
        "": {"papers": [record], "nextCursor": "second"},
        "second": {"papers": [record], "nextCursor": None},
    }}})
    result = collect_hf(client, date(2026, 9, 30), date(2026, 9, 30), source)
    assert len(result) == 1
    assert len(client.calls) == 2
    assert source["_stats"]["raw_items"] == 2


def test_hf_date_mismatch_cannot_fake_a_requested_week():
    source = {}
    client = HFClient({"2026-09-30": [hf_record(submitted="2026-01-01")]})
    with pytest.raises(SourceError, match="valid dated paper metadata"):
        collect_hf(client, START, END, source)
    assert any("date mismatch" in w for w in source["_warnings"])


def test_hf_discovery_evidence_is_unique_per_paper_on_same_date():
    client = HFClient({"2026-09-30": [hf_record(), hf_record(aid="2609.23456")]})
    result = collect_hf(client, START, END, {})
    assert len(result) == 2
    assert result[0].evidence[1].url == result[1].evidence[1].url
    assert result[0].evidence[1].id != result[1].evidence[1].id


def test_invalid_intervals_rejected_before_network():
    client = HFClient({})
    for collector in (collect_hf, collect_robotics):
        with pytest.raises(ValueError):
            collector(client, END, START, {})
    assert not client.calls
