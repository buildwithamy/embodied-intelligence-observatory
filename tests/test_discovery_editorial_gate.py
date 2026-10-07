"""Discovery recall and editorial gates are independent from paper quality scores."""
from datetime import date
from pathlib import Path

import pytest
import yaml

from embodied_observatory.cli import main
from embodied_observatory.discovery import NewsCandidate, canonical_url, discover, lead_id
from embodied_observatory.edition import build_edition
from embodied_observatory.editorial_gate import (
    apply_reviews,
    approve_selection,
    digest,
    score_event,
    validate_selection,
)
from embodied_observatory.pipeline import config, load_json, publish, write_json

ROOT = Path(__file__).resolve().parents[1]
WEEK = '2026-W40'
START, END = date(2026, 9, 21), date(2026, 10, 4)


def selection_path(root):
    return root / 'runs/2026-W40/editorial_selection.yaml'


def issue_path(root):
    return root / 'data/editorial/2026-W40-v04.json'


def change_selection(root, edit):
    path = selection_path(root)
    selection = yaml.safe_load(path.read_text(encoding='utf-8'))
    edit(selection)
    path.write_text(yaml.safe_dump(selection, allow_unicode=True, sort_keys=False), encoding='utf-8')


def approve_fixture(root):
    approve_selection(root, WEEK, selection_path(root), issue_path(root),
                      'synthetic_test_reviewer', True)


@pytest.mark.skipif(not (ROOT / 'runs/2026-W40/news_candidates.json').exists(),
                    reason='W40 回放数据含第三方原文，未放入公开仓库')
def test_recorded_major_news_recall_and_adjacent_amd():
    fixture = yaml.safe_load((ROOT / 'tests/fixtures/major_news_regression_2026w40.yaml').read_text(encoding='utf-8'))
    candidates = {c['id']: c for c in load_json(ROOT / 'runs/2026-W40/news_candidates.json')}
    for row in fixture['positive_events']:
        event = candidates[row['id']]
        assert event['verification'] == 'confirmed' and event['proposed_tier'] == row['tier']
        assert any(row['original'] in source['url'] and len(source['body']) > 100
                   for source in event['primary_sources'])
    amd = candidates['amd-world-labs-agreement']
    assert amd['relation'] == 'adjacent' and amd['state'] == 'developing'
    assert any('AMD' not in source['query'] and 'World Labs' not in source['query']
               and 'acquisition' in source['query'] for source in amd['discovery_sources'])
    assert len(amd['primary_sources']) == 3
    assert 'amd-world-labs-agreement' in load_json(ROOT / 'runs/2026-W40/editorial_audit.json')['suggested_top_stories']


def test_unknown_entity_and_date_stay_on_desk(tmp_path):
    import shutil

    shutil.copytree(ROOT / 'config', tmp_path / 'config')
    path = tmp_path / 'results.json'
    records = [
        {'title': 'UnlistedCo acquires spatial intelligence world model team', 'url': 'https://example.com/deal?utm_source=test', 'snippet': 'compute investment'},
        {'title': 'Same entity different deal', 'url': 'https://example.com/deal2', 'event_date': '2026-09-24'},
        {'title': 'Future', 'url': 'https://example.com/future', 'event_date': '2026-10-05'},
        {'title': 'Old', 'url': 'https://example.com/old', 'event_date': '2026-09-20'},
        {'title': 'Bad URL', 'url': 'file:///secret'},
        {'title': 'Valid after bad result', 'url': 'https://example.com/last'},
    ]
    write_json(path, {'queries': [{'query': 'spatial intelligence acquisition', 'category': 'capital', 'results': records},
                               {'query': '官方原文导航', 'category': 'capital', 'query_type': 'source_navigation', 'results': []}]})
    result = discover(tmp_path, tmp_path, START, END, results_files=[path], week=WEEK)
    items = load_json(tmp_path / 'data/discovery/2026-W40.json')
    assert len(items) == 3 and result['queries'][0]['out_of_window'] == 2
    assert result['queries'][0]['errors'] and ['capital', 'zh'] in result['missing_open_coverage']
    assert items[0]['relation'] == 'adjacent' and items[0]['event_date'] is None
    assert all(c['verification'] == 'unconfirmed' for c in items)
    with pytest.raises(ValueError, match='14 inclusive'):
        discover(tmp_path, tmp_path, END, END, results_files=[path])


def test_url_dedup_preserves_semantic_parameters():
    assert lead_id('https://example.com/a?utm_source=x#top') == lead_id('https://example.com/a/')
    assert canonical_url('https://example.com/a?version=2&_bhlid=tracking') == 'https://example.com/a?version=2'
    assert lead_id('https://example.com/a?version=1') != lead_id('https://example.com/a?version=2')


