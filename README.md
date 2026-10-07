# Embodied Intelligence Observatory

**具身智能观察站**：跟踪具身智能研究、技术、产业、开源生态与教育发展的公开信息工程。核心产品是中文《具身智能周报》，面向机器人研究者、工程师、教师、学生及产业观察者。

当前为 **V0.4 人工运行验证阶段**。先做最近14天的中英开放新闻发现，再独立核验、评分、审计与确认选题；论文评分与新闻重要性分别运行。

本期入口：[V0.4 选题预览](site/previews/2026-W40-v04/index.html) · [Editorial Audit](runs/2026-W40/EDITORIAL_AUDIT.md) · [选题文件](runs/2026-W40/editorial_selection.yaml) · [A–K 执行报告](docs/v04_completion_report.md)。预览待维护者确认，正式 [W40 网页](site/weekly/2026-W40/index.html) 仍保留V0.3。没有定时任务、自动提交、外网发布或社交媒体分发。

## V0.4：发现、核验、审计与人工选题

真实外部检索记录可导入并离线重放。每条查询记录 query、category、language、scope、results；命中记录 title、url、snippet，event_date未核实可为空。source_navigation不计入开放查询覆盖，watchlist不替代九类中英开放发现。

```powershell
.\.venv\Scripts\python.exe -m embodied_observatory discover --week 2026-W40 --start 2026-09-21 --end 2026-10-04 --results-file data/research/v04-capital-models.json data/research/v04-other-discovery.json data/research/v04-models-followup.json data/research/v04-open-capital-check.json data/research/v04-open-physical-ai-capital.json data/research/v04-watchlist-discovery.json
.\.venv\Scripts\python.exe -m embodied_observatory audit --week 2026-W40 --reviews data/editorial/2026-W40-news-reviews.json
# 阅读Audit，编辑Selection中的顺序、去向和理由，并准备对应的编辑稿，再预览：
.\.venv\Scripts\python.exe -m embodied_observatory report --week 2026-W40 --selection runs/2026-W40/editorial_selection.yaml --issue-file data/editorial/2026-W40-v04.json --dry-run
# 仅由维护者明确确认后执行；此命令只记录审核，不生成网页：
.\.venv\Scripts\python.exe -m embodied_observatory review-selection --week 2026-W40 --selection runs/2026-W40/editorial_selection.yaml --issue-file data/editorial/2026-W40-v04.json --reviewer 维护者 --reviewed
.\.venv\Scripts\python.exe -m embodied_observatory report --week 2026-W40 --selection runs/2026-W40/editorial_selection.yaml --issue-file data/editorial/2026-W40-v04.json --archive
```

修改发现记录、原文、评分配置、Audit、Selection或编辑稿后，旧确认会失效，需重新审计/确认。Audit重跑保留现有选题文件，避免覆盖人工选择；旧文件的audit摘要失效时需要人工对照新Audit更新。正式`edition`、`report --selection`和`publish`共用闸门，单独`--reviewed`不能绕过。

不提供`--results-file`时，`discover`使用Bing RSS；`--offline`只重放缓存。此入口实测存在无关结果、旧文与访问限制，尚未达到本轮人工检索质量。错误与空结果会记录，日期不足的线索保留待核验。事件对价、客户部署、开放许可与论文结果均须原文审核，搜索摘要不会自动成为正文。`scripts/prepare_v04_*`是W40一次性原文整理/编辑脚本，不是未来周刊的自动发现或审核规则。

配置：[九类查询](config/discovery_queries.yaml) · [实体检查](config/entity_watchlist.yaml) · [新闻评分](config/editorial_scoring.yaml)。完整记录：[发现日志](runs/2026-W40/discovery_log.json) · [候选池](runs/2026-W40/news_candidates.json) · [原文快照](runs/2026-W40/major_event_snapshot.json)。重大记忆保留60天内可核验记录，旧事件不因近期报道刷新日期。

## V0.3：保留的图文编辑层

V0.3的一手事件、润色文案、SVG插图和历史审计继续保留。当前生成正式网页必须走上面的V0.4闸门；本地浏览静态网页：

```powershell
python -m http.server 8765 --bind 127.0.0.1 --directory site
```

