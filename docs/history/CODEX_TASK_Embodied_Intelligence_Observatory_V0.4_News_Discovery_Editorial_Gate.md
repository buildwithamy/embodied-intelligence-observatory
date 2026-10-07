# Codex 改进任务：Embodied Intelligence Observatory V0.4
## 重点：重构“重大新闻发现 + 编辑闸门”，提升最近 2 周重点新闻召回率

> 项目：Embodied Intelligence Observatory  
> 当前版本：V0.3  
> 当前阶段：人工运行验证期  
> 本次任务重点：**新闻发现、重大事件召回、编辑选题**  
> 本次任务非重点：网页视觉、文案润色、自动发布  
> 暂时不要做 GitHub Actions Cron 或无人值守自动化。

---

# 0. 为什么要做 V0.4

V0.3 已经完成了较好的展示层升级：

- 有 Hero；
- 有 10 分钟速读；
- 有 30 天大事回溯；
- 有 Top Stories；
- 有 Impact Radar；
- 有 Research Radar；
- 有 Papers Worth Reading；
- 有 Learning Corner；
- 页面已经具备技术周刊的基本形态。

但当前版本存在一个更严重的问题：

> **页面可以把“已经抓到的内容”解释得很好，但不能稳定保证“最近最重要的事情已经进入候选池”。**

这会直接伤害项目第一优先级：

> **帮助读者快速知道最近具身智能真正发生了哪些重要变化。**

典型回归案例：

- AMD 收购 World Labs 这类涉及 **spatial intelligence / world models / physical AI / robotics / simulation / compute stack** 的重大结构性事件，如果没有进入最终候选池，即使后续网页、Impact Radar、论文解读做得再精美，整期周刊仍然会让读者觉得“没有抓住最近的重点”。

因此 V0.4 暂时冻结大部分展示层工作，把主要精力放到：

```text
Discovery
↓
Major News Audit
↓
Editorial Gate
↓
Deep Research
↓
Impact Analysis
↓
Writing / Render
```

本次必须先把前三层做好。

---

# 1. 产品优先级保持不变

项目内容优先级继续按照：

## A. 第一优先级：最近真正重要的事情和趋势

## B. 第二优先级：这些变化对真实应用与教育意味着什么

## C. 第三优先级：研究启示与论文脉络

因此：

> **重大产业 / 技术事件不能因为“不是论文”或“不在固定机器人公司列表”而漏掉。**

论文是重要证据源，但不天然拥有最高优先级。

---

# 2. 本次不要继续“美化页面”

除非为适配新的数据字段必须修改，否则：

- 不重新设计 Hero；
- 不大改 CSS；
- 不更换整体视觉语言；
- 不新增复杂动效；
- 不投入大量时间调整卡片；
- 不重新做一套前端框架；
- 不引入 React / Vue 等重型前端；
- 不做社交媒体分发。

现有网页结构基本冻结。

本次成功标准首先是：

> **重大新闻发现率明显提高。**

---

# 3. 重构思路：Discovery 与 Verification 分开

当前系统容易把：

> “优先使用一手来源”

误解成：

> “主要依赖一手来源发现新闻”。

这两个阶段必须拆开。

## 3.1 Discovery：广泛发现

Discovery 阶段允许使用：

- Reuters
- Financial Times
- Bloomberg
- TechCrunch
- IEEE Spectrum
- The Robot Report
- VentureBeat
- 主流科技媒体
- 高质量机器人行业周报 / Digest
- 国内高质量科技 / 产业媒体
- 公司官方博客
- 官方社交账号
- GitHub
- 学术社区
- 高校 / 政府官网

其目的只有一个：

> **尽可能发现“最近两周不能错过的事情”。**

Discovery 来源不一定成为最终引用来源。

## 3.2 Verification：回到一手资料

候选事件进入 Major News Candidate 后，再优先回到：

1. 公司官方公告；
2. 官方新闻稿；
3. 官方技术博客；
4. SEC / 监管 / 政府文件；
5. 原始论文；
6. 官方 GitHub / Project Page；
7. 高校 / 政府官网。

