"""Independent major-news scoring, audit and a hash-bound manual selection gate."""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .discovery import NewsCandidate, canonical_url
from .major_events import MajorEvent, load_events
from .models import utcnow
from .pipeline import config, load_json, validate_week, write_json


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selection_content_digest(selection: dict) -> str:
    import json

    content = {key: value for key, value in selection.items() if key != 'review'}
    return hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def issue_dates(week: str):
    validate_week(week)
    start = date.fromisocalendar(int(week[:4]), int(week[6:]), 1)
    end = start + timedelta(days=6)
    return end - timedelta(days=13), end


def score_event(candidate: NewsCandidate, settings: dict, end: date):
    weights = settings['weights']
    if abs(sum(weights.values()) - 1) > 1e-6 or any(w < 0 for w in weights.values()):
        raise ValueError('major-event weights must be nonnegative and sum to 1')
    if candidate.scores:
        if set(candidate.scores) != set(weights) or set(candidate.score_reasons) != set(weights):
            raise ValueError('every editorial score needs a separate reason')
        if any(not 0 <= value <= 5 for value in candidate.scores.values()):
            raise ValueError('major-event dimensions must be between 0 and 5')
    else:
        structural = 'capital' in candidate.categories
        platform = bool(set(candidate.categories) & {'models', 'infrastructure'})
        candidate.scores = dict(strategic_impact=4 if structural else 3 if platform else 2,
            cross_ecosystem_impact=4 if platform or structural else 2, event_scale=2,
            technical_significance=3 if platform else 2,
            evidence_quality=4 if candidate.verification == 'confirmed' else 1,
            freshness_momentum=4 if candidate.event_date and (end - candidate.event_date).days < 14 else 1)
        candidate.score_reasons = {k: '规则初筛，待编辑根据原文调整。' for k in weights}
    candidate.score = round(sum(candidate.scores[k] * weights[k] for k in weights) * 20, 2)
    # Importance is separate from evidence confidence. Unconfirmed potential S events remain on the desk.
    structural = max(candidate.scores['strategic_impact'], candidate.scores['cross_ecosystem_impact']) >= 4
    candidate.proposed_tier = ('S' if candidate.score >= settings['tier_thresholds']['S'] and structural else
                               'A' if candidate.score >= settings['tier_thresholds']['A'] else 'B')
    return candidate


def memory_candidate(event: MajorEvent) -> NewsCandidate:
    return NewsCandidate(id=event.id, title=event.title, event_date=event.last_updated,
        categories=[{'industry': 'deployment', 'technology': 'products'}.get(c, c) for c in event.categories],
        entities=[], relation='direct', verification='confirmed' if event.confirmed else 'unconfirmed',
        primary_sources=[s.model_dump(mode='json') for s in event.sources], event_ref='event:' + event.id,
        origin='memory', summary=event.summary, why_it_matters=event.why_it_matters,
        application_areas=event.application_scenarios, confidence='high' if event.confirmed else 'low',
        state=event.status, what_changed_since_last_issue=event.what_changed_since_last_issue)


def eligible(candidate: NewsCandidate, start: date, end: date) -> bool:
    return (candidate.verification == 'confirmed' and candidate.event_date is not None
            and start <= candidate.event_date <= end and candidate.relation in {'direct', 'adjacent'}
            and candidate.state != 'archived' and bool(candidate.primary_sources))


