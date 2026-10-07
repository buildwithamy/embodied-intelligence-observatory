"""Open bilingual discovery. Search hits are leads, never verified event evidence."""
from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import http_url, utcnow
from .pipeline import config, load_json, validate_week, week_id, write_json
from .ranking import matches


class DiscoverySource(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str
    url: str
    query: str
    category: str
    snippet: str = ''
    published_at: date | None = None
    source_kind: Literal['official', 'media', 'community', 'unknown'] = 'unknown'
    _url = field_validator('url')(http_url)


class NewsCandidate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(pattern=r'^[a-z0-9][a-z0-9-]{1,120}$')
    title: str = Field(min_length=1)
    event_date: date | None = None
    categories: list[str]
    entities: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    discovery_sources: list[DiscoverySource] = Field(default_factory=list)
    relation: Literal['direct', 'adjacent', 'weak', 'unknown'] = 'unknown'
    verification: Literal['unconfirmed', 'confirmed', 'contradicted'] = 'unconfirmed'
    verification_note: str = ''
    primary_sources: list[dict] = Field(default_factory=list)
    event_ref: str = ''
    origin: Literal['open_discovery', 'memory', 'manual_tip'] = 'open_discovery'
    summary: str = ''
    why_it_matters: str = ''
    application_areas: list[str] = Field(default_factory=list)
    confidence: Literal['low', 'medium', 'high'] = 'low'
    scores: dict[str, float] = Field(default_factory=dict)
    score_reasons: dict[str, str] = Field(default_factory=dict)
    score: float = 0
    proposed_tier: Literal['S', 'A', 'B'] = 'B'
    score_method: str = 'provisional_rules'
    reviewer: str = ''
    state: Literal['new', 'developing', 'stable', 'resolved', 'archived'] = 'new'
    what_changed_since_last_issue: str = ''


def canonical_url(url: str) -> str:
    http_url(url)
    p = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(p.query)
             if not k.casefold().startswith('utm_') and k.casefold() not in {'trk', 'fbclid', 'gclid', '_bhlid'}]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip('/'), urlencode(query), ''))


def lead_id(url: str) -> str:
    return 'news-' + hashlib.sha256(canonical_url(url).encode()).hexdigest()[:16]


def query_plan(root: Path, start: date, end: date) -> list[dict]:
    queries = config(root, 'discovery_queries')
    plan = []
    for category, languages in queries.items():
        for language in ('en', 'zh'):
            if not languages.get(language):
                raise ValueError(f'{category} needs both English and Chinese open queries')
            for query in languages[language]:
                plan.append({'query': query, 'category': category, 'language': language,
                             'scope': 'open', 'time_window': [start.isoformat(), end.isoformat()]})
    # Watchlist adds minimum entity coverage without replacing open-category queries.
    for group, entities in config(root, 'entity_watchlist').items():
        for entity in entities:
            plan.append({'query': f'"{entity["name"]}" robotics physical AI news',
                         'category': {'foundation_models': 'models', 'robot_companies': 'products',
                                      'education_policy': 'education'}.get(group, 'infrastructure'),
                         'language': 'en', 'scope': 'watchlist',
                         'time_window': [start.isoformat(), end.isoformat()]})
    return plan


def related(text: str, settings: dict) -> str:
    if any(matches(text, term) for term in settings['direct_terms']):
        return 'direct'
    if any(matches(text, term) for term in settings['adjacent_terms']):
        return 'adjacent'
    return 'unknown'  # Never discard a capital/strategic search result merely for no robot keyword.


def search_rss(client, query: str, start: date, end: date, maximum: int) -> list[dict]:
    expression = f'{query} after:{start.isoformat()} before:{(end + timedelta(days=1)).isoformat()}'
    raw = client.get_text('https://www.bing.com/search?' + urlencode({'q': expression, 'format': 'rss'}))
    tree = ET.fromstring(raw)
    if tree.tag != 'rss':
        raise ValueError('search response is not RSS (possible block or login wall)')
    return [{'title': item.findtext('title', ''), 'url': item.findtext('link', ''),
             'snippet': re.sub('<[^>]+>', ' ', item.findtext('description', '')),
             # RSS pubDate is search metadata; an editor must establish the event date.
             'event_date': None, 'published_at': None, 'source_kind': 'unknown'}
            for item in tree.findall('./channel/item')[:maximum]]


