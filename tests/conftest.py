"""Isolated replay of the reviewed, real W40 evidence; never writes the live site."""
import shutil
from pathlib import Path

import pytest

from embodied_observatory.pipeline import load_json

ROOT = Path(__file__).resolve().parents[1]
# The W40 replay data quotes third-party articles in full, so the public repository leaves it out.
W40_REPLAY = ROOT / 'runs/2026-W40/editorial_audit.json'


@pytest.fixture
def editorial_workspace(tmp_path):
    if not W40_REPLAY.exists():
        pytest.skip('W40 回放数据含第三方原文，未放入公开仓库')
    for folder in ('config', 'templates'):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    manifest = load_json(ROOT / 'runs/2026-W40/editorial_audit.json')
    files = set(manifest['input_hashes']) | {
        'data/candidates/2026-W40.json', 'data/editorial/2026-W40-v04.json',
        'runs/2026-W40-v04-copy-edit.json', 'runs/2026-W40/editorial_audit.json',
        'runs/2026-W40/EDITORIAL_AUDIT.md', 'runs/2026-W40/news_candidates.json',
        'runs/2026-W40/major_event_snapshot.json', 'runs/2026-W40/editorial_selection.yaml',
    }
    for filename in files:
        target = tmp_path / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / filename, target)
    return tmp_path