def apply_reviews(items: list[NewsCandidate], reviews_file: Path | None, end: date):
    if not reviews_file:
        return items
    known = {c.id: c for c in items}
    for row in load_json(reviews_file):
        row = dict(row)
        aliases = {canonical_url(url) for url in row.pop('discovery_urls', [])}
        ident = row['id']
        if ident not in known:
            raise ValueError('review references undiscovered candidate: ' + ident)
        if row.get('reviewer') not in {'codex_review', 'human_review'}:
            raise ValueError('news evidence review needs an identified reviewer')
        candidate = known[ident]
        for alias_id, lead in list(known.items()):
            if alias_id != ident and not lead.event_ref and any(canonical_url(s.url) in aliases for s in lead.discovery_sources):
                candidate.discovery_sources.extend(lead.discovery_sources)
                del known[alias_id]
        allowed = {'title', 'event_date', 'entities', 'topics', 'relation', 'verification', 'verification_note',
                   'primary_sources', 'event_ref', 'summary', 'why_it_matters', 'application_areas',
                   'confidence', 'scores', 'score_reasons', 'state', 'what_changed_since_last_issue', 'reviewer'}
        unknown = set(row) - allowed - {'id'}
        if unknown:
            raise ValueError('unknown news review fields: ' + ', '.join(sorted(unknown)))
        updated = NewsCandidate.model_validate({**candidate.model_dump(), **row,
                                                'score_method': 'editorial_evidence_review'})
        if updated.verification == 'confirmed':
            if not updated.primary_sources or not updated.event_date:
                raise ValueError('confirmation needs dated original source bodies')
            for source in updated.primary_sources:
                canonical_url(source['url'])
                if len(source.get('body', '')) < 20 or not source.get('published_at'):
                    raise ValueError('confirmation needs readable, dated source bodies')
                if date.fromisoformat(source['published_at']) > end:
                    raise ValueError('future verification source cannot enter historical issue')
            if updated.event_date.isoformat() not in {s['published_at'] for s in updated.primary_sources}:
                raise ValueError('event/update date must be supported by original sources')
        known[ident] = updated
    return list(known.values())


def safe_cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def source_text(sources):
    return '; '.join(f'[{safe_cell(s["title"])}]({s["url"]})' for s in sources) or '未找到；不得作为已核验新闻发布'