最终周刊重大结论优先引用一手来源。

如果一手资料不可获得，可以保留高质量媒体来源，但必须标注。

---

# 4. 新增独立的“最近 14 天开放发现”阶段

每一期 Weekly 在处理固定数据源之前或同时，必须执行一次：

```text
Open Discovery Window = 最近 14 天
```

例如 W40 人工回归测试可以使用：

```text
2026-09-21 ～ 2026-10-04
```

或按照实际运行日：

```text
today - 13 days ～ today
```

14 天窗口的目的：

> **发现本周 + 上周仍然重要的新变化。**

它与 30–60 天 Major Event Memory 作用不同。

---

# 5. Discovery 必须覆盖的主题

不要只做一个泛化搜索。

至少按以下主题分别进行发现。

## 5.1 M&A / Capital / Strategic Moves

关键词示例：

```text
embodied AI acquisition
robotics acquisition
physical AI acquisition
spatial intelligence acquisition
robotics funding
humanoid funding
embodied AI funding
robotics merger
physical AI investment
机器人 收购
具身智能 并购
机器人 融资
具身智能 融资
```

重点捕捉：

- 收购；
- 合并；
- 大额融资；
- 战略投资；
- 芯片 / 云 / AI 巨头进入具身智能；
- 重要研究团队被收购或整合。

## 5.2 Models / Foundation Models / World Models

关键词示例：

```text
robot foundation model
VLA robotics
world model robotics
physical AI model
spatial intelligence model
robotics generalist policy
embodied foundation model
机器人 基础模型
VLA 机器人
世界模型 机器人
空间智能
具身大模型
```

## 5.3 Robot Products / Platforms

关键词示例：

```text
humanoid robot launch
robotics platform launch
robot hand launch
robot arm launch
robotics compute platform
humanoid product
机器人 新产品
人形机器人 发布
机械臂 发布
灵巧手 发布
机器人 平台
```

## 5.4 Real Deployment / Orders / Operations

关键词示例：

```text
robot deployment factory
humanoid deployment warehouse
robotics commercial deployment
robot order humanoid
robot fleet deployment
机器人 批量部署
人形机器人 订单
机器人 工厂 部署
机器人 门店 部署
具身智能 商业化
```

## 5.5 Benchmarks / Real Robot Evaluation

关键词示例：

```text
robotics benchmark real robot
humanoid benchmark
VLA benchmark real robot
physical AI benchmark
robot generalization evaluation
机器人 benchmark
真机 评测
具身智能 基准
机器人 泛化 评测
```

## 5.6 Compute / Simulation / Infrastructure

关键词示例：

```text
physical AI GPU
robotics compute platform
robotics simulation platform
Isaac robotics
robotics edge inference
spatial intelligence compute
机器人 推理
机器人 算力
机器人 仿真
具身智能 计算平台
```

这一类非常重要。

**不要只盯传统机器人公司。**

可能改变具身智能行业的重要事件也可能来自：

- AMD
- NVIDIA
- Microsoft
- AWS
- Google
- Meta
- 芯片公司
- 云计算公司
- 空间智能公司
- 仿真公司
- 数据公司

## 5.7 Open Source / Dataset / Tooling

关键词示例：

```text
robotics open source release
robotics dataset release
VLA open source
robot simulation open source
LeRobot release
ROS robotics release
机器人 开源
具身智能 数据集
机器人 数据集
机器人 仿真 开源
```

## 5.8 Policy / Standards

包括：

- 国家政策；
- 行业规划；
- 机器人标准；
- AI / physical AI 监管；
- 产业专项计划；
- 重大政府采购 / 示范工程。

## 5.9 Education / Talent

包括：

- 新专业；
- 微专业；
- 培养方案；
- 国家级教学标准；
- 公开课程；
- 重要实验教学项目；
- 人才培养政策。

---

# 6. 新增“相邻领域重大事件”发现机制

这是 V0.4 的关键。

重大具身智能事件未必使用：

```text
embodied AI
robotics
humanoid
```

