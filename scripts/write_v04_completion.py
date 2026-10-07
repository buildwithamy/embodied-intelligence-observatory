"""Write the task's A–K handoff from the current real discovery/audit artifacts."""
from datetime import date
from pathlib import Path

import yaml

from embodied_observatory.discovery import NewsCandidate
from embodied_observatory.editorial_gate import eligible
from embodied_observatory.pipeline import load_json

ROOT = Path(__file__).resolve().parents[1]


def main():
    run = ROOT / 'runs/2026-W40'
    log = load_json(run / 'discovery_log.json')
    news = [NewsCandidate.model_validate(c) for c in load_json(run / 'news_candidates.json')]
    selection = yaml.safe_load((run/'editorial_selection.yaml').read_text(encoding='utf-8'))
    memory = load_json(ROOT / 'data/major_events.json')
    before = {e['id'] for e in load_json(ROOT / 'data/editorial/history/2026-W40-major-events-before-v04.json')}
    additions = [e for e in memory if e['id'] not in before]
    recent = sorted([c for c in news if eligible(c, date(2026, 9, 21), date(2026, 10, 4))],
                    key=lambda c: (-c.score, c.id))
    amd = next(c for c in news if c.id == 'amd-world-labs-agreement')
    open_queries = sum(q['scope'] == 'open' for q in log['queries'])
    navigations = sum(q['scope'] == 'source_navigation' for q in log['queries'])
    rows = ['# V0.4 执行报告：新闻发现、独立审计与人工选题', '',
        '执行日：2026-10-06。开放发现窗口：2026-09-21～2026-10-04；重大记忆窗口：2026-08-06～2026-10-04。', '',
        f'工程、审计、预览与测试已完成；选题状态为 **{selection["review"]["status"]}**。正式 W40 页面仍为已认可的 V0.3，尚未替换。', '',
        '## A. 原系统遗漏大新闻的原因', '',
        '旧采集器以固定官方 RSS、GitHub Releases 和论文源为入口。白名单之外的资本、空间智能与计算平台事件，可能根本没有进入候选池；进入池后的论文型评分又偏重代码和研究新颖性。单靠增加一个 AMD 站点，不能解决相邻领域的持续漏报。', '',
        'V0.3 的独立审计曾补回部署与产品事件，但本身仍依赖人工直接找已知一手来源。现在先做跨公司、跨领域开放发现，再追到原文核验，新闻重要性也与论文评分分开。', '',
        '## B. 修改了什么', '',
        '- 新增 `config/discovery_queries.yaml`：九类主题，每类中英开放查询，资本、模型与算力包含相邻领域关键词。',
        '- 新增 `config/entity_watchlist.yaml`：35 个最低检查实体；不会据此过滤其他公司。',
        '- 新增 `config/editorial_scoring.yaml`：战略影响30%、跨生态影响20%、规模15%、技术意义15%、证据10%、时效10%。重要性和核验状态分开保存。',
        '- 新增独立 NewsCandidate、真实查询日志、事件日期与报道日期、URL 去重、原文核验记录、六维分数与逐项理由。摘要只提供线索；日期不明的候选继续留队列。',
        '- 新增 `discover → audit → editorial_selection.yaml → review-selection → report/edition`。`publish --reviewed` 也不能绕开此闸门。',
        '- Audit、候选、来源、配置、事件快照、选题与编辑稿用摘要绑定；确认后的改稿或来源变化会要求重新审核。Dry Run 禁止把输出目录设为正式项目根。',
        '- 保留前端配色、布局、CSS、JS 与已有插图。只修改选题数据、时间窗口和与内容不符的提示文字；没有整篇重润色，没有新增模型 API 调用。', '',
        f'本轮实际执行 {open_queries} 个开放查询、{log["executed_watchlist_queries"]} 个 Watchlist 查询、{navigations} 个原文导航，返回 {sum(q["results_seen"] for q in log["queries"])} 条检索记录。URL 去重后有 {log["candidate_count"]} 条发现线索；归并事件及加入记忆后有 {len(news)} 条候选，其中 {sum(c.verification == "unconfirmed" for c in news)} 条仍未核验。检索命中数不等于合格新闻数。', '',
        '这次使用真实外部检索记录导入，原文由 Codex 核读。CLI 的 Bing RSS 入口能记录和重放查询，但实测出现无关词典结果、旧文和网络限制，尚不足以替代本轮的人工检索与核验。没有把本轮结果称为无人自动召回。', '',
        '## C. AMD / World Labs 回归结果', '',
        '- Found in discovery：是。除实体查询外，不含 AMD 或 World Labs 的空间智能/physical AI 并购查询命中 ITPro 的报道，后续与官方事件归并。',
        '- Relatedness：adjacent。空间模型与计算路线图涉及机器人、仿真和 physical AI；不要求所有原文都包含 robot 关键词。',
        '- Primary sources：AMD 公告、World Labs 公告和 AMD 8-K；原文正文保存在事件快照。',
        f'- Tier：**{amd.proposed_tier} / {amd.score:g}**；建议首页第一条。',
        '- 技术/交易边界：9/28为公告日；8-K载协议于9/26签署，约82亿美元为股票交易对价。预计年底前完成仍需批准和交割条件，不能写成收购已完成；机器人技术收益尚未实测。', '',
        '[AMD 公告](https://newsroom.amd.com/news/amd-acquire-world-labs/) · [World Labs 公告](https://www.worldlabs.ai/blog/amd-announcement) · [AMD 8-K](https://ir.amd.com/financial-information/sec-filings/content/0000002488-26-000182/amd-20260926.htm)', '',
        '## D. W40 Top 15 候选', '',
        '以下排名以可核验且在两周内的事件/实质更新为基础。分数是有理由的编辑判断，不是客观行业价值或投资评分。证据、实体和应用领域详见 Audit。', '',
        '| 排名 | 事件 | 日期 | 级别 / 分数 |', '|---|---|---|---|']
    for rank, c in enumerate(recent[:15], 1):
        rows.append(f'| {rank} | {c.title} | {c.event_date} | {c.proposed_tier} / {c.score:g} |')
    rows += ['', '## E. 当前页面事件的降级与保留', '',
        '- Figure Helix 2.5：原发布较早，保留家庭泛化封面回看与背景，暂不占两周新事件的首页 Top Story。',
        '- Digit 5 / FORT、智元部署、Atlas RMAC：均保留候选、速读或时间线。影响重要但较集中于产品/部署，排名低于跨生态收购和平台变化；演示、订单与持续运营指标继续区分。',
        '- Isaac ROS 5.0：保留 A 级工具进展；开发助手支持不等于真机部署更可靠。Isaac Lab 较早发布作为背景。',
        '- 人形机器人标准：第1与第5部分合并到同一标准系列，避免重复放大；目前核验了元数据，未读到完整条款，不推测合规能力。',
        '- Microsoft 推理卸载、Light-O1：仍是高优先级候选，放速读和回溯；在最多五条的首页中，排在上述新选题之后。Microsoft 的3月报告不是9月新论文；Light-O1 的模拟成功率不是实际家庭任务成功率。',
        '- 原有两项论文故事：论文证据与六篇精读继续保留在研究区，没有因为栏目配额占据新闻首页。', '',
        '## F. 补入的事件与边界', '',
        f'重大记忆从10条扩至{len(memory)}条，保留原有2条归档；新增{len(additions)}条。下面是本轮新增记录，并非全部都是两周内的新发布。', '',
        '| ID | 原发布 / 最近实质更新 | 去向 |', '|---|---|---|']
    for event in additions:
        destination = '两周内候选' if event['last_updated'] >= '2026-09-21' else '背景记忆；不刷新发布日期'
        rows.append(f'| `{event["id"]}` | {event["event_date"]} / {event["last_updated"]} | {destination} |')
    rows += ['',
        '开放资本查询还发现了高通/PickNik、Cognex/RealSense 和 SiMa.ai 融资。前两项原文核验后改变了首页建议；SiMa.ai 是本轮1.5亿美元融资，累计融资与估值另列，2028硬件目标不当作当前产品指标。', '',
        '模型与基础设施扩展包括 FLUX 3 Action、Light-O1、Intrinsic Core、Microsoft 推理卸载、RLark/RPent，以及端侧推理和机器人控制工具。部署、产品和教育补入 Sharpa、TrinaTracker、Viam、RoboChrono及课程/微专业线索，重要性较低的记录进备忘，不强凑 Top Story。', '',
        'Skild S1 的原发布日期为8/18；World Labs Atlas为9/1，都作为背景。Gemini ER2原日期为7/30，超出本期60天记忆窗口。近期媒体重新报道不能把它们写成本期发布。Praxis-1 已读到官方技术稿，但官网只标9月，精确日仅有二手/嵌入帖证据，继续待核验；权重尚属未来计划，也不能写成已经开源。', '',
        '旧系统缺少这些事件，主要是固定来源范围、相邻领域边界和论文排序造成。现在九类开放发现与实体检查分开执行，重要线索回到公司技术稿、原始公告和监管文件；同时保留不能确定的日期和反爬失败，不用猜测补齐。', '',
        '## G. Major News Audit', '',
        '[EDITORIAL_AUDIT.md](../runs/2026-W40/EDITORIAL_AUDIT.md) 包含 Top15、背景记忆、补入项、建议 Top5、降级理由与六维评分证据。完整未核验队列另存 JSON，以便人工先看重要部分。', '',
        '[查询日志](../runs/2026-W40/discovery_log.json) · [候选池](../runs/2026-W40/news_candidates.json) · [原文事件快照](../runs/2026-W40/major_event_snapshot.json) · [有限人工参考集](../runs/2026-W40/manual_major_news_check.yaml)', '',
        '人工参考集来自原有事件与本轮独立原文核验，记录发现来源及是否进入最终选题；尚未确认前 final_selected 保持空值。它不是全网真值集，也不能据此计算无人系统的全球召回率。查询日志能区分未执行、空结果、来源导航、无日期与未核验等问题，漏报后可增加独立参考项再复查。', '',
        '## H. Editorial Selection', '',
        '[editorial_selection.yaml](../runs/2026-W40/editorial_selection.yaml) 保存首页顺序、briefing、recent_major、exclude及S级例外理由；建议首页为 AMD、PickNik、FLUX 3 Action、RealSense、Intrinsic Core。S级事件若不在首页，必须记下例外理由。', '',
        f'当前仍为 `{selection["review"]["status"]}`。任务书第12节要求人工查看Audit、确认选题后再生成正式周刊，因此没有代替用户填写已审核。正式更新只差这一项用户确认；确认绑定具体选题和具体编辑稿。', '',
        '## I. W40 预览、验证与截图', '',
        '[打开本地预览](http://127.0.0.1:8765/previews/2026-W40-v04/index.html) · [静态文件](../site/previews/2026-W40-v04/index.html) · [编辑输入](../data/editorial/2026-W40-v04.json)', '',
        '[桌面首屏](screenshots/2026-W40-v04-desktop.png) · [手机首屏](screenshots/2026-W40-v04-mobile.png) · [桌面重点解读](screenshots/2026-W40-v04-desktop-stories.png) · [手机重点解读](screenshots/2026-W40-v04-mobile-stories.png)', '',
        '验证：79项pytest通过；Ruff通过。Playwright在1440、390、320px宽度检查5条首页故事、6篇默认折叠论文、图片加载、展开交互、横向溢出和脚本错误；三个尺寸均通过。最新数据导入后又验证了31项发现/编辑闸门测试。', '',
        '回归覆盖：AMD由无品牌并购查询发现、相邻领域保留、未知实体、不明日期、超期/未来记录、坏结果不阻断后续记录、URL追踪参数去重、共享来源不误合并两个已核验事件、重要性不自动确认事实，以及三个正式入口的闸门、S级例外、确认后修改失效和Dry Run隔离。', '',
        '本轮新增付费模型调用为0。编辑稿保留V0.3已润色内容，历史DeepSeek使用记录单独继承；不是本轮新增调用。', '',
        '## J. 当前盲区', '',
        '- 索引时效、地区差异和搜索日期操作符不严格；执行查询不是全部消息都已找到。Watchlist也不能代表行业边界。',
        '- Bing RSS实测召回质量不足；本轮真实外部搜索导入仍需要人工核读，不宣称全自动大新闻发现。',
        '- X/LinkedIn、付费媒体、中文站点与政府网站反爬可能无法直接取到原文。遇到不可达、发布日期不足或宣传与原文冲突，线索留在编辑桌。',
        f'- 当前有{sum(c.verification == "unconfirmed" for c in news)}条未核验线索，包含很多旧文、索引页和无关结果；数量增长不能当作新闻质量增长。还没有多周独立漏报基线，不能保证重大新闻无遗漏。',
        '- 公司自报部署、订单、演示、许可与测试结果仍需独立对照；聚合站和二手日期不能直接确认模型发布。', '',
        '## K. P0 / P1 / P2', '',
        '- P0：选择质量稳定、可记录请求的搜索后端；补充原文日期与网页元数据读取，建立独立人工漏报清单，继续检查未核验高影响线索。',
        '- P1：细化中文别名与政策/教育查询，支持许可允许的付费媒体入口、社交公告与失败重试；改进同一事件的跨媒体聚合。',
        '- P2：连续多周记录独立人工参考集、漏报来源与排序调整效果，再评估自动化；当前不新增定时发布。', '',
        '## 最终验收判断', '',
        'Q1：本轮已把影响行业理解的交易、动作模型、平台工具及原有部署事件放到编辑桌，但没有证据证明两周大新闻已穷尽。',
        'Q2：已用无品牌空间智能/physical AI检索发现并核验AMD、PickNik、RealSense，也纳入Microsoft推理卸载；相邻领域不会因不在公司名单中而被排除。',
        'Q3：降级理由、六维分数、日期与证据边界可以追查；最终人工顺序还待确认。',
        'Q4：能够回到每条查询、结果、错误和事件归并记录，并在人工参考集中记录漏报，修改Query、Watchlist或评分后重跑。跨周召回率尚未验证。', '']
    (ROOT/'docs/v04_completion_report.md').write_text('\n'.join(rows), encoding='utf-8')


if __name__ == '__main__':
    main()