打开 `http://127.0.0.1:8765/`；预览为 `/previews/2026-W40-v04/index.html`。网页与静态资源可直接从文件打开。`edition` 默认写site与drafts，显式`--archive`写本地reports；Dry Run写隔离目录，不改正式输出。历史重建读取该期绑定的原文快照，并校验截止日期。旧`report`缺少`--selection`时只生成V0.1待审Markdown草稿；`publish`已改为使用V0.4网页闸门。

V0.3首次独立审计保留10条事件、展示8条；V0.4新增开放发现后，记忆扩至33条，原有2条归档仍保留。`audit`读取真实发现与原文审核，不自行联网或自动确认。事件状态和发布日期与当前新闻评分分开保存。

[V0.3 架构](docs/v03_architecture.md) · [编辑输入](data/editorial/2026-W40-v03.json) · [事件记忆](data/major_events.json) · [独立审计](runs/2026-W40-major-news-audit.json)。每期 3 个核心信号、5–7 条速读、3–5 个 Top Stories、2–3 个研究问题、4–8 篇折叠论文与1–3个学习概念均绑定已确认事件或已审核论文引用，未确认线索不能进入正文。

## 为什么做

让读者先知道近期真正发生了什么，再理解对机器人应用、课程与学生能力的影响。论文作为证据与深读入口，候选池保留出版日期、来源、筛选理由与解读边界。教育由技术与部署变化导出，公开课程资源明确区分于当周新增动态。准确性、稳定性、可追溯性优先于条数。

## 内容与来源

- 论文：`jiangranlv/robotics_arXiv_daily` 区间快照新增 ID + arXiv 原始元数据；HF Daily Papers 逐日 API。
- 企业：NVIDIA Robotics、Google DeepMind 官方 RSS，限定直接机器人关联。
- 开源：LeRobot、ROS 2、MoveIt 2、MuJoCo、Isaac Lab 官方 GitHub Releases。
- 技术与教育：MIT 机器人新闻、教育 RSS；教育部教育新闻与专业设置栏目。
- 持续学习资源：MIT Underactuated Robotics、Berkeley CS285、LeRobot 官方文档。

配置位于 [config/sources.yaml](config/sources.yaml)。RSS 与政府可见列表有历史窗口限制，无法保证穷尽。一个源成功返回零条不表示行业没有事件。详见 [来源覆盖](docs/source_coverage.md) 与每次运行 manifest。

## 安装

Python 3.11+，在项目目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Linux/macOS 将解释器路径替换为 `.venv/bin/python`。后面的命令用已安装本项目的解释器执行；`eio` 是同一 CLI 的入口。程序在运行目录寻找 config 与 prompts，也可用 `--root` 指定项目目录。没有安装时可在 PowerShell 设置 `$env:PYTHONPATH='src'`。

## 环境变量与 AI 使用

所有凭证只从环境变量读取；程序不自动加载 `.env`。`.env.example` 只有变量名称与空值。

| 变量 | 用途 |
|---|---|
| GITHUB_TOKEN | 可选，提高 GitHub API 限流额度 |
| OPENAI_API_KEY | 仅 `--llm` 时需要，OpenAI 兼容 API key |
| OPENAI_MODEL | `--llm` 必须显式指定模型 |
| OPENAI_BASE_URL | 可选兼容接口地址，默认 OpenAI `/v1` |

网络、解析、去重、日期与报告渲染使用 Python。模型仅用于理解、分类、五维评分、结构化解读与独立事实检查。`--llm` 才会触发模型 API 调用；没有 key 时生成保守候选草稿，不伪造论文解读。也可导入明确标记 `human_review` / `codex_review` 的结构化 JSON。

模型返回内容必须通过 Schema 与证据引用验证。自动事实检查不等于独立复现实验，人工审核仍然必要。Prompt 独立保存于 [prompts/](prompts/)；周报编辑采用确定性 renderer，不增加额外的整篇模型调用。

## 手动运行

```powershell
python -m embodied_observatory weekly --start 2026-09-28 --end 2026-10-04
```

以上先执行14天开放发现，再完成论文采集、规则预筛、评分、正文获取与待审草稿；不会自动完成新闻原文核验、人工选题或正式网页更新。启用结构化 API 解读：

```powershell
python -m embodied_observatory weekly --start 2026-09-28 --end 2026-10-04 --llm
```

导入本次已核验的结构化解读并重跑：

```powershell
python -m embodied_observatory weekly --start 2026-09-28 --end 2026-10-04 --analysis-file data/editorial/2026-W40.json
```

