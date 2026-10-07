# 数据源覆盖与实测记录

客户端日期：2026-10-06（Asia/Shanghai）。指定验证周：**2026-09-28 至 2026-10-04**。下表保留初次非论文探测结果。后续完整 weekly 重试时教育部政策列表恢复访问并返回0条，最终为13源尝试、12成功、1失败，以 `runs/2026-W40.json` 为准。本页不替代逐次 Run Manifest，也不承诺整个行业的完整覆盖。

## 已实现来源

| 来源 | 获取方式 | 本次项目客户端结果 | 指定周候选数 | 已核验的范围或限制 |
|---|---|---|---:|---|
| NVIDIA Robotics | 官方RSS | 成功 | 0 | 当前RSS 18项，最近发布日期2026-09-22；限定机器人/Physical AI主题 |
| Google DeepMind | 官方RSS | 成功 | 0 | 当前RSS 100项；当周通用模型与生物信息新闻未通过机器人过滤 |
| LeRobot | 官方GitHub Releases | 成功 | 0 | 11项；最近正式Release v0.6.1发布于2026-08-03 |
| ROS 2 | 官方GitHub Releases | 成功 | 0 | 实际读取2页；不能因第一页旧日期就停止分页，最近项2026-09-14 |
| MoveIt 2 | 官方GitHub Releases | 成功 | 0 | API正常，但该仓库返回空Release列表；tag/changelog不能冒充Release |
| MuJoCo | 官方GitHub Releases | 成功 | 0 | 55项；3.14.0发布于2026-09-22，3.15.0于2026-10-05，均不在指定周 |
| Isaac Lab | 官方GitHub Releases | 成功 | 0 | 24项；使用API的draft/prerelease标志排除非正式发布 |
| MIT Robotics | 官网公布的专题RSS | 成功 | 2 | 研究新闻归技术类，不能作为人才培养动态充数 |
| MIT Education | 官网公布的教育RSS | 成功 | 0 | 37项；当周原有2篇教育新闻，但不满足机器人教学主题 |
| 教育部教育新闻 | 官方当前列表+详情 | 失败 | 未知 | 项目客户端3次请求后 `network unavailable`；独立探测还遇到403/TLS错误 |
| 教育部本科专业设置政策 | 官方当前列表+详情 | 失败 | 未知 | 项目客户端3次请求后 `network unavailable`；独立探测有短暂200及503，不能算稳定成功 |

首次非论文探测：**尝试11，成功9，失败2，当周入池2**。最终完整运行非论文部分：**11尝试、10成功、1失败、2候选、1入选**，教育部政策列表恢复但无当周匹配。访问成功且返回0，与访问失败、覆盖未知是不同状态。来源可用性随网络及站点变化，以最新Manifest为准。

MIT当周两个原始链接：

- [Powered by muscle cells, a paper-thin robot swims through watery maze（2026-09-29）](https://news.mit.edu/2026/powered-by-muscle-cells-paper-thin-robot-swims-through-watery-maze-0929)
- [Computational tools for society’s most complex challenges（2026-10-02）](https://news.mit.edu/2026/computational-tools-for-societys-most-complex-challenges-cathy-wu-1002)

第二项是跨领域研究者介绍，入候选池不代表必然入选周报，仍须相关性筛选与编辑判断。

## 教育覆盖不能靠关键词凑数

教育来源同时要求机器人主题与课程、教学、教材、培养等教育主题。MIT教育源额外要求标题直接涉及机器人、具身智能、机电或自主系统。真实运行中，[The next generation’s guide to the new space economy](https://news.mit.edu/2026/guide-to-new-space-economy-1002)在正文附带出现机器人，本次主动排除，不能把太空经济课程当作机器人教育新课程。

教育部来源仅纳入公开专业、课程、教学、培养信息，不纳入一般招生、校园活动或维护者公司内部内容。初次两个国内源均不可达，完整运行时政策列表恢复；教育新闻仍失败，**本周国内教育覆盖不足，政策仅覆盖可见专业设置栏目**。周报明确显示缺口；没有教育条目不能写成“本周没有教育进展”。

可供人工核对的历史教育背景是教育部的[2026年本科专业目录发布（2026-04-28）](https://www.moe.gov.cn/jyb_xwfb/gzdt_gzdt/s5987/202604/t20260428_1435016.html)及[官方通知](https://www.moe.gov.cn/srcsite/A08/moe_1034/s3882/202604/t20260427_1434931.html)。这些历史页面不纳入本周候选，不能改写日期冒充当前新闻。若后续要验证历史教育栏目，需显式另跑历史范围，并核对文章发布元数据与通知生成日期的区别。

## 日期与可追溯性

- RSS使用发布者给出的日历日期，Atom优先`published`、缺失时使用`updated`；日期缺失或无效的条目跳过并警告。
- GitHub使用`published_at`，排除`draft`和`prerelease`，不以`created_at`替代。分页读到列表耗尽，达到配置上限则报覆盖不完整。
- 教育部网页路径日期只用于减少详情请求，条目日期由详情页发布元数据或明确的“日期+来源”行核实；没有可验证日期则报错。
- RSS保存原始标题、正文摘要、发布日期、发布者和文章链接；Release保存官方release正文和链接；详情页保存官方正文。Evidence归属于原始发布方，企业指标和论文结果仍属于发布方主张。
- RSS/当前列表只覆盖其可见窗口；教育部列表没有实现全站档案搜索。历史区间超出窗口时，不能把空列表理解成完整历史覆盖。

## 边界和未接入

尚未接入国内企业广泛报道、收费数据库、社交媒体、普通媒体转载、全部ROS包级变更、MoveIt tags/changelog、全国高校课程和职业教育公告。Boston Dynamics根RSS实测可解析但无条目，未启用；不能把无可用数据的RSS当成稳定行业覆盖。MIT常见猜测路径 `/rss/topic/robotics` 返回404，实际采用[MIT官方RSS目录](https://news.mit.edu/rss)提供的 `/topic/mitrobotics-rss.xml`。

如果维护者需要另一周验证开源与产业栏目，**2026-09-21至2026-09-27**有已经核验的NVIDIA与MuJoCo发布日期可供显式另跑。本次不会静默替换指定的最近完整周。

## 验证方式

10个非联网collector测试覆盖RSS/Atom、时区日历日期与边界、来源证据、教育误匹配、GitHub分页/预发布/限流响应、官网结构变化、详情日期验证及错误传播；已通过。针对本模块的Ruff检查已通过。

本次公开读取按 `web-access` 指引优先使用公开API/RSS/原始HTML。其Bash CDP前置检测因本机WSL权限失败，未操作用户浏览器；静态公开读取不依赖登录，实际网络请求通过已批准的公开只读方式完成。

连续人工运行3–4周时，应分别记录来源成功率、可见窗口、条目数量、编辑后有效数量、教育与国内覆盖缺口。不要为了让栏目非空而降低主题标准。