def audit(root: Path, output: Path, week: str, *, reviews_file: Path | None = None):
    start, end = issue_dates(week)
    directory = output / 'runs' / week
    discovery_path = root / 'data/discovery' / (week + '.json')
    log_path = root / 'runs' / week / 'discovery_log.json'
    discovery = load_json(log_path)
    if discovery['week'] != week or discovery['date_range'] != [start.isoformat(), end.isoformat()]:
        raise ValueError('discovery window must match the issue 14-day cutoff')
    items = [NewsCandidate.model_validate(c) for c in load_json(discovery_path)]
    settings = config(root, 'editorial_scoring')
    memory = [e for e in load_events(root / 'data/major_events.json')
              if 0 <= (end - e.event_date).days < settings['memory_days']
              and e.last_updated <= end and all(s.published_at <= end for s in e.sources)]
    # Merge search hits with memory by original-source URL, keeping all discovery provenance.
    for event in memory:
        urls = {canonical_url(s.url) for s in event.sources}
        hits = [c for c in items if any(canonical_url(s.url) in urls for s in c.discovery_sources)]
        converted = memory_candidate(event)
        for hit in hits:
            converted.discovery_sources.extend(hit.discovery_sources)
            converted.categories = sorted(set(converted.categories + hit.categories))
            items.remove(hit)
        items.append(converted)
    items = apply_reviews(items, reviews_file, end)
    items = [score_event(c, settings, end) for c in items]
    recent = [c for c in items if c.event_date is None or start <= c.event_date <= end]
    recent.sort(key=lambda c: (not eligible(c, start, end), -c.score, c.id))
    remembered = sorted([c for c in items if c.event_date and c.event_date < start], key=lambda c: (-c.score, c.id))
    usable = [c for c in recent if eligible(c, start, end)
              and c.proposed_tier in {'S', 'A'} and c.score >= settings['top_story_min_score']]
    proposed = sorted(usable, key=lambda c: (c.proposed_tier != 'S', -c.score, c.id))[:5]
    previous_path = root / 'runs' / (week + '-major-news-audit.json')
    previous_ids = set(load_json(previous_path).get('confirmed_events', [])) if previous_path.exists() else set()
    missed = [c for c in items if c.verification == 'confirmed' and c.discovery_sources and c.state != 'archived'
              and c.event_ref.removeprefix('event:') not in previous_ids]
    # The review desk is intentionally short. Full raw queues and scores remain in JSON.
    reviewed = [c for c in items if c.reviewer or c.verification == 'confirmed']
    pending_important = sorted([c for c in items if c.verification != 'confirmed'],
                               key=lambda c: (-c.score, c.id))[:10]
    rejected = [c for c in reviewed + pending_important if c not in proposed]
    rows = [f'# {week} Editorial Audit', '', f'开放发现：{start}～{end}；重大记忆：{end - timedelta(days=59)}～{end}。',
            '', '先发现，再核验；以下分级为编辑建议，不能代替人工确认选题。', '', '## 1. 最近 14 天 Top 15 候选', '',
            '| Rank | Title | Date（事件/最近实质更新） | Category | Entity | Tier / Score | Why it may matter | Primary source | Discovery sources | Applications | Confidence / Verification |',
            '|---|---|---|---|---|---|---|---|---|---|---|']
    for rank, c in enumerate(recent[:15], 1):
        values = [rank, c.title, c.event_date or '日期待核验', ', '.join(c.categories), ', '.join(c.entities) or '待补充',
                  f'{c.proposed_tier} / {c.score:g}', c.why_it_matters or '待核验重要性；检索命中不等于已发生',
                  source_text(c.primary_sources), source_text([s.model_dump() for s in c.discovery_sources]),
                  ', '.join(c.application_areas) or '待评估', f'{c.confidence} / {c.verification}']
        rows.append('| ' + ' | '.join(safe_cell(v) for v in values) + ' |')
    if len(recent) < 15:
        rows += ['', f'仅有 {len(recent)} 条可追踪候选，未补造新闻以凑满 15 条。']
    rows += ['', '## 2. 最近 30–60 天仍需记住的事件', '', '| 事件 | Tier | 状态 | 本期更新 | 建议 |', '|---|---|---|---|---|']
    for c in remembered:
        rows.append('| ' + ' | '.join(safe_cell(v) for v in (c.title, c.proposed_tier, c.state,
            c.what_changed_since_last_issue or '无已核实新进展', '保留背景；不冒充两周内新发布' if c.proposed_tier != 'B' else '资源索引 / 降级')) + ' |')
    rows += ['', '## 3. 可能被遗漏的大新闻 / 本轮补入', '']
    for c in missed:
        rows += [f'- **{c.title}**（`{c.id}`）：{c.why_it_matters} {source_text(c.primary_sources)}']
    if not missed:
        rows += ['本轮尚无核验通过的新补入事件；不据此宣称旧流程没有遗漏。']
    pending_reviewed = [c for c in reviewed if c.verification == 'unconfirmed']
    if pending_reviewed:
        rows += ['', '### 重要待核验线索（仍留编辑桌，不进正式正文）', '']
        rows += [f'- **{c.title}**：{c.why_it_matters} {c.verification_note}' for c in pending_reviewed]
    rows += ['', '### 发现覆盖与盲区', '',
             f'- 尚未成功覆盖的中英类别：{discovery["missing_open_coverage"] or "无（代表执行查询，不代表全网召回完整）"}',
             f'- Watchlist 查询执行 {discovery["executed_watchlist_queries"]}/{discovery["planned_watchlist_queries"]}；开放查询不受其限制。',
             f'- 返回零结果的查询：{discovery["zero_results_queries"]}。',
             '- 付费墙、社交平台、地域与索引延迟仍会漏新闻。检索日期与事件日期分别保存。', '', '## 4. 建议进入本期首页的 Top 5', '']
    for rank, c in enumerate(proposed, 1):
        rows += [f'### Top {rank} · {c.title}', '', f'`{c.id}` · {c.proposed_tier} · {c.score:g}', '',
                 c.why_it_matters, '', f'原文核验：{c.verification_note or "已有原文证据；数据与结论仍归属于披露方。"}', '']
    rows += ['## 5. 建议降级 / 排除的重要候选', '', '| Candidate | Decision | Reason |', '|---|---|---|']
    for c in rejected:
        reason = (c.verification_note or '缺少可核验原文/日期') if c.verification != 'confirmed' else (
            '已超过14天；保留重大记忆或作为背景' if c.event_date and c.event_date < start else
            '重要性低于首页候选；放速读/行业/论文区，不以栏目配额占首页')
        rows.append('| ' + ' | '.join(safe_cell(v) for v in (c.title, 'exclude' if c.verification != 'confirmed' else 'downgrade', reason)) + ' |')
    rows += ['', '## 6. 评分证据', '']
    rows += ['完整待核验队列与逐项评分见 [news_candidates.json](news_candidates.json)；未核验线索不进入正式周刊。', '']
    for c in sorted(reviewed, key=lambda c: (-c.score, c.id)):
        rows += [f'### {c.title} (`{c.id}`)', '']
        rows += [f'- {name}: {value:g}/5 — {c.score_reasons[name]}' for name, value in c.scores.items()]
        rows += ['']
    directory.mkdir(parents=True, exist_ok=True)
    audit_path = directory / 'EDITORIAL_AUDIT.md'
    audit_path.write_text('\n'.join(rows), encoding='utf-8')
    candidate_path = directory / 'news_candidates.json'
    write_json(candidate_path, [c.model_dump(mode='json') for c in items])
    event_path = directory / 'major_event_snapshot.json'
    write_json(event_path, [e.model_dump(mode='json') for e in memory])
    inputs = [discovery_path, log_path, root / 'data/major_events.json', root / 'config/editorial_scoring.yaml',
              root / 'config/discovery_queries.yaml', root / 'config/entity_watchlist.yaml']
    if previous_path.exists():
        inputs.append(previous_path)
    for path, expected in discovery.get('input_hashes', {}).items():
        source = (root / path).resolve()
        if not source.is_relative_to(root.resolve()) or digest(source) != expected:
            raise ValueError('search export changed or is outside the workspace; rerun discover')
        inputs.append(source)
    if reviews_file:
        inputs.append(reviews_file)
    planned_watchlist = {q['query'] for q in discovery['query_plan'] if q['scope'] == 'watchlist'}
    executed_watchlist = {q['query'] for q in discovery['queries'] if q['scope'] == 'watchlist' and not q['errors']}
    watchlist_complete = planned_watchlist <= executed_watchlist
    manifest = {'schema_version': '0.4', 'week': week, 'date_range': [start.isoformat(), end.isoformat()],
        'input_hashes': {str(p.resolve().relative_to(root.resolve())): digest(p) for p in inputs},
        'audit_sha256': digest(audit_path), 'candidates_sha256': digest(candidate_path),
        'event_snapshot_sha256': digest(event_path), 'suggested_top_stories': [c.id for c in proposed],
        'new_confirmed_candidates': [c.id for c in missed], 'candidate_count': len(items),
        'recent_candidate_count': len(recent),
        'coverage_complete': not discovery['missing_open_coverage'] and watchlist_complete,
        'watchlist_coverage_complete': watchlist_complete,
        'status': 'awaiting_manual_selection', 'run_time': utcnow().isoformat()}
    write_json(directory / 'editorial_audit.json', manifest)
    selection_path = directory / 'editorial_selection.yaml'
    if not selection_path.exists():
        selection = {'issue': week, 'audit_sha256': manifest['audit_sha256'],
            'review': {'status': 'pending', 'reviewer': '', 'reviewed_at': '', 'issue_sha256': ''},
            'top_stories': [{'id': c.id, 'selected': True, 'tier': c.proposed_tier, 'order': n,
                             'story_id': '', 'reason': c.why_it_matters} for n, c in enumerate(proposed, 1)],
            'briefing': [{'id': c.id, 'selected': True} for c in recent if eligible(c, start, end)],
            'recent_major': [{'id': c.id, 'selected': True} for c in items
                             if eligible(c, end - timedelta(days=59), end) and c.proposed_tier != 'B'],
            'exclude': [{'id': c.id, 'reason': c.verification_note or '未完成事实核验/不相关'}
                        for c in items if c.verification != 'confirmed'],
            's_tier_exceptions': []}
        selection_path.write_text(yaml.safe_dump(selection, allow_unicode=True, sort_keys=False), encoding='utf-8')
    manual_path = directory / 'manual_major_news_check.yaml'
    previous_manual = yaml.safe_load(manual_path.read_text(encoding='utf-8')) if manual_path.exists() else {}
    prior_checks = {row['id']: row for row in previous_manual.get('known_major_events', [])}
    manual = {'issue': week, 'measurement': 'bounded_manual_reference_set_not_global_recall',
            'known_major_events': [{'id': c.id, 'title': c.title,
                'found_by_pipeline': bool(c.discovery_sources),
                'final_selected': prior_checks.get(c.id, {}).get('final_selected'),
                'discovery_origin': 'open_search' if c.discovery_sources else 'previous_memory'}
                for c in items if c.verification == 'confirmed'],
            'missed_events': previous_manual.get('missed_events', []),
            'limits': '真实外部检索导入与历史记忆的有限参考集，不是无人自动发现的召回率。'}
    manual_path.write_text(yaml.safe_dump(manual, allow_unicode=True, sort_keys=False), encoding='utf-8')
    return manifest