这些明显关键词。

还可能使用：

```text
physical AI
spatial intelligence
world model
3D world model
interactive world model
simulation
agentic robotics
real-world AI
robot learning
action model
```

因此 Discovery 阶段必须允许：

> **从相邻领域发现可能影响具身智能的结构性事件。**

如果事件涉及：

- 空间智能；
- 世界模型；
- 仿真；
- 机器人计算；
- 物理世界 AI；
- 实时推理；
- 3D / physical reasoning；

即使新闻标题没有“robot”或“embodied”，也要进入相关性二次判断。

---

# 7. 建立 Entity Watchlist，但不能只依赖 Watchlist

新增或扩展：

```text
config/entity_watchlist.yaml
```

至少分成以下几类。

## 7.1 Foundation / Model / Research

示例：

- Physical Intelligence
- World Labs
- Google DeepMind
- OpenAI
- Skild AI
- Figure AI
- Microsoft Research / Physical AI
- NVIDIA Research
- Meta AI（如与 physical / spatial / robotics 直接相关）

## 7.2 Robot Companies

示例：

- Boston Dynamics
- Agility Robotics
- Apptronik
- 1X
- Figure
- Tesla / Optimus
- Unitree / 宇树
- 智元机器人
- 银河通用
- 优必选
- 傅利叶智能
- 其他重要企业

## 7.3 Infrastructure / Compute / Simulation

示例：

- NVIDIA
- AMD
- Hugging Face Robotics
- Isaac
- ROS
- MoveIt
- MuJoCo
- LeRobot
- Genesis
- ManiSkill

## 7.4 Education / Policy

维护重要主管部门和高校。

## 7.5 Watchlist 之外仍必须开放发现

重要规则：

> **Watchlist 是最低覆盖，不是搜索边界。**

如果 Reuters、主流科技媒体、机器人行业媒体等出现：

- 大额并购；
- 大额融资；
- 重大产品发布；
- 重大战略合作；
- 重大真实部署；

即使实体不在 Watchlist，也必须进入候选池。

---

# 8. 新增“Major Event Scoring”，不要复用论文评分

重大新闻与论文的价值判断完全不同。

新增：

```text
config/editorial_scoring.yaml
```

建议 Major Event 评分：

## Strategic Impact｜战略影响：30%

是否可能改变：

- 行业格局；
- 竞争关系；
- 技术栈；
- 关键资源；
- 产业链位置。

## Cross-Ecosystem Impact｜跨生态影响：20%

影响范围是：

- 单一产品；
- 单一公司；
- 还是模型 + 硬件 + 仿真 + 开发生态 + 应用？

## Event Scale｜事件规模：15%

参考：

- 并购金额；
- 融资规模；
- 部署数量；
- 订单；
- 客户覆盖；
- 平台用户规模；
- 政策层级。

不能机械以金额排序，但规模应作为信号。

## Technical Significance｜技术意义：15%

是否可能改变：

- robot learning；
- control；
- simulation；
- deployment；
- data；
- inference；
- hardware capability。

## Evidence Quality｜证据质量：10%

优先：

```text
官方 + 多来源确认
>
官方单方披露
>
高质量媒体
>
二手消息
```

## Freshness / Momentum｜新鲜度与后续性：10%

最近是否：

- 刚发生；
- 有新进展；
- 引发后续产业反应；
- 仍在持续发酵。

---

# 9. Major Event 分级

## S 级

满足其中之一：

- 明显改变行业结构；
- 头部企业重大收购 / 战略动作；
- 重大模型 / 平台发布；
- 大规模真实部署；
- 国家级政策；
- 具备跨生态影响。

通常：

> 过去 2 周内出现 S 级事件，原则上必须进入首页 / Top Stories。

## A 级

重要，但影响范围或证据尚小于 S。

通常进入：

- 10 分钟速读；
- Recent Major；
- Industry / Tech。

## B 级

有价值，但主要服务特定读者。

适合：

- Industry Brief；
- Open Source；
- Research Radar；
- Resource Index。

---