分步执行：

```powershell
python -m embodied_observatory collect --start 2026-09-28 --end 2026-10-04
python -m embodied_observatory analyze --week 2026-W40 --llm
python -m embodied_observatory report --week 2026-W40
# 完成V0.4发现、审计与选题确认后，才可运行：
python -m embodied_observatory publish --week 2026-W40 --reviewed
```

`publish`重用已审核选题，写入site、drafts及`reports/YYYY/YYYY-WXX.md`，不写旧版latest，不会commit或push。未审核的新闻或论文不能进入正式正文。缺少Audit/Selection时，即使传入`--reviewed`也会阻止生成。

## Dry Run 与缓存

```powershell
python -m embodied_observatory weekly --start 2026-09-28 --end 2026-10-04 --dry-run
python -m embodied_observatory weekly --start 2026-09-28 --end 2026-10-04 --dry-run --offline --skip-research --analysis-file data/editorial/2026-W40.json
```

Dry Run 在系统临时目录保存所有产物，仅读取已有正式缓存，不写正式 data/drafts/runs/reports/latest。屏幕显示路径与数量，临时目录保留供检查；同样会进行网络请求，若带 `--llm` 仍会产生 API 费用。`--offline` 禁止网络，只重放缓存；不能与 `--llm` 组合。

HTTP 缓存 TTL 默认 6 小时，`--refresh` 重新获取；分析缓存键包括模型、接口、Prompt、Schema 与内容。`cache-clear` 只清空本项目 `.cache`；来源原始公开响应另存 `data/raw/*-responses.json`。缓存不保存凭证或敏感 headers。

## 架构与输出

```text
collect → normalize → dedup → classify/rank → research
→ structured analysis → fact check → draft → human review → publish
```

| 目录 | 内容 |
|---|---|
| config/ | 数据源、五维权重、大新闻 watchlist、持续课程资源 |
| prompts/ | 分类、各类解读、事实检查、编辑约束 |
| data/raw/ | 原始候选与本次使用的公开响应 |
| data/normalized/ | 去重后的标准化数据 |
| data/candidates/ | 分类、评分、证据与结构化解读 |
| data/editorial/ | 人工 / Codex 核验导入记录 |
| data/major_events.json | 持续事件、日期、状态与一手来源快照 |
| site/ | 读者网页、本期详情与本地静态资源 |
| drafts/ | 待维护者审核周报 |
| runs/ | 来源成功/失败、数量、警告、API用量 |
| reports/ | 显式 edition --archive 的本地归档；旧 publish 的文本产物 |

[架构](docs/architecture.md) · [编辑政策](docs/editorial_policy.md) · [运行指南](docs/manual_run.md) · [论文源语义](docs/paper_sources.md) · [本次执行报告](docs/execution_report.md)

## 编辑原则与准确性

优先原论文、官方项目、官方代码、政府与高校。作者报告与公司声明注明归属；观察站判断另列。没有证据不写性能提升数字、不把 demo 写成成熟系统、不用单篇论文宣布行业趋势、不凑条数。没有全文时标为摘要层级。公开网页及模型可能出错；科研、采购、投资和教学决策应查看原始来源。

本项目使用自动化程序与 AI 模型辅助信息收集、分类、摘要、内容组织与初步事实检查，通过一手资料、可追溯链接、结构化校验及人工审核提高准确性。首期使用 Codex 内容核验，模型 API 调用量与本对话模型成本分开记录。

## 测试与贡献

```powershell
python -m ruff check src tests
python -m pytest -q
```

测试使用明确标记的离线 fixtures，覆盖日期、ID/URL/title 规范化、去重来源合并、Schema、评分、失败隔离、缓存、草稿与 Dry Run。真实周报使用真实公开数据，不把测试 fixtures 当运行成果。贡献源请附官方地址、日期格式、稳定性验证与空结果说明，见 [CONTRIBUTING.md](CONTRIBUTING.md)。代码采用 MIT 许可；原论文、新闻与课程保留其原有权利。

## Roadmap

1. 连续 3–4 周人工运行，记录漏报、重复、来源失败、解读夸张与教育栏目可用性。
2. 优先补国内企业与教育政策稳定源、完善人工事实审核与评分。
3. 仅在维护者明确提出「现在开始做自动化版本」后，设计调用同一 CLI 的云端流程与人工发布门槛。