class SelectionItem(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str
    selected: bool = True
    tier: str | None = None
    order: int | None = Field(default=None, ge=1)
    story_id: str = ''
    reason: str = ''


def validate_selection(root: Path, week: str, selection_file: Path | None, issue_file: Path,
                       *, preview=False):
    """No writes before validation. A pending selection may only produce an explicit dry-run preview."""
    if selection_file is None:
        selection_file = root / 'runs' / week / 'editorial_selection.yaml'
    selection = yaml.safe_load(selection_file.read_text(encoding='utf-8'))
    if selection.get('issue') != week:
        raise ValueError('selection issue mismatch')
    directory = root / 'runs' / week
    manifest = load_json(directory / 'editorial_audit.json')
    if manifest['week'] != week or manifest['date_range'] != [d.isoformat() for d in issue_dates(week)]:
        raise ValueError('audit issue/cutoff mismatch')
    for path, expected in manifest['input_hashes'].items():
        resolved = (root / path).resolve()
        if not resolved.is_relative_to(root.resolve()) or digest(resolved) != expected:
            raise ValueError('audit inputs changed; run audit again')
    for filename, key in [('EDITORIAL_AUDIT.md', 'audit_sha256'), ('news_candidates.json', 'candidates_sha256'),
                          ('major_event_snapshot.json', 'event_snapshot_sha256')]:
        if digest(directory / filename) != manifest[key]:
            raise ValueError('audited artifact changed; run audit again')
    if selection.get('audit_sha256') != manifest['audit_sha256']:
        raise ValueError('selection refers to a stale audit')
    review = selection.get('review', {})
    if not preview and (review.get('status') != 'approved' or not review.get('reviewer')
                        or not review.get('reviewed_at') or review.get('issue_sha256') != digest(issue_file)
                        or review.get('selection_sha256') != selection_content_digest(selection)):
        raise ValueError('manual selection approval required for this exact editorial file; use --dry-run for preview')
    if not preview:
        try:
            reviewed_at = datetime.fromisoformat(review['reviewed_at'])
            if reviewed_at.tzinfo is None or reviewed_at > utcnow():
                raise ValueError('invalid review time')
        except (TypeError, ValueError) as exc:
            raise ValueError('human review timestamp must be a valid, nonfuture time with timezone') from exc
    candidates = {c.id: c for c in (NewsCandidate.model_validate(c) for c in load_json(directory / 'news_candidates.json'))}
    start, end = issue_dates(week)
    excluded_rows = selection.get('exclude', [])
    exclude = {row['id'] for row in excluded_rows}
    if len(exclude) != len(excluded_rows) or any(ident not in candidates for ident in exclude):
        raise ValueError('excluded IDs must be known and unique')
    if any(not row.get('reason', '').strip() for row in excluded_rows):
        raise ValueError('excluded events need an editorial reason')
    groups = {}
    for group in ('top_stories', 'briefing', 'recent_major'):
        rows = [SelectionItem.model_validate(row) for row in selection.get(group, [])]
        selected = [r for r in rows if r.selected]
        if len({r.id for r in selected}) != len(selected):
            raise ValueError('duplicate selection ID in ' + group)
        for row in selected:
            if row.id not in candidates or row.id in exclude:
                raise ValueError('unknown or excluded selection ID: ' + row.id)
            candidate = candidates[row.id]
            if not eligible(candidate, end - timedelta(days=59), end):
                raise ValueError('unverified, undated, future or unrelated candidate cannot be selected: ' + row.id)
            if group == 'top_stories':
                if candidate.proposed_tier not in {'S', 'A'} or candidate.score < config(root, 'editorial_scoring')['top_story_min_score']:
                    raise ValueError('Top Story needs S or high A importance')
                if not row.story_id or row.order is None or not row.reason:
                    raise ValueError('Top Story requires story_id, order and an editorial reason')
                if row.tier != candidate.proposed_tier:
                    raise ValueError('selection tier must match audited editorial scoring')
        groups[group] = selected
    top = groups['top_stories']
    if len(top) > 5 or len({r.order for r in top}) != len(top) or len({r.story_id for r in top}) != len(top):
        raise ValueError('Top Story ordering/identity must be unique with at most five selections')
    if not top:
        raise ValueError('select at least one Top Story before rendering')
    exceptions = {r['id']: r['reason'] for r in selection.get('s_tier_exceptions', []) if r.get('reason')}
    selected_ids = {r.id for r in top}
    for c in candidates.values():
        if eligible(c, start, end) and c.proposed_tier == 'S' and c.id not in selected_ids and c.id not in exceptions:
            raise ValueError('recent S event needs homepage selection or explicit exception: ' + c.id)
    if not manifest['coverage_complete'] and not selection.get('coverage_exception'):
        raise ValueError('incomplete discovery/watchlist coverage needs a recorded editorial exception')
    issue = load_json(issue_file)
    stories = {s['id']: s for s in issue['stories']}
    for row in top:
        if row.story_id not in stories:
            raise ValueError('selected story lacks reviewed editorial copy: ' + row.story_id)
        ref = candidates[row.id].event_ref
        if not ref or ref not in stories[row.story_id]['refs']:
            raise ValueError('story does not cite selected event evidence: ' + row.id)
    return selection, groups, candidates, manifest


def approve_selection(root: Path, week: str, path: Path, issue_file: Path, reviewer: str, reviewed: bool):
    if not reviewed or not reviewer.strip():
        raise ValueError('review-selection requires --reviewed and a named human reviewer')
    selection, _, _, _ = validate_selection(root, week, path, issue_file, preview=True)
    selection['review'] = {'status': 'approved', 'reviewer': reviewer.strip(),
                           'reviewed_at': utcnow().isoformat(), 'issue_sha256': digest(issue_file),
                           'selection_sha256': selection_content_digest(selection)}
    path.write_text(yaml.safe_dump(selection, allow_unicode=True, sort_keys=False), encoding='utf-8')
    return {'issue': week, 'status': 'approved', 'selection': str(path)}
