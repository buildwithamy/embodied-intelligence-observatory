"""Fetch original bodies for an explicitly chosen review shortlist; no model API."""
import argparse
import json
from pathlib import Path

from embodied_observatory.http import HttpClient
from embodied_observatory.pipeline import load_items, store_items
from embodied_observatory.research import deepen

parser = argparse.ArgumentParser()
parser.add_argument("--week", required=True)
parser.add_argument("--ids", nargs="+", required=True, help="Candidate IDs or arXiv IDs")
args = parser.parse_args()
root = Path.cwd()
items = load_items(root / "data/candidates" / (args.week + ".json"))
client = HttpClient(root / ".cache/http")
chosen = [c for c in items if c.id in args.ids or c.arxiv_id in args.ids]
for item in chosen:
    deepen(item, client)
store_items(root / "data/research" / (args.week + ".json"), chosen)
print(json.dumps([{"id": c.id, "title": c.title, "evidence": [{"id": e.id, "kind": e.kind,
       "characters": len(e.text)} for e in c.evidence], "notes": c.notes[-1:]} for c in chosen],
       ensure_ascii=False, indent=2))
