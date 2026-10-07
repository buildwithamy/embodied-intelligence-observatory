# 人工运行指南

## 每周操作

1. 选择最近完整自然周。首次验证为2026-09-28～2026-10-04（ISO 2026-W40）；日期为闭区间。按源出版记录的日历日判断，GitHub采集提交范围使用UTC。
2. 运行 `weekly --start ... --end ...`；有配置的API模型再加`--llm`。屏幕与manifest报告失败、数量及草稿位置。不是自然周的范围会警告，周ID按start命名。
3. 检查`runs/YYYY-WXX.json`：来源失败、HF逐日成功、robotics快照SHA及metadata缺失量、有效候选/入选数、二次检查队列、模型用量。成功零条与失败必须分开评估。
4. 看`data/candidates/`与草稿，核对题目、作者、出版日期、arXiv ID、指标、公司名称、链接、分类、事实归属与阅读层级。模型解读不能取代来源核验。
5. 修改候选review JSON或草稿；调用`analyze --analysis-file ...`及`report`重新生成。确认后维护者自行运行`publish --week ... --reviewed`，再人工commit与push。

V0.1无自动commit/push。源全部失败或只有极少数据时，诊断文件仍保存但生成被阻止，不应拿空周报作为成功。

## 结构化人工解读

文件为JSON数组，每项包含`id`，可选`relevant`、`scores`、`tags`、`evidence`、`notes`与`analysis`。`id`来自候选池，不可发明。analysis需中文标题、研究问题、方法、主要结果、价值判断、局限、confidence、evidence_refs、claim_refs、fact_check、origin与read_depth。origin为`human_review`或`codex_review`；Schema拒绝不存在的证据ID。

三个事实字段分别在claim_refs引用对应证据。新增全文/官方正文先以Evidence保存，包括id、url、source、kind、text、retrieved_at。`fact_check=pass`表示编辑已将这些字段与来源对照；请把检查范围写入fact_check_notes。relevant=false可排除规则误选。参见`data/editorial/2026-W40.json`真实首期记录。

人工来源补充可使用`collect/weekly --supplement path.json`，文件为完整Candidate数组。必须有真实日期、官方URL、证据与sources；发布日期不在范围的项会被过滤。不把人工输入称为自动抓取。

## 重跑与Dry Run

HTTP缓存默认6小时；同一范围重跑会利用缓存但可重新渲染。`--refresh`重新请求；`--offline`使用已有缓存，未命中会按来源失败处理。缓存重放不等于本次实时抓取。清空缓存用`cache-clear`，保留data与reports。

Dry Run所有写入发生在系统临时目录（输出路径显示在屏幕），不改变正式产物。analyze/report的Dry Run会复制必要输入到临时目录。不要从临时目录直接发布。运行API模型仍有费用；离线模式不可与API模型组合。

重复collect会重建同一周候选，所以应显式导入已有review文件以保留核验结果。手改draft后不要随意重跑report，它会重新渲染draft；正式reports与latest只有publish更改。

## 模型调用与费用

默认零模型API调用，仅确定性预筛与模板。API模式对规则命中/大新闻待审候选分类评分，每个入选项另解读和事实检查；成功重复调用通过cache复用。tokens记录在manifest，未配置模型费率不猜费用。本对话Codex审核成本不属于脚本API用量，manifest单独计editorial_imports。

主要token消耗是候选摘要和重点全文；优先规则排除无关条目、限制栏目条数、复用内容/Prompt缓存。不要为了低成本牺牲证据；可以使用结构化人工审核替代API而非制造「完整分析」。

## 连续3–4周验证表

每期人工记录以下指标（可另写`runs/YYYY-WXX-review.md`）：

| 维度 | 维护者需要记录 |
|---|---|
| 覆盖 | 是否漏大新闻；两论文源是否正常；教育数据是否不足；国内企业是否明显弱于国外 |
| 内容质量 | 焦点是否重要；规则/模型误判；夸张结论；abstract复述程度；公司PR依赖 |
| 去重 | 同一论文、新闻、Release是否重复；版本是否误当新论文 |
| 长度与比例 | 总长度、论文数量、产业与教育比例、读者反馈 |
| 成本 | 模型调用次数、cache命中、输入/输出tokens、账单费用、最贵步骤 |
| 稳定性 | Collector失败类型、耗时、页面改版、空结果与API限流 |
| 审核负担 | 编辑花费时间、改写字段数、需要额外一手资料的条目 |

每周按watchlist人工看头部公司、国内企业、国家政策和专业建设，复查未进入排名的大新闻。结束后看连续manifest判断哪些源值得保留，再决定是否提出自动化版本；本阶段不要自行加入Cron、无人值守发布或社媒分发。