# 10. 新增“Editorial Audit”，先选题，再写网页

这是 V0.4 最重要的人工闸门。

每次生成最终周刊之前，先生成：

```text
runs/YYYY-WXX/EDITORIAL_AUDIT.md
```

## 10.1 第一部分：最近 14 天 Top 15 候选

每条必须包括：

```text
Rank
Title
Date
Category
Entity
Proposed Tier: S / A / B
Why it may matter
Primary source
Discovery source(s)
Related application areas
Confidence
```

## 10.2 第二部分：最近 30–60 天仍要记住的事件

列出：

- S 级；
- A 级；
- 当前状态；
- 本周是否有新进展；
- 是否建议继续出现在正文。

## 10.3 第三部分：可能被遗漏的大新闻

主动回答：

> 主流新闻 / 行业媒体最近两周报道了哪些具身智能或相邻领域大事，但当前候选池尚未收录？

如果找到：

必须补入候选池再评分。

## 10.4 第四部分：建议进入本期首页的 Top 5

Codex 给出建议：

```text
Top 1
Top 2
Top 3
Top 4
Top 5
```

每条用 2–3 句解释：

> 为什么它比其他候选更值得放首页。

## 10.5 第五部分：建议降级 / 排除的重要候选

这是避免“什么都塞进去”的关键。

例如：

```text
Candidate
Decision: downgrade / exclude
Reason
```

理由可以包括：

- 只是公司 PR；
- 规模小；
- 缺乏真实证据；
- 和上周重复；
- 对具身智能影响弱；
- 更适合论文区而非 Top Story。

---

# 11. 增加人工 Selection 文件

Audit 完成后生成：

```text
runs/YYYY-WXX/editorial_selection.yaml
```

示例：

```yaml
issue: 2026-W40

top_stories:
  - id: event_xxx
    selected: true
    tier: S
    order: 1

briefing:
  - id: event_yyy
    selected: true

recent_major:
  - id: event_zzz
    selected: true

exclude:
  - id: event_abc
    reason: "insufficient evidence"
```

维护者可以人工修改。

最终网页生成必须优先读取：

```text
editorial_selection.yaml
```

而不是完全依赖自动排序。

---

# 12. 最终网页前增加“人工闸门”

理想手动流程：

```text
discover
↓
normalize / dedup
↓
major-news-audit
↓
EDITORIAL_AUDIT.md
↓
人工查看 3–5 分钟
↓
修改 editorial_selection.yaml
↓
deep research
↓
impact analysis
↓
render
```

当前阶段：

> **不要跳过 Audit 直接生成正式周刊。**

---

# 13. 新增 CLI

根据现有 CLI 结构合理适配，目标是支持类似：

```bash
eio discover   --start 2026-09-21   --end 2026-10-04
```

生成 Discovery 候选。

```bash
eio audit   --week 2026-W40
```

生成：

```text
EDITORIAL_AUDIT.md
editorial_selection.yaml
```

```bash
eio report   --week 2026-W40   --selection runs/2026-W40/editorial_selection.yaml
```

生成最终网页。

名称可按照当前工程实际调整。

---

# 14. 建立 Major News Regression Test

当前 W40 作为第一个回归测试样本。

新增类似：

```text
tests/fixtures/major_news_regression_2026w40.yaml
```

## 14.1 必须召回的事件

至少将以下事件作为回归样本。

### AMD / World Labs

事件：

> AMD 收购 World Labs。

要求：

- Discovery 必须发现；
- 必须进入候选池；
- 必须进入 Major News Audit；
- 应被评估为高优先级重大事件；
- 必须回到 AMD / World Labs 官方资料核验；
- 需要判断其与：
  - spatial intelligence
  - world models
  - physical AI
  - robotics
  - simulation
  - compute
  的关系。

**如果该事件在 2026-W40 回归中完全未被发现，则 V0.4 核心验收失败。**

注意：

> 这个测试的目的不是长期硬编码 AMD 新闻，而是验证系统能否召回“来自机器人相邻领域、但对 physical AI / embodied intelligence 具有结构性影响”的重大事件。

