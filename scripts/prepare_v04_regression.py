"""One-time W40 source curation from recorded search/primary reads, never a discovery rule."""
import json
import re
from pathlib import Path

from embodied_observatory.discovery import canonical_url, lead_id
from embodied_observatory.major_events import MajorEvent
from embodied_observatory.pipeline import load_json, write_json

ROOT = Path(__file__).resolve().parents[1]
DIMENSIONS = ('strategic_impact', 'cross_ecosystem_impact', 'event_scale',
              'technical_significance', 'evidence_quality', 'freshness_momentum')


def main():
    first = load_json(ROOT / 'data/research/v04-capital-models.json')
    second = load_json(ROOT / 'data/research/v04-other-discovery.json')
    blobs = [*first['source_readings'].values(), *[r['content'] for r in second['raw_page_reads']]]
    blobs.append((ROOT / 'data/research/v04-late-capital-primary-reads.txt').read_text(encoding='utf-8'))
    followup = load_json(ROOT / 'data/research/v04-models-followup.json')
    blobs.extend(r['raw_response'] for r in followup['source_readings'])
    readings = {}
    for blob in blobs:
        headers = list(re.finditer(r'(?m)^([^\n]+) \((https?://[^\n)]+)\)\n(?=[\ue200\ue202])', blob))
        for n, header in enumerate(headers):
            raw = blob[header.end():headers[n + 1].start() if n + 1 < len(headers) else len(blob)]
            lines = re.findall(r'(?m)^L\d+: ?(.*)$', raw)
            body = '\n'.join(lines) if lines else raw
            # Remove tool citation identifiers, retaining actual original source text.
            body = re.sub(r'[\ue200].*?[\ue201]', '', body)
            url = canonical_url(header.group(2))
            if url not in readings or len(body) > len(readings[url]['body']):
                readings[url] = {'title': header.group(1), 'url': header.group(2), 'body': body.strip()}
    curated = list(first['reviews'])
    curated.extend(load_json(ROOT / 'data/research/v04-late-capital-reviews.json'))
    for item in curated:
        if item['id'] == 'amd-world-labs-agreement':
            item['discovery_sources'].append('https://www.itpro.com/business/acquisition/amd-to-acquire-another-ai-software-firm-world-labs')
    for r in second['reviews']:
        if r['id'] in {'msr-inference-offloading-20260923', 'humanoid-standard-part5-20260928'}:
            continue
        curated.append({'id': r['id'], 'title': r['title'], 'category': r['category'],
            'event_date': r['event_date'], 'published_at': r['published_at'],
            'primary_sources': [r['url']], 'official_verified': r['status'] == 'verified_primary',
            'proposed_tier': r['editorial_priority'], 'facts': r['facts'], 'limits': r['constraints'],
            'summary': r['summary'], 'entities': [], 'topics': [], 'discovery_sources': [r['url']],
            'confidence': 'high' if r['status'] == 'verified_primary' else 'low',
            'related_application_areas': []})
    backup = ROOT / 'data/editorial/history/2026-W40-major-events-before-v04.json'
    if not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes((ROOT / 'data/major_events.json').read_bytes())
    original = load_json(backup)
    previous = {e['id']: e for e in load_json(ROOT / 'data/major_events.json')}
    events = {e['id']: e for e in original}
    reviews = []
    high_scores = {
        'qualcomm-picknik-agreement-20260923': (4, 5, 2, 4, 4, 5),
        'cognex-realsense-agreement-20260922': (4, 4, 3, 3, 5, 5),
        'sima-series-c-20260928': (3, 3, 3, 3, 4, 5),
        'skild-s1-date-conflict': (4, 4, 3, 4, 4, 1),
        'worldlabs-atlas-context': (4, 4, 2, 4, 4, 2),
        'amd-world-labs-agreement': (5, 5, 5, 4, 5, 5),
        'microsoft-offloaded-physical-ai-inference': (4, 4, 2, 4, 4, 5),
        'bfl-flux3-action': (4, 4, 3, 4, 4, 5),
        'lightorigins-light-o1': (4, 3, 2, 4, 4, 5),
        'intrinsic-core-20260922': (4, 4, 2, 4, 4, 5),
        'humanoid-task-manipulation-standard-2026': (3, 4, 3, 3, 4, 5),
        'agility-digit5-cooperative-safety': (3, 3, 3, 4, 4, 4),
        'boston-atlas-rmac-manufacturing': (3, 3, 3, 4, 4, 4),
        'agibot-chimelong-service-deployment': (3, 3, 4, 3, 3, 5),
        'isaac-ros-5-agent-workflows': (3, 3, 2, 4, 4, 5),
        'isaac-lab-3-early-access': (4, 4, 2, 4, 4, 2),
        'figure-helix-25-unseen-homes': (4, 4, 3, 5, 3, 2),
        'skild-commercial-deployment-revenue': (2, 2, 3, 1, 3, 1),
        'rlark-20260924': (3, 3, 2, 4, 4, 5),
        'rpent-20260921': (3, 3, 2, 3, 4, 5),
        'skild-physical-self-play': (3, 3, 2, 4, 3, 5),
        'sharpa-d01-w02-ae01-20260928': (2, 3, 2, 4, 3, 5),
        'perceptron-mk15': (2, 3, 2, 3, 3, 5),
        'robochrono-20260929': (2, 2, 2, 3, 4, 5),
        'viam-boxbot-20260922': (2, 2, 2, 3, 4, 5),
        'cmedc-embodied-program-20260922': (2, 2, 2, 2, 4, 5),
        'school-rl-curriculum-20260922': (2, 2, 2, 2, 4, 5),
    }
    rationales = {
        'qualcomm-picknik-agreement-20260923': ('芯片平台厂商拟整合机器人操作框架维护者。', 'MoveIt、ROS、Dragonwing与Arduino连接多个开发生态。', '未披露交易金额，不按未知金额加分。', '可影响规划、操作与端侧推理的集成路径，但暂无新性能对照。', '高通原文和OSRA公告可查；开源承诺是未来安排。', '9/23公告，仍待交割与后续集成。'),
        'cognex-realsense-agreement-20260922': ('工业机器视觉厂商拟扩展到机器人深度感知。', '涵盖工业视觉、AMR、人形机器人和开发者平台。', '约5亿美元拟收购对价，规模明确。', '本轮主要为能力与渠道整合，没有新算法或闭环性能实测。', '投资者关系原文含对价、交割条件与业务分拆。', '9/22新增协议，预计Q4交割仍待跟踪。'),
        'sima-series-c-20260928': ('为端侧physical AI芯片与软件继续筹资。', '涉及机器人、汽车和无人机，影响仍集中于本平台。', '本轮1.5亿美元，累计5亿美元，估值14.5亿美元分别记录。', '硬件目标在2028年，当前融资不当作性能发布。', '公司融资公告可查，商业增长未经独立审计。', '9/28披露新融资，后续产品与部署仍待核验。'),
        'amd-world-labs-agreement': ('头部算力厂商拟整合空间模型研究团队，涉及产业链位置。', '连接空间模型、算力、仿真与开放生态。', '8-K确认约82亿美元全股票交易；规模大但待交割。', '模型需求可影响计算路线图，机器人收益尚未实测。', 'AMD、World Labs双方公告及8-K相互支持。', '9/28公告，监管和交割是下一步跟踪点。'),
        'microsoft-offloaded-physical-ai-inference': ('改变机器人计算放在何处的系统选择。', '连接机器人、边缘/云GPU、ROS2与LeRobot。', '提供工作负载实验与示例，尚无大规模部署数量。', '闭环性能、续航和网络/GPU竞争有明确权衡。', '官方功能公告、公开工具和较早技术报告可查。', '9/23新增工具能力；不把3月报告算成新论文。'),
        'bfl-flux3-action': ('视频生成团队进入机器人动作模型，扩展模型参与者。', '视频预测、机器人动作、开放权重和LeRobot相连接。', '公开7B权重与适配路径，评测仍来自团队。', '联合未来视频与动作预测，提供可检验适配路径。', '开发者原文、官方模型页及代码；许可有限制。', '9/23发布，适配与评测可后续验证。'),
        'lightorigins-light-o1': ('人类动作预训练提供机器人数据之外的学习路径。', '连接人类视频、全身动作与跨本体适配。', '公开预训练规模和模拟评测，不是规模真机部署。', '缩放指标、模拟成功率与真机演示明确区分。', '原技术稿及公司供稿可查；未独立复现。', '9/21新发布，有Preview和代码供后续检查。'),
        'intrinsic-core-20260922': ('工业机器人的核心控制能力进一步公开。', 'ROS兼容运行时、数字孪生、控制和CNC方案连接。', '公开核心代码，暂不以未知用户规模加分。', '提供接近实际机加工任务的集成入口。', '官方发布与Apache2.0仓库可查；不是所有云服务免费。', '9/22正式发布，可以继续验证硬件适配。'),
    }
    for r in curated:
        if not r['official_verified'] or not r['event_date'] or r['event_date'] < '2026-08-06':
            continue
        if r['id'] == 'humanoid-standard-part1-20260928':
            # Same standard family; do not manufacture a second large policy event.
            existing = events['humanoid-task-manipulation-standard-2026']
            url = r['primary_sources'][0]
            source = {**readings[canonical_url(url)], 'published_at': r['published_at']}
            existing['sources'].append(source)
            existing['constraints'].append('同日第1部分总则合并为同一标准系列；仅核验元数据。')
            continue
        sources = []
        for url in r['primary_sources'][:3 if r['id'] == 'amd-world-labs-agreement' else 1]:
            key = canonical_url(url)
            if key not in readings:
                raise ValueError('Missing original reading snapshot: ' + url)
            sources.append({**readings[key], 'published_at': r['published_at']})
        if r['id'] == 'trinatracker-robots-20260924':
            url = 'https://www.prnewswire.com/news-releases/trinatracker-launches-two-robots-to-expand-its-smart-pv-ecosystem-302889010.html'
            sources.append({**readings[canonical_url(url)], 'published_at': '2026-09-24'})
        facts = r.get('summary') or ' '.join(r['facts'][:2])
        why = (r.get('recommendation') or '技术/应用线索，适合行业备忘。')
        if r['id'] in rationales:
            why = rationales[r['id']][0] + rationales[r['id']][1]
        payload = {'id': r['id'], 'title': r['title'], 'event_date': r['event_date'],
            'last_updated': r['published_at'], 'importance': r['proposed_tier'] if r['proposed_tier'] in {'S', 'A', 'B'} else 'B',
            'status': 'developing' if 'agreement' in r['id'] else ('stable' if r['published_at'] < '2026-09-21' else 'new'),
            'summary': facts, 'why_it_matters': why,
            'what_changed_since_last_issue': ('首次补入重大记忆，原发布早于两周窗口；近期媒体报道不刷新日期。'
                if r['published_at'] < '2026-09-21' else '首次补入W40独立开放发现；无上一期完整基线。'),
            'categories': [r['category']], 'application_scenarios': r['related_application_areas'],
            'sources': sources, 'constraints': r['limits'], 'confirmed': True}
        if r['id'] in previous:
            payload['first_seen'] = previous[r['id']]['first_seen']
        events[r['id']] = MajorEvent.model_validate(payload).model_dump(mode='json')
    write_json(ROOT / 'data/major_events.json', sorted(events.values(), key=lambda e: (e['event_date'], e['id'])))
    raw_by_id = {r['id']: r for r in curated}
    named_entities = {
        'figure-helix-25-unseen-homes': ['Figure'],
        'agility-digit5-cooperative-safety': ['Agility Robotics', 'FORT'],
        'agibot-chimelong-service-deployment': ['AGIBOT', 'Chimelong'],
        'boston-atlas-rmac-manufacturing': ['Boston Dynamics'],
        'isaac-ros-5-agent-workflows': ['NVIDIA'], 'isaac-lab-3-early-access': ['NVIDIA'],
        'humanoid-task-manipulation-standard-2026': ['国家市场监督管理总局', '国家标准化管理委员会'],
        'intrinsic-core-20260922': ['Intrinsic'], 'skild-physical-self-play': ['Skild AI'],
        'rlark-20260924': ['Infinigence'], 'rpent-20260921': ['Infinigence'],
        'viam-boxbot-20260922': ['Viam'], 'nota-npu-vla-20260922': ['Nota AI', 'Qualcomm'],
        'sharpa-d01-w02-ae01-20260928': ['Sharpa'], 'trinatracker-robots-20260924': ['TrinaTracker'],
    }
    for ident, event in events.items():
        if event['status'] == 'archived':
            continue
        r = raw_by_id.get(ident, {})
        values = high_scores.get(ident, (2, 2, 2, 3, 4, 4 if event['last_updated'] >= '2026-09-21' else 1))
        reasons = rationales.get(ident, (
            event['why_it_matters'], '影响范围限于所披露产品/平台，未证实全生态变化。',
            '按公开样本/部署/产品覆盖判断，未披露的规模不加分。',
            event['summary'], '已有官方原文；公司自报/元数据不当作独立复现。',
            '按原发布日期和实质更新日期判断；新媒体报道不自动刷新事件日期。'))
        reviews.append({'id': ident, 'reviewer': 'codex_review', 'scores': dict(zip(DIMENSIONS, values)),
            'score_reasons': dict(zip(DIMENSIONS, reasons)), 'entities': r.get('entities') or named_entities.get(ident, []),
            'topics': r.get('topics', []), 'relation': 'adjacent' if ident in {'amd-world-labs-agreement', 'worldlabs-atlas-context'} else 'direct',
            'verification_note': ' '.join(r.get('limits', event.get('constraints', []))),
            'discovery_urls': list(dict.fromkeys(r.get('discovery_sources', []) + [s['url'] for s in event['sources']])),
            'confidence': 'high'})
    # Explicit desk decisions for important date conflicts; they do not enter memory as new news.
    discovered = {c['id'] for c in load_json(ROOT / 'data/discovery/2026-W40.json')}
    for item in curated:
        if item['id'] not in {'skild-s1-date-conflict', 'gemini-er2-date-conflict'}:
            continue
        if item['id'] in events:
            continue  # Its aliases already merge into the dated historical memory event.
        ident = next((lead_id(url) for url in item['discovery_sources'] + item['primary_sources']
                      if lead_id(url) in discovered), '')
        if ident not in discovered:
            continue
        reviews.append({'id': ident, 'reviewer': 'codex_review', 'event_date': item['event_date'],
            'discovery_urls': item['discovery_sources'],
            'verification': 'contradicted', 'state': 'archived', 'confidence': 'high',
            'verification_note': '原文日期为' + item['event_date'] + '；近期媒体报道不是本期新发布。',
            'primary_sources': [{**readings[canonical_url(url)], 'published_at': item['event_date']}
                                for url in item['primary_sources'] if canonical_url(url) in readings],
            'scores': dict(zip(DIMENSIONS, (3, 3, 2, 4, 4, 1))),
            'score_reasons': dict(zip(DIMENSIONS, ('技术有背景意义。', '跨本体/平台学习路线。',
                '无新增规模事实。', '保留原文技术信息。', '原文日期可查。', '不在本期新发布窗口。')))})
    praxis = followup['reviews'][0]
    ident = lead_id(praxis['dated_secondary_urls'][0])
    if ident in discovered:
        source = readings[canonical_url(praxis['official_urls'][0])]
        reviews.append({'id': ident, 'title': 'Runway Praxis-1：技术原文可读，精确发布日期待核验',
            'reviewer': 'codex_review', 'entities': ['Runway'], 'relation': 'direct', 'event_date': None,
            'verification': 'unconfirmed', 'confidence': 'medium',
            'summary': ' '.join(praxis['claims_verified'][:2]),
            'why_it_matters': '视频预训练团队进入动作模型，但官方只标9月，不能强填为9/30。',
            'verification_note': praxis['date_verification'] + ' ' + ' '.join(praxis['wording_guardrails']),
            'primary_sources': [{**source, 'published_at': None}],
            'discovery_urls': praxis['dated_secondary_urls'],
            'scores': dict(zip(DIMENSIONS, (4, 4, 2, 4, 3, 3))),
            'score_reasons': dict(zip(DIMENSIONS, ('视频模型转向机器人动作。', '连接视频预训练和多个机械臂平台。',
                '仅早期合作方，未公布部署规模。', '官方包含微调后放置误差对照。',
                '技术原文已读，精确日仅有二手证据。', '官方9月月份无法判定是否在本期两周内。')))})
    write_json(ROOT / 'data/editorial/2026-W40-news-reviews.json', reviews)
    write_json(ROOT / 'data/research/v04-source-snapshots.json', readings)
    print(json.dumps({'original_events': len(original), 'current_memory': len(events),
                      'original_reading_snapshots': len(readings), 'editorial_reviews': len(reviews)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