def test_same_tracker_does_not_merge_distinct_curated_events(tmp_path):
    from embodied_observatory.discovery import DiscoverySource

    source = DiscoverySource(title='Index', url='https://example.com/index', query='news', category='products')
    events = [NewsCandidate(id=ident, title=ident, categories=['products'], event_ref='event:' + ident,
                            discovery_sources=[source]) for ident in ('first-event', 'second-event')]
    path = tmp_path / 'review.json'
    write_json(path, [{'id': 'first-event', 'reviewer': 'codex_review', 'discovery_urls': [source.url]}])
    assert len(apply_reviews(events, path, END)) == 2


def test_importance_does_not_confirm_evidence():
    event = NewsCandidate(id='unconfirmed-major', title='Potential acquisition', categories=['capital'],
                          scores={name: 5 for name in config(ROOT, 'editorial_scoring')['weights']},
                          score_reasons={name: 'test importance reason' for name in config(ROOT, 'editorial_scoring')['weights']})
    scored = score_event(event, config(ROOT, 'editorial_scoring'), END)
    assert scored.proposed_tier == 'S' and scored.verification == 'unconfirmed' and scored.event_date is None


@pytest.mark.parametrize('command', ['edition', 'report', 'publish'])
def test_pending_selection_blocks_every_formal_entry(editorial_workspace, command):
    root = editorial_workspace
    args = ['--root', str(root), command, '--week', WEEK]
    if command != 'publish':
        args += ['--issue-file', str(issue_path(root)), '--selection', str(selection_path(root)), '--archive']
    else:
        args += ['--reviewed']
    assert main(args) == 2
    assert not (root / 'site').exists() and not (root / 'reports').exists()


def test_approved_selection_order_controls_render(editorial_workspace):
    root = editorial_workspace
    change_selection(root, lambda selection: [row.update(order=6-row['order']) for row in selection['top_stories']])
    approve_fixture(root)
    result = build_edition(root, root, WEEK, issue_path(root), archive=True)
    from bs4 import BeautifulSoup

    soup = BeautifulSoup((root / 'site/index.html').read_text(encoding='utf-8'), 'html.parser')
    assert soup.select_one('.top-story h3').get_text().startswith('Intrinsic Core')
    assert result['top_stories'] == 5 and result['model_api_calls'] == 0
    assert result['editorial_gate']['mode'] == 'approved'
    assert publish(root, WEEK, True).exists()


@pytest.mark.parametrize('target', ['issue', 'selection', 'audit', 'source'])
def test_approval_cannot_survive_changed_evidence_or_copy(editorial_workspace, target):
    root = editorial_workspace
    approve_fixture(root)
    if target == 'selection':
        change_selection(root, lambda selection: selection['top_stories'][0].update(reason='changed after review'))
    else:
        paths = {'issue': issue_path(root), 'audit': root/'runs/2026-W40/EDITORIAL_AUDIT.md',
                 'source': root/'data/major_events.json'}
        path = paths[target]
        path.write_bytes(path.read_bytes() + b'\n')
    with pytest.raises(ValueError):
        build_edition(root, root, WEEK, issue_path(root), archive=True)
    assert not (root / 'site').exists()


def test_s_news_requires_selection_or_explained_exception(editorial_workspace):
    root = editorial_workspace
    change_selection(root, lambda selection: selection['top_stories'].pop(0))
    with pytest.raises(ValueError, match='recent S event'):
        validate_selection(root, WEEK, None, issue_path(root), preview=True)
    change_selection(root, lambda selection: selection['s_tier_exceptions'].append(
        {'id': 'amd-world-labs-agreement', 'reason': 'Synthetic fixture: editor explicitly chooses briefing.'}))
    validate_selection(root, WEEK, None, issue_path(root), preview=True)


def test_unverified_story_cannot_pass_gate(editorial_workspace):
    root = editorial_workspace
    candidates = load_json(root / 'runs/2026-W40/news_candidates.json')
    unknown = next(c['id'] for c in candidates if c['verification'] == 'unconfirmed')
    change_selection(root, lambda selection: selection['briefing'].append({'id': unknown, 'selected': True}))
    with pytest.raises(ValueError, match='unverified'):
        validate_selection(root, WEEK, None, issue_path(root), preview=True)


def test_pending_preview_isolated_and_missing_audit_blocks(editorial_workspace, tmp_path):
    root = editorial_workspace
    before = {str(p): digest(p) for p in root.rglob('*') if p.is_file()}
    preview = root.parent / (root.name + '-preview')
    result = build_edition(root, preview, WEEK, issue_path(root), archive=True, dry_run=True)
    assert result['status'] == 'selection_preview' and not (preview/'reports').exists()
    assert before == {str(p): digest(p) for p in root.rglob('*') if p.is_file()}
    with pytest.raises(ValueError, match='isolated'):
        build_edition(root, root, WEEK, issue_path(root), dry_run=True)
    (root / 'runs/2026-W40/editorial_audit.json').unlink()
    with pytest.raises(FileNotFoundError):
        build_edition(root, preview, WEEK, issue_path(root), dry_run=True)
