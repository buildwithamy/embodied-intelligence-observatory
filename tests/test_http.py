import hashlib
import json
import time

import httpx
import pytest

from embodied_observatory.http import HttpClient, SourceError


def test_cache_contains_no_headers_or_tokens(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test-secret-never-store")
    url = "https://api.github.com/repos/example/example/releases"

    def response(url, **kwargs):
        assert kwargs["headers"]["Authorization"] == "Bearer test-secret-never-store"
        return httpx.Response(200, text='[{"tag_name":"v1"}]', request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "get", response)
    client = HttpClient(tmp_path)
    assert client.get_json(url)[0]["tag_name"] == "v1"
    contents = next(tmp_path.glob("*.json")).read_text(encoding="utf-8")
    assert "test-secret" not in contents and "Authorization" not in contents
    client.offline = True
    assert client.get_json(url)[0]["tag_name"] == "v1" and client.cache_hits == 1


def test_offline_cache_miss_and_stale(tmp_path):
    with pytest.raises(SourceError):
        HttpClient(tmp_path, offline=True).get_text("https://example.org/no-cache")
    url = "https://example.org/stale"
    path = tmp_path / (hashlib.sha256(url.encode()).hexdigest() + ".json")
    path.write_text(json.dumps({"url": url, "fetched_epoch": time.time() - 999999, "body": "old"}))
    assert HttpClient(tmp_path, offline=True).get_text(url) == "old"
