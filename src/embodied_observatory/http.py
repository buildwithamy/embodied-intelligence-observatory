"""Public-response caching. Credentials never enter cache keys, bodies, or logs."""
import hashlib
import json
import logging
import os
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)


class SourceError(RuntimeError):
    pass


class HttpClient:
    def __init__(self, cache_dir: Path, *, refresh=False, offline=False, read_cache: Path | None = None,
                 timeout=25, ttl=21600):
        self.cache_dir = cache_dir
        self.read_cache = read_cache or cache_dir
        self.refresh, self.offline = refresh, offline
        self.timeout, self.ttl = timeout, ttl
        self.requests = self.cache_hits = 0
        self.accessed: dict[str, dict] = {}

    def get_text(self, url: str) -> str:
        key = hashlib.sha256(url.encode()).hexdigest()
        path = self.read_cache / (key + ".json")
        if path.exists() and not self.refresh:
            record = json.loads(path.read_text(encoding="utf-8"))
            if self.offline or time.time() - record["fetched_epoch"] < self.ttl:
                self.cache_hits += 1
                self.accessed[url] = record
                return record["body"]
        if self.offline:
            raise SourceError("offline cache miss")
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
            raise SourceError("invalid public URL")
        headers = {"User-Agent": "Embodied-Observatory/0.1 (manual research)", "Accept": "application/json,*/*"}
        token = os.getenv("GITHUB_TOKEN")
        if token and parsed.hostname == "api.github.com":
            headers["Authorization"] = "Bearer " + token
        error = "request failed"
        for attempt in range(3):
            try:
                self.requests += 1
                response = httpx.get(url, headers=headers, timeout=self.timeout, follow_redirects=True)
                response.raise_for_status()
                record = {"url": url, "fetched_epoch": time.time(), "body": response.text}
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                (self.cache_dir / (key + ".json")).write_text(json.dumps(record, ensure_ascii=False),
                                                             encoding="utf-8")
                self.accessed[url] = record
                return response.text
            except httpx.HTTPStatusError as exc:
                error = f"HTTP {exc.response.status_code} ({parsed.hostname})"
                if exc.response.status_code < 500 and exc.response.status_code != 429:
                    break
            except httpx.RequestError:
                error = f"network unavailable ({parsed.hostname})"
            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))
        raise SourceError(error)

    def get_json(self, url: str):
        try:
            return json.loads(self.get_text(url))
        except json.JSONDecodeError as exc:
            raise SourceError("invalid JSON response") from exc
