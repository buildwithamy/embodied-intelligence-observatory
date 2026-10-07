"""Real-data offline dry-run isolation check; formal data hashes must match."""
import hashlib
import json
from pathlib import Path

from embodied_observatory.cli import main
from embodied_observatory.pipeline import write_json

root = Path.cwd()


def snapshot():
    paths = []
    for name in ("data", "drafts", "runs", "reports", ".cache"):
        folder = root / name
        if folder.exists():
            paths.extend(p for p in folder.rglob("*") if p.is_file())
    if (root / "latest.md").exists():
        paths.append(root / "latest.md")
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


before = snapshot()
code = main(["weekly", "--start", "2026-09-28", "--end", "2026-10-04", "--dry-run", "--offline",
             "--skip-research", "--analysis-file", "data/editorial/2026-W40.json"])
after = snapshot()
result = {"week": "2026-W40", "exit_code": code, "formal_files_unchanged": before == after,
          "files_checked": len(before), "network_mode": "offline_real_cache",
          "note": "This check used real cached source responses and real editorial data, not fixtures."}
write_json(root / "runs/2026-W40-dry-run-check.json", result)
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(code or before != after)
