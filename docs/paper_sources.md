# 论文来源实现与真实核验

核验日期：2026-10-06（北京时间）。本次验证区间固定为最近完整自然周 **2026-09-28～2026-10-04**，没有换成历史区间冒充本期。

## robotics_arXiv_daily

来源：[jiangranlv/robotics_arXiv_daily](https://github.com/jiangranlv/robotics_arXiv_daily)。

检查[上游生成程序](https://github.com/jiangranlv/robotics_arXiv_daily/blob/main/daily_arxiv.py)发现：

- `docs/cv-arxiv-daily.json` 是主题分类下的累计 `arXiv ID → Markdown 行`；`update_json_file()` 保留历史记录并覆盖同 ID 的信息。
- README 每次从累计 JSON 重新生成。README 的全量行数不能当作本周新增论文数量。
- 行首虽然标为 `Publish Date`，实际写入的是 `result.updated.date()`，即 arXiv 修订日。
- Authors 列只保存 `paper_last_author + " Team"`，并非完整作者名单；JSON 不含论文摘要。
- README 的生成日期或某次提交时间都不能代替论文首次发表日。

Collector 通过 GitHub commits API 查询指定日期范围内涉及累计 JSON 的提交，分页读取并检查重复 SHA、最大页数和响应结构。以区间最早提交的父提交作为周初快照、最后一个提交作为周末快照，计算跨所有分类的 **新增 ID 集合**。同一 ID 在不同分类出现、修改标题、修订旧论文、移动分类都不会成为新增 ID。

然后按每批 50 个 ID 请求 [arXiv Atom API](https://export.arxiv.org/api/query)，显式设置 `max_results`，从原始论文元数据补全题目、完整作者、摘要和 `published` 日期。相邻批次默认至少间隔三秒。若批量 API 部分失败，可读取 arXiv 原始摘要页中 `citation_arxiv_id`、`citation_title`、全部 `citation_author`、`citation_abstract` 和 `citation_date`。备用解析不用表示修订日的 `citation_online_date`。备用默认最多尝试 20 篇，避免上游全面不可用时无限请求；其余缺失论文会明确计入 coverage warning。

缺失基线、无父提交、快照结构改变、分页截断等直接作为 source failure；不会退回全量 README。个别论文未能取得真实日期、作者、摘要则跳过并记录缺失数；本来有新增论文但全部元数据获取失败时直接失败。

边界快照法依赖上游累计更新特征，表示“期末保留且期初不存在的 ID”。若上游在区间内删除又添加同一 ID，或添加后又删除，该项不会计为本期新增。检测到跨边界删除时会记录 warning。它也不能给每条记录提供精确首次抓取时间，因此 robotics 不伪造 `discovery_dates`。

此次真实运行得到：

| 指标 | 数值 |
|---|---:|
| 指定周涉及 JSON 的提交 | 7 |
| 跨分类新增 ID | 299 |
| 成功补全 arXiv 作者、摘要、发表日 | 299 |
| 缺失元数据 | 0 |
| 首次发表日在本期范围内 | 244 |
| 本期新收录但首次发表较早 | 55 |

周初基线 SHA 为 `df8455816af3951b5ba96a7357268505180a9a58`，周末快照 SHA 为 `580183498039c51894f8ebbd19b764061f486aa1`。累计 JSON 的最后实际修改是 10 月 2 日，README 后续生成日期不是额外的论文 JSON 新增。

每条 Candidate 保留两份快照 URL、arXiv API 请求 URL、原始行、分类和证据。`published_at` 始终为 arXiv 首次发表日；源收录区间与上游修订日写入 notes。

## Hugging Face Daily Papers

已核验公开 API：[`https://huggingface.co/api/daily_papers?date=2026-09-28`](https://huggingface.co/api/daily_papers?date=2026-09-28)。实际返回 JSON 数组，其中每条 `paper` 对象含 `id`、`title`、`authors`、`publishedAt`、`submittedOnDailyAt`、`summary`，部分记录含 `upvotes`、`projectPage`、`githubRepo`。

Collector 按区间逐天请求，不为实际无分页的数组接口猜测 page 参数；若未来改成带明确 `papers/items` 和 `nextCursor/next` 的响应，才顺着显式 continuation 读取，检测重复 cursor、异常地址和最大页数。每天先完整取得响应，再处理数据，一天中途分页失败不能记成完整覆盖。单日失败不影响其他日期；全部日期失败时 source failure。

`paper.publishedAt` 保存到 `published_at`，当天推荐日期保存到 `discovery_dates`。记录的 `submittedOnDailyAt` 若与请求日冲突会跳过并告警，不把其他日期响应当作本期。先发表后推荐的历史论文可以在原始发现池中保存，但不能称为本周新发表论文。主 pipeline 对首次发表日进行本期过滤。

`upvotes` 仅保留为 `community_popularity`，代表社区关注信号；本身不等价于研究质量、技术突破或可复现性。题目、摘要、作者与链接保留原始来源证据；没有摘要和作者时不只凭标题编写论文分析。

此次真实运行得到：

| 指标 | 数值 |
|---|---:|
| 请求日期 | 7 |
| 成功日期 | 7 |
| 原始推荐记录 | 233 |
| Collector 内按 arXiv ID 去重 | 233 |
| 首次发表日在本期范围内 | 150 |
| 首次发表较早的推荐记录 | 83 |

两个论文源合计 532 条发现记录、518 个独立 arXiv ID，交集 14 篇。上述 532/518 是发现层统计，不能当成本周合格论文、相关论文或精选论文数量；真正周报计数以 pipeline 的日期过滤、去重、相关性筛选和人工核验为准。

## 配置、覆盖与复核

公共函数为 `collect_robotics(client, start, end, source)` 和 `collect_hf(client, start, end, source)`，均返回 `list[Candidate]`。client 提供 `get_json(url)` 和 `get_text(url)`，公共响应缓存由统一 HTTP 层负责。

可配置的 robotics 字段：`repo`（亦支持 `repository`）、`snapshot_path`、`page_size`、`max_pages`、`arxiv_api_url`、`arxiv_batch_size`、`arxiv_delay_seconds`、`arxiv_fallback_limit`；HF 支持 `url`（亦支持 `api_url`）和 `max_pages`。

每个 source 的 `_stats` 保存原始条目、提交或日期覆盖、元数据失败和备用恢复统计，`_warnings` 保存部分失败及缺失信息，由 pipeline 纳入 run manifest。实时网络核验与单元测试分开；离线测试覆盖历史行不会成为新增、跨分类重复、发表日与修订日不同、推荐日与发表日不同、GitHub 分页、HF continuation、部分/全部请求失败、HTML 元数据备用以及错误日期响应。

web-access skill 已加载；尝试其 CDP 前置脚本时，当前 Windows 的 WSL Bash 返回 `E_ACCESSDENIED`。这些来源属于公开 API 和公开静态页面，按该 skill 的工具选择直接采用公开 HTTP 读取，无需浏览器登录或额外浏览器设置。