## 14.2 当前页面已经捕获的事件作为正样本

同时验证系统仍然能够发现类似：

- Figure 家庭泛化评测；
- Digit 5 / FORT 安全合作；
- 智元较大规模部署；
- Isaac Lab / Isaac ROS 重要更新；
- Atlas 制造场景 / 手部更新；
- 重要机器人标准。

不要求这些全部都必须进 Top 5。

要求：

> 它们应该进入候选池，并由编辑评分决定最终层级。

---

# 15. 再增加 2 个“探索性检查样本”

以下事件不强制一定进入最终 Top Story，但必须验证 Discovery 是否有能力发现。

## 15.1 Physical AI / Edge / Cloud Inference

检查最近 14–30 天：

- 机器人推理；
- edge/cloud inference；
- physical AI toolchain；
- robot compute。

如果存在高质量官方 / 主流来源，应进入候选池。

## 15.2 Robot Foundation Model / Generalist Policy

检查：

- Skild；
- Physical Intelligence；
- Figure；
- DeepMind；
- 其他重要模型。

重点判断：

> 最近是否有比单纯“客户数 / ARR”更重要的模型或技术发布。

同一家公司同时有：

- 财务新闻；
- 模型发布；
- 产品发布；

系统必须能够判断：

> 哪一条更值得具身智能读者关注。

---

# 16. 不设置机械“栏目配额”

不要强制：

```text
产业必须 2 条
论文必须 2 条
教育必须 1 条
```

这会导致低价值内容占位置。

正确原则：

> **先按重要程度选，再保证读者能够理解这些事件横跨哪些方向。**

如果最近两周最大的五件事全部来自产业 / 模型，也允许首页全部是这些内容。

论文放到 Research / Papers 区继续服务深读。

---

# 17. Top Stories 的编辑规则

Top Story 必须至少满足：

- S / 高 A 级；
- 证据可靠；
- 对行业理解有明显价值；
- 不是普通 Release；
- 不只是论文 novelty；
- 具有较强时效性或持续影响。

过去 14 天如果存在 S 级：

> S 级优先于普通论文进入 Top Stories。

---

# 18. 对“30 天重大事件”增加状态管理

继续使用：

```text
data/major_events.json
```

建议状态：

```text
new
developing
stable
resolved
archived
```

每周更新：

```text
what_changed_since_last_issue
```

避免：

> 同一事件每周原样复制。

---

# 19. Discovery Query 配置化

新增：

```text
config/discovery_queries.yaml
```

按类别维护：

```yaml
capital:
  en:
    - ...
  zh:
    - ...

models:
  en:
    - ...
  zh:
    - ...

deployment:
  ...

infrastructure:
  ...

education:
  ...
```

不要把所有搜索词散落在代码里。

---

# 20. 记录 Discovery 过程

为了之后分析“为什么漏新闻”，每次运行保存：

```text
runs/YYYY-WXX/discovery_log.json
```

至少记录：

```json
{
  "query": "",
  "category": "",
  "time_window": "",
  "results_seen": 0,
  "candidates_added": 0,
  "duplicates": 0,
  "errors": []
}
```

不要记录秘密 token。

---

# 21. 增加“新闻召回率”人工评估

当前无法计算真正完整的 Recall，但连续人工运行期间可以维护一个简单指标。

每期维护者可以向：

```text
runs/YYYY-WXX/manual_major_news_check.yaml
```

补充：

```yaml
known_major_events:
  - title: ...
    found_by_pipeline: true
    final_selected: true

missed_events:
  - title: ...
    reason: ...
```

连续 3–4 周以后重点看：

- 人工认为明显重要的新闻，有多少被自动发现；
- 哪类新闻最容易漏；
- 哪类 Discovery Query 最有效。

---

# 22. 失败条件

以下任一情况视为本次任务未完成：

## P0-1

AMD / World Labs 回归事件仍然无法被 Discovery 找到。

## P0-2

系统仍然主要依赖固定 `sources.yaml`，没有开放式 Discovery。

