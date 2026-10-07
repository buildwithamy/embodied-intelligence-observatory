"""Audit saved real-run artifacts. Optional public link checks never publish."""
import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from embodied_observatory.pipeline import load_items, load_json, validate_week, write_json


def audit(root: Path, week: str, check_links=False):
    validate_week(week)
    manifest = load_json(root / "runs" / (week + ".json"))
    items = load_items(root / "data/candidates" / (week + ".json"))
    selected = [c for c in items if c.status in {"selected", "analyzed"}]
    problems = []
    ids = [c.arxiv_id for c in selected if c.arxiv_id]
    if len(ids) != len(set(ids)):
        problems.append("duplicate selected arXiv IDs")
    for item in selected:
        if not manifest["date_range"]["start"] <= item.published_at.isoformat() <= manifest["date_range"]["end"]:
            problems.append(item.id + ": publication date outside interval")
        if item.source_type == "paper" and (not item.authors or not item.abstract):
            problems.append(item.id + ": paper metadata incomplete")
        if not item.analysis or item.analysis.fact_check != "pass":
            problems.append(item.id + ": structured review incomplete")
    draft = (root / "drafts" / (week + ".md")).read_text(encoding="utf-8")
    for number in range(1, 8):
        if f"## 0{number}｜" not in draft:
            problems.append(f"missing report section {number}")
    urls = sorted(set(re.findall(r"\]\((https?://[^)\s]+)\)", draft)))
    statuses = []
    if check_links:
        def check(url):
            try:
                with httpx.Client(timeout=20, follow_redirects=True,
                                  headers={"User-Agent": "Embodied-Observatory/0.1 (manual link audit)"}) as client:
                    with client.stream("GET", url) as response:
                        return {"url": url, "http_status": response.status_code,
                                "ok": response.is_success, "final_url": str(response.url)}
            except httpx.RequestError:
                return {"url": url, "http_status": None, "ok": False, "error": "network unavailable"}
        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(check, urls))
    result = {"week": week, "selected": len(selected), "papers": len(ids), "schema_valid": True,
              "problems": problems, "unique_links": len(urls), "links_checked": check_links,
              "link_results": statuses,
              "note": "Schema/date/dedup/link checks do not independently reproduce research claims."}
    write_json(root / "runs" / (week + "-audit.json"), result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--week", required=True)
    parser.add_argument("--check-links", action="store_true")
    args = parser.parse_args()
    result = audit(Path.cwd(), args.week, args.check_links)
    print(json.dumps({k: v for k, v in result.items() if k != "link_results"}, ensure_ascii=False, indent=2))
    print("links failed:", json.dumps([r for r in result["link_results"] if not r["ok"]], ensure_ascii=False))
    raise SystemExit(bool(result["problems"]))