def discover(root: Path, output: Path, start: date, end: date, *, client=None,
             results_files: list[Path] | None = None, week: str | None = None):
    if (end - start).days != 13:
        raise ValueError('open discovery requires exactly 14 inclusive calendar days')
    week = validate_week(week or week_id(end))
    plan = query_plan(root, start, end)
    settings = config(root, 'editorial_scoring')
    imported = []
    if results_files:
        for path in results_files:
            imported.extend(load_json(path)['queries'])
        # Persist all real external tool queries rather than pretending they used the configured text.
        executions = [{**q, 'scope': ('source_navigation' if q.get('method') == 'source_link_follow_up'
                                    or q.get('query_type') == 'source_navigation' else q.get('scope', 'open')),
                       'language': q.get('language', 'zh' if re.search('[\u4e00-\u9fff]', q['query']) else 'en')}
                      for q in imported]
    else:
        if client is None:
            raise ValueError('live discovery needs an HTTP client')
        executions = plan
    items: dict[str, NewsCandidate] = {}
    logs = []
    for execution in executions:
        query, category = execution['query'], execution['category']
        log = {k: execution[k] for k in ('query', 'category', 'scope', 'language')}
        log.update(time_window=[start.isoformat(), end.isoformat()], results_seen=0,
                   candidates_added=0, duplicates=0, out_of_window=0, undated=0,
                   errors=list(execution.get('errors', [])), results=[])
        try:
            results = (execution.get('results', []) if results_files else
                       search_rss(client, query, start, end, settings['max_results_per_query']))
            for row in results:
                log['results_seen'] += 1
                try:
                    source = DiscoverySource(title=row['title'], url=canonical_url(row['url']), query=query,
                                         category=category, snippet=row.get('snippet', ''),
                                         published_at=row.get('published_at'),
                                         source_kind=row.get('source_kind', 'unknown'))
                    candidate_date = date.fromisoformat(row['event_date']) if row.get('event_date') else None
                except (ValueError, KeyError, TypeError) as exc:
                    log['errors'].append('invalid_result:' + type(exc).__name__)
                    continue
                log['results'].append({**source.model_dump(mode='json'), 'event_date': row.get('event_date')})
                if candidate_date is not None and not start <= candidate_date <= end:
                    log['out_of_window'] += 1
                    continue
                if candidate_date is None:
                    log['undated'] += 1
                ident = lead_id(source.url)
                if ident in items:
                    candidate = items[ident]
                    candidate.discovery_sources.append(source)
                    candidate.categories = sorted(set(candidate.categories + [category]))
                    candidate.entities = sorted(set(candidate.entities + row.get('entities', [])))
                    candidate.topics = sorted(set(candidate.topics + row.get('topics', [])))
                    if candidate.event_date is None:
                        candidate.event_date = candidate_date
                    elif candidate_date and candidate.event_date != candidate_date:
                        candidate.verification_note = '同一URL的线索日期冲突；保留检索记录，待编辑核对。'
                        candidate.event_date = None
                    log['duplicates'] += 1
                else:
                    items[ident] = NewsCandidate(id=ident, title=source.title, event_date=candidate_date,
                        categories=[category], entities=row.get('entities', []), topics=row.get('topics', []),
                        discovery_sources=[source], relation=related(source.title + ' ' + source.snippet, settings))
                    log['candidates_added'] += 1
        except Exception as exc:
            # Never dump transport URLs/headers or arbitrary exception strings into the public log.
            log['errors'].append(type(exc).__name__)
        logs.append(log)
    covered = {(row['category'], row['language']) for row in logs
               if row['scope'] == 'open' and not row['errors']}
    required = {(category, language) for category in config(root, 'discovery_queries') for language in ('en', 'zh')}
    manifest = {'schema_version': '0.4', 'week': week, 'run_time': utcnow().isoformat(),
                'mode': 'external_search_import' if results_files else ('offline_search_replay' if client.offline else 'bing_rss'),
                'date_range': [start.isoformat(), end.isoformat()], 'queries': logs,
                'query_plan': plan, 'missing_open_coverage': sorted([list(pair) for pair in required - covered]),
                'planned_watchlist_queries': sum(q['scope'] == 'watchlist' for q in plan),
                'executed_watchlist_queries': sum(q['scope'] == 'watchlist' for q in logs),
                'candidate_count': len(items), 'zero_results_queries': sum(r['results_seen'] == 0 for r in logs),
                'input_hashes': {str(p.resolve().relative_to(root.resolve())) if p.resolve().is_relative_to(root.resolve()) else str(p.resolve()):
                                hashlib.sha256(p.read_bytes()).hexdigest() for p in results_files or []},
                'limits': ['查询时间词不是事件日期证明；无日期结果保留待核验。',
                           '搜索未命中不能证明没有新闻；搜索摘要不得直接进入正式周刊。',
                           'Watchlist只是最低覆盖，开放发现不按已知公司过滤。']}
    write_json(output / 'runs' / week / 'discovery_log.json', manifest)
    write_json(output / 'data/discovery' / (week + '.json'), [c.model_dump(mode='json') for c in items.values()])
    return manifest