## P0-3

Major News Audit 仍然只是普通 Collector 的别名。

## P0-4

没有生成独立的 `EDITORIAL_AUDIT.md`。

## P0-5

最终页面仍然可以绕过 Selection / Audit 直接自动选出所有重点新闻，而人工无法方便调整。

---

# 23. 本次不要求修改 DeepSeek 文案润色

DeepSeek 润色不属于本次主要问题。

本轮：

- 保留现有文风；
- 不做大规模中文改写；
- 不因润色改变事实；
- 不花主要时间调标题语气。

等 Major News Recall 稳定以后再继续优化文风。

---

# 24. 页面只做必要的小调整

如果需要，可以增加一个很小的标记：

```text
S · Major
A · Important
B · Brief
```

但不要让评分占据读者注意力。

内部评分可以隐藏。

---

# 25. W40 回归执行要求

实现完成后，请重新跑一次：

```text
2026-W40
```

Discovery 重点覆盖：

```text
2026-09-21 ～ 2026-10-04
```

Major Memory 可以回看：

```text
2026-09-05 ～ 2026-10-04
```

---

# 26. 本轮不要一开始重写整期网页

执行顺序必须是：

## Step 1

改造 Discovery。

## Step 2

生成 W40：

```text
EDITORIAL_AUDIT.md
```

## Step 3

确认 AMD / World Labs 等重大事件是否出现。

## Step 4

生成：

```text
editorial_selection.yaml
```

## Step 5

再使用现有 renderer 生成新版 W40。

不要先花几个小时重新设计网页后才检查候选新闻。

---

# 27. Codex 完工报告

必须输出：

## A. 原系统为什么会漏掉重大新闻

结合代码和数据流解释。

不要只复述任务说明。

## B. Discovery 做了哪些改变

列出：

- 新查询；
- 新数据源类型；
- 新配置；
- 新 CLI。

## C. AMD / World Labs 回归测试

明确说明：

```text
discovered?
discovery source?
primary source found?
tier?
final editorial recommendation?
```

## D. W40 Top 15 Candidate

列出排名。

## E. 哪些当前页面事件被降级

解释原因。

## F. 哪些新事件被补进候选池

尤其说明：

> 原系统为什么没发现。

## G. Major News Audit

提供文件路径。

## H. Editorial Selection

提供文件路径。

## I. 新版 W40

提供网页路径与截图。

但：

> 页面截图不是本轮最重要的验收项。

## J. 当前新闻发现能力仍有哪些盲区

例如：

- 付费媒体；
- X / LinkedIn；
- 中国媒体访问；
- 搜索引擎限制；
- 网站反爬；
- 地区限制。

## K. P0 / P1 / P2

列出后续改进。

---

# 28. 最终验收问题

V0.4 做完后，先不要问：

> 页面漂不漂亮？

先回答：

### Q1

如果一个长期关注具身智能的人过去两周完全没看新闻，打开我们的 Editorial Audit：

> 他最不应该错过的事情是否基本都在？

### Q2

如果主流媒体都在讨论一个重大 physical AI / spatial intelligence / robotics 事件：

> 即使它来自 AMD、Microsoft、云厂商或相邻领域，我们能否发现？

### Q3

如果一个事件没有进入最终 Top Story：

> 我们能否清楚解释它为什么被降级？

### Q4

如果下一周人工发现漏了一件大事：

> 我们能否从 discovery log 追查漏掉的原因，并修改 Query / Watchlist / Ranking？

只有这些问题大体回答“是”，再继续做自动化。

---

# 29. 本阶段最终目标

V0.3 已经基本解决：

> “怎么把内容做成一份能看的网页。”

V0.4 要优先解决：

> **“怎么保证我们首先抓到了值得看的内容。”**

请把工程注意力从：

```text
presentation optimization
```

暂时转向：

```text
major-news recall
editorial judgment
traceable selection
```

本轮最重要的衡量标准：

> **如果最近两周发生了一件足以影响具身智能行业理解的大事，系统应该大概率先把它放到编辑桌上。**
