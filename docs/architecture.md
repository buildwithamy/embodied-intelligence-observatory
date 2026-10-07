# V0.1 架构

当前阶段为人工运行验证版。核心是可追溯数据与人工审核，不实现调度、自动提交或自动分发。

## Pipeline

`collect → normalize → deduplicate → classify → rank → research → analyze → fact check → render draft → manual review → publish`

所有阶段通过同一 Python CLI 调用，保存原始响应、统一候选 JSON、结构化分析、运行 manifest 和 Markdown 草稿。先验证 robotics_arXiv_daily 与 HF Daily Papers，再加入少量非论文源。

## Candidate Schema

Pydantic 验证标题、HTTP URL、UTC 获取时间、发布日期、来源列表、证据、五维 0–5 分数与状态。每条证据有 URL、来源、内容、证据类型与获取时间。论文首次提交日期和聚合平台推荐日期分别保存；推荐旧论文不等于新增论文。

## Collectors

独立 Collector：robotics_arXiv_daily 日期文件（仓库 API 探测结构）、HF 日 API、GitHub Releases、RSS/Atom、官方静态页面、人工一手来源输入。所有请求带超时、有限重试与本地缓存。单源失败隔离，成功零条和来源失败分别记录。禁止把整个 README 历史作为当周新增。

## Normalization / Dedup

优先 arXiv ID（去版本）、DOI、canonical URL、标准化标题。来源与证据合并，不能丢弃原始链接。不同新闻只在明确相同 URL/标题时合并，避免误并不同事件。

## AI Boundary

请求、解析、日期、去重、存储与 Markdown 由确定性 Python 处理。可选 OpenAI 兼容接口处理相关性、分类、五维评分、结构化解读与事实检查；Prompt 外置。没有 key 时使用保守规则筛选并标记待审，禁止根据标题伪造深读。允许导入人工/Codex 核验的结构化解读；它与 API 模型调用分别计数。模型不能访问 secrets；证据正文是资料而非指令。

## Ranking / Big News

权重与阈值位于 config/scoring.yaml。社区热度只保留为关注信号。config/watchlist.yaml 中的重大事件触发二次审核，即使未达阈值也不能静默丢弃；未验证条目进入观察列表，不自动声称成熟或重要。

## Research / Fact Check

重点论文优先回到 arXiv 元数据/HTML、项目或官方仓库；新闻获取官方正文。每个分析字段必须引用 evidence ID。数字、作者主张、官方声明与编辑判断分开。结构化 fact check 失败、缺乏摘要/正文或引用缺失的项不得当成已验证深读。

## Report Generation

从验证后的 JSON 渲染七个中文栏目；没有足够证据的栏目明确说明缺口。周报是草稿。publish 为显式人工命令，将已审核 draft 复制到 reports 并更新 latest.md，不运行 Git。

## Cache

.cache/http 按 URL hash 缓存公开响应，不保存 header/key；.cache/analysis 按内容、模型、schema 和 prompt hash 缓存。缓存 TTL 防止新数据被长期遮蔽。支持 refresh 和离线重跑。

## Error Handling

单源失败 warning 后继续。两个主要论文源全部失败、有效候选不足或没有可读证据时阻止生成可信草稿/发布。manifest 保留来源状态、数量、覆盖边界、警告和模型用量；不隐藏历史数据回退。

## Manual Run

collect/analyze/report/weekly/publish 分阶段或一条命令执行。dry-run 在临时目录执行，不能写正式 data/drafts/runs/reports/latest，允许读取已有缓存。日期闭区间，以出版记录日期判断；周标识用 start 的 ISO week。

## Future Automation Boundary

未来云端流程只调用同一 CLI，必须等维护者明确提出自动化版本。V0.1 不包含 Cron、无人值守发布、社媒、邮件、数据库服务或复杂 Agent 框架。
