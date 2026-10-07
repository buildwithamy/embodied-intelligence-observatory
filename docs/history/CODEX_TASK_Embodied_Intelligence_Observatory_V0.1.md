# Codex 执行任务：Embodied Intelligence Observatory V0.1（人工运行验证版）

> 仓库：`embodied-intelligence-observatory`  
> 项目中文名：**具身智能观察站**  
> 当前阶段：**先人工运行 3–4 周，验证内容质量与流程稳定性，再考虑云端自动化。**

---

## 0. 这次任务最重要的约束

本阶段**不要做定时云端自动化**。

请不要：

- 创建按周自动执行的 GitHub Actions Cron；
- 创建自动发布到 GitHub Pages 的定时任务；
- 创建自动提交周报的无人值守流程；
- 创建微信公众号、小红书、X/Twitter、邮件自动分发；
- 追求“完全无人值守”。

当前目标是先完成一个：

> **可以由仓库维护者手动运行、使用真实数据、稳定生成高质量周报的 MVP。**

未来连续运行 3–4 周、人工确认质量稳定后，再单独设计云端自动执行任务。

可以为未来自动化预留清晰接口，但本次不要实现自动调度。

---

# 1. 项目定位

请在当前 GitHub 仓库中搭建：

# Embodied Intelligence Observatory

中文：

# 具身智能观察站

它是一个持续跟踪具身智能领域的重要研究、技术、产业、开源生态和教育发展的公开信息项目。

项目面向：

- 具身智能从业者
- 机器人算法工程师
- AI / Robotics 研究者
- 高校教师
- 本科生、研究生
- 职业教育教师
- 具身智能相关专业学生
- 产品经理
- 产业研究人员
- 对具身智能有系统学习需求的技术人员

项目中的核心内容产品暂定为：

> **Embodied Intelligence Weekly**  
> **具身智能周报**

但仓库本身不要局限成“周报仓库”。

未来可以逐渐扩展为：

```text
Embodied Intelligence Observatory
├── Weekly
├── Papers
├── Industry
├── Open Source
├── Education
└── Resources
```

当前 V0.1 只需要把“每周信息采集 → 筛选 → 深读 → 周报生成”主链路跑通。

---

# 2. 当前阶段目标

请完成一个真正可运行的人工触发版 MVP。

至少实现：

1. 获取指定时间范围内的具身智能相关论文；
2. 同时使用：
   - `jiangranlv/robotics_arXiv_daily`
   - Hugging Face Daily Papers
3. 对论文进行标准化与去重；
4. 收集一批稳定的：
   - 企业动态
   - 技术动态
   - 开源项目
   - 教育动态
   - 政策信息
5. 建立统一候选信息池；
6. 对候选内容进行分类、筛选和评分；
7. 对重点论文与重大事件进行进一步阅读；
8. 自动生成一份中文 Markdown 周报草稿；
9. 所有内容保留来源；
10. 支持本地 / Codex 手动执行；
11. 支持 Dry Run；
12. 有基本单元测试和集成测试；
13. 生成一份真实数据周报进行端到端验证；
14. 完成 README 和架构说明。

当前优先级：

> **准确性 > 稳定性 > 可追溯性 > 可维护性 > 功能数量**

---

# 3. 当前阶段暂不实现

V0.1 明确不做：

- GitHub Actions 定时 Cron
- 无人值守自动发布
- GitHub Pages 自动更新
- 微信公众号自动发布
- 小红书自动发布
- X / Twitter 自动发布
- 邮件订阅系统
- 用户系统
- 推荐系统
- React 重型前端
- 数据库集群
- Redis
- Kubernetes
- 向量数据库
- 大规模 Multi-Agent
- 为了“看起来高级”而引入复杂 Agent Framework

如果某些 GitHub Actions 对 CI 测试很有帮助，可以保留**非定时的普通 CI**，但不要加入周期调度。

---

# 4. 项目核心原则

整个项目需要长期遵循：

## 4.1 确定性程序优先

以下任务优先用普通 Python 完成：

- API 请求
- RSS 获取
- GitHub API
- JSON 处理
- HTML 解析
- arXiv ID 提取
- URL 标准化
- 标题标准化
- 去重
- 时间过滤
- 文件读写
- 缓存
- Schema Validation
- 日志

不要浪费 LLM 做这些明确可编程的工作。

---

## 4.2 LLM 负责真正需要理解的部分

模型主要负责：

- 是否属于具身智能
- 内容分类
- 论文理解
- 新闻理解
- 技术重要性判断
- 产业意义判断
- 教育意义判断
- 多来源综合
- 深度摘要
- 局限分析
- 周报编辑
- 辅助事实检查

---

## 4.3 Primary Source First

来源优先级：

1. 原始论文
2. 官方 Project Page
3. 官方 GitHub
4. 官方技术报告
5. 公司官方博客 / Newsroom
6. 政府 / 教育主管部门
7. 高校官网
8. 高质量专业媒体
9. 普通媒体
10. 社交媒体

社交媒体可以作为线索。

重大结论尽量继续回到一手来源核实。

---

## 4.4 Evidence Before Conclusion

不能因为：

- 一个 demo
- 一篇论文
- 一条公司宣传
- 一个 viral 视频

就直接下“行业已经进入新阶段”这类大结论。

要区分：

- 已验证事实
- 作者主张
- 官方声明
- 媒体报道
- 编辑观察
- 尚待验证

---

## 4.5 Quality Before Quantity

不要求每期必须凑满固定条数。

如果本周只有 5 篇论文真正值得推荐，就只写 5 篇。

如果没有重要教育新闻，也不要为了栏目完整而加入普通招生宣传。

---

# 5. 内容覆盖范围

---

## 5.1 产业与公司

重点跟踪：

### 国际

- OpenAI
- Google DeepMind
- NVIDIA
- Physical Intelligence
- Skild AI
- Figure
- Agility Robotics
- Tesla Robotics
- Boston Dynamics
- 1X
- Apptronik

### 国内

- 宇树科技
- 智元机器人
- 银河通用
- 傅利叶智能
- 优必选
- 以及出现重大技术、产品或商业进展的公司

重点事件：

- 新机器人
- 新模型
- 新平台
- 新产品
- 技术报告
- benchmark
- 真实机器人评测
- 商业部署
- 订单
- 大规模采购
- 融资
- 并购
- 战略合作
- 重要人员 / 组织变化
- 影响行业的重要芯片与算力平台变化

普通品牌宣传降低权重。

---

# 6. 技术与开源生态

重点技术方向：

- VLA
- VLM for Robotics
- World Models
- Action Models
- Spatial Intelligence
- Robot Learning
- Imitation Learning
- Reinforcement Learning
- Manipulation
- Dexterous Manipulation
- Humanoid Robotics
- Locomotion
- Navigation
- Vision
- RGB-D
- Tactile Sensing
- Multimodal Perception
- Sim2Real
- Robot Data
- Synthetic Data
- Teleoperation
- Motion Planning
- Trajectory Generation
- IK
- Force Control
- Contact-rich Manipulation
- Long-horizon Tasks
- Planning
- Memory
- Multi-Robot Systems
- Robot Safety

重点生态：

- ROS 2
- MoveIt
- MuJoCo
- Isaac Sim
- Isaac Lab
- Genesis
- LeRobot
- ManiSkill
- LIBERO
- RoboSuite
- RoboDojo
- Open X-Embodiment
- BridgeData
- Hugging Face Robotics
- 其他出现重要更新的项目

重点关注：

- Release
- Breaking Changes
- 新模型
- 新数据集
- benchmark
- 工具链变化
- API 变化
- 新开源项目
- 开源协议变化
- 明显提升机器人开发效率的新能力

---

# 7. 论文来源

论文部分至少使用两个主要来源。

---

## 7.1 robotics_arXiv_daily

来源仓库：

`jiangranlv/robotics_arXiv_daily`

目标：

获取指定日期区间内真正新增的具身智能相关论文。

优先研究：

- 仓库更新方式
- commit diff
- 按日期组织方式
- arXiv ID

不要每次重新把整个 README 历史记录当成“新论文”。

记录至少包括：

```text
title
authors
date
arxiv_id
arxiv_url
abstract
source
```

---

## 7.2 Hugging Face Daily Papers

获取指定日期范围内的 Hugging Face Daily Papers。

尽量记录：

```text
title
authors
date
arxiv_id
paper_url
project_url
github_url
community_popularity
source
```

注意：

> Hugging Face 热度只能作为“社区关注度信号”。

不能把 upvotes / popularity 直接等价成论文质量。

---

# 8. 论文筛选边界

纳入：

- VLA
- 机器人基础模型
- World / Action Models
- Robot Learning
- Imitation Learning
- Reinforcement Learning
- Manipulation
- Dexterous Manipulation
- Humanoid
- Navigation
- Locomotion
- Robot Data
- Sim2Real
- Robot Safety
- Spatial Intelligence
- 3D Perception
- Tactile
- Multimodal Perception
- Long-horizon Task
- Planning
- Memory
- Multi-Robot
- Robotics Benchmark

VLM 论文只有在与以下内容存在直接关系时纳入：

- robot
- 3D / spatial intelligence
- physical world interaction
- embodied agent
- manipulation
- navigation

以下通常不纳入：

- 普通纯 LLM
- 纯 NLP
- 纯图像生成
- 与机器人无直接关联的普通 VLM
- 与物理世界交互无关的 Agent 论文

---

# 9. 论文去重

优先使用：

```text
arXiv ID
```

作为论文唯一标识。

无 arXiv ID 时再尝试：

1. DOI
2. canonical URL
3. normalized title

同一篇论文最终只保留一个 Candidate。

但必须保存来源列表，例如：

```json
{
  "sources": [
    "robotics_arxiv_daily",
    "huggingface_daily"
  ]
}
```

同时被两个来源收录可以作为一个弱关注度信号，但不要直接决定最终排名。

---

# 10. 教育与人才培养

这是项目的重要特色，不能被“论文周报”淹没。

---

## 10.1 国内

重点关注：

- 教育部
- 工信部
- 人社部
- 职业教育相关主管部门
- 普通本科
- 职业本科
- 高职院校

关注主题：

- 具身智能专业
- 机器人工程
- 人工智能
- 智能机器人
- 机器人相关微专业
- 培养方案
- 专业标准
- 课程体系
- 教材
- 精品课程
- 实验教学
- 虚拟仿真实验
- 实训基地
- 产教融合
- 专业建设
- 教学改革
- 人才培养政策

不要把普通招生新闻当成重要教育动态。

---

## 10.2 国际

关注：

- Stanford
- MIT
- Berkeley
- CMU
- ETH Zurich
- Georgia Tech
- University of Michigan
- Imperial College
- Oxford
- Cambridge
- 以及其他机器人教育强校

重点关注公开：

- Robotics Course
- Embodied AI Course
- Robot Learning Course
- Manipulation Course
- Labs
- Assignments
- Lecture Notes
- Open-source Teaching Resources

---

# 11. “大新闻兜底”机制

请设计 Big News Watchlist。

即使普通评分没有进入 Top Rank，以下事件也必须进行二次检查：

- 头部公司重大模型发布
- 重大机器人产品发布
- 重要 benchmark
- 大型真实机器人评测
- 重大融资
- 重大收购
- 大规模产业订单
- 重大开源项目发布
- 国家级政策
- 国家级产业规划
- 高校正式开设具身智能相关专业
- 重要专业培养标准
- 影响具身智能行业的重要芯片 / 计算平台变化

建议配置：

```text
config/watchlist.yaml
```

不要把主要 watchlist 大量硬编码到 Python。

---

# 12. 数据模型

建立统一 Candidate Schema。

可采用 Pydantic 或类似方式验证。

建议字段：

```json
{
  "id": "",
  "title": "",
  "url": "",
  "canonical_url": "",
  "published_at": "",
  "retrieved_at": "",
  "source_type": "",
  "sources": [],
  "authors": [],
  "organizations": [],
  "categories": [],
  "tags": [],
  "arxiv_id": "",
  "doi": "",
  "github_url": "",
  "project_url": "",
  "abstract": "",
  "raw_summary": "",
  "analysis": "",
  "technical_score": 0,
  "industry_score": 0,
  "education_score": 0,
  "reproducibility_score": 0,
  "evidence_score": 0,
  "overall_score": 0,
  "status": "",
  "evidence": [],
  "notes": []
}
```

允许根据工程实现合理调整。

但不要删除：

- 原始来源
- 发布时间
- 获取时间
- 来源列表
- evidence

---

# 13. 评分体系

建议采用五维评分。

每项：

```text
0–5
```

---

## Technical Importance

技术贡献与新颖性。

---

## Industry Impact

是否可能影响：

- 产品
- 企业
- 工程实践
- 部署
- 商业模式
- 产业链

---

## Evidence Quality

证据可靠程度。

例如：

```text
原始论文 / 官方报告
>
官方项目 / 官方 GitHub
>
高质量媒体
>
普通媒体
>
社交媒体
```

---

## Reproducibility / Availability

是否存在：

- Code
- Model
- Dataset
- Project Page
- Benchmark
- 可复现实验

---

## Education Value

是否对以下群体有明显价值：

- 学生
- 教师
- 课程建设者
- 初入具身智能的人
- 工程实践者

评分权重放在：

```text
config/scoring.yaml
```

不要把权重大量散落在代码中。

---

# 14. 事实与判断严格分开

这是编辑质量的核心规则。

例如：

### 作者报告

> 作者在 LIBERO 某 benchmark 上报告了 XX 指标。

### 周报观察

> 当前结果显示该方法在该 benchmark 上具有竞争力，但真实机器人、长时序任务和跨环境泛化仍需要继续验证。

不能直接写：

> 该方法已经解决机器人泛化问题。

内容中尽量区分：

- Paper reports
- Company says
- Official release
- Media reports
- Observatory note
- Still unclear

中文正文可以自然表达，不一定必须机械使用英文标签。

---

# 15. 禁止事项

生成内容不得：

1. 编造论文；
2. 编造作者；
3. 编造 benchmark；
4. 编造性能提升数字；
5. 编造公司发布；
6. 仅根据标题解释论文；
7. 把 PR 宣传直接当成熟技术事实；
8. 把 demo 写成成熟商业系统；
9. 根据单篇论文直接宣布行业趋势；
10. 为了凑数加入低价值内容；
11. 大段复制论文 abstract；
12. 大段复制新闻正文；
13. 把 AI 推理冒充官方结论；
14. 隐藏无法验证的信息。

如果无法确认，应明确写：

> 尚未找到足够的一手资料验证。

---

# 16. 周报结构

输出目录建议：

```text
reports/YYYY/YYYY-WXX.md
```

同时维护：

```text
latest.md
```

但在当前人工验证阶段：

> `latest.md` 的更新也通过手动运行命令完成。

---

## 推荐模板

```markdown
# Embodied Intelligence Weekly

具身智能周报 · YYYY 年第 XX 周

时间范围：

YYYY-MM-DD ～ YYYY-MM-DD
```

---

## 本周速览

3–5 条。

要求：

尽量总结“这一周发生了什么变化”，而不是简单罗列新闻标题。

---

## 01｜本周焦点

选择 3–5 个真正重要事件。

每项包括：

### 发生了什么

### 为什么值得关注

### 已确认的信息

### 仍需观察

### Sources

---

## 02｜产业与公司

约 5–10 条。

宁缺毋滥。

---

## 03｜技术与开源

关注：

- 模型
- 框架
- 工具
- 数据集
- benchmark
- GitHub Release
- Robotics Platform

---

## 04｜本周论文精选

建议：

约 5–12 篇。

不要硬凑。

其中最重要的约 3–5 篇做较深入分析。

每篇至少包括：

### 中文标题

English Title

**研究问题**

**核心方法**

**主要结果**

**为什么值得关注**

**局限与待验证问题**

**Links**

- Paper
- Project
- Code

标签示例：

```text
VLA
Manipulation
World Model
Humanoid
RL
Robot Data
Sim2Real
```

---

## 05｜教育与人才培养

包括：

- 专业建设
- 微专业
- 课程
- 教材
- 培养方案
- 教育政策
- 实训平台
- 开放课程
- 教学资源

面向公共读者。

不要写任何仓库维护者个人公司的内部课程情况。

---

## 06｜本周值得继续观察

3–5 项。

特点：

- 当前信息还不足；
- 但值得继续关注；
- 明确写清楚“为什么暂时不能下结论”。

---

## 07｜资源索引

分类整理：

### Papers

### Code

### Dataset

### Models

### Courses

### Reports

### Policy

---

# 17. 来源覆盖报告

每一期周报生成后，同时生成一个机器可读或 Markdown Run Manifest。

建议：

```text
runs/YYYY-WXX.json
```

至少记录：

```text
run_time
date_range
sources_attempted
sources_success
sources_failed
raw_items
normalized_items
deduplicated_items
candidate_items
selected_items
papers_selected
news_selected
education_selected
warnings
```

这样连续运行 3–4 周以后，可以判断：

- 哪些源稳定；
- 哪些源经常失效；
- 哪些栏目经常缺数据；
- 每周处理量是否合理；
- AI 调用是否过多。

---

# 18. 数据源策略

第一版不要一次接入几十个脆弱网页。

优先：

1. 官方 API
2. RSS
3. GitHub API
4. 稳定静态页面
5. 官方 Newsroom

如果必须解析网页：

- 独立 Collector；
- 保留异常处理；
- 网页改版不能拖垮全部流程。

建议：

```text
config/sources.yaml
```

字段可以包括：

```yaml
name:
type:
url:
category:
priority:
enabled:
reliability:
notes:
```

---

# 19. 第一批数据源策略

V0.1 必须优先跑通：

### Papers

- robotics_arXiv_daily
- Hugging Face Daily Papers

### Open Source

先选择少量高价值项目，例如：

- LeRobot
- ROS 2
- MoveIt
- MuJoCo
- Isaac Lab

根据数据源稳定性选择实际实现方式。

### Industry

先选择少量有稳定官方渠道的企业。

不要第一版一次接入全部公司。

### Education / Policy

先选少量稳定来源。

重点验证：

> “教育类信息是否真的能够被稳定捕获并产生有价值的周报内容。”

---

# 20. Prompt 管理

主要 Prompt 独立保存：

```text
prompts/
    classify.md
    paper_analysis.md
    industry_analysis.md
    technology_analysis.md
    education_analysis.md
    weekly_editor.md
    fact_check.md
```

不要把大段 Prompt 写死在 Python。

Prompt 修改应能够通过 Git diff 清楚看到。

---

# 21. AI 输出要求

AI 生成结果尽量采用结构化 JSON，再由程序生成最终 Markdown。

例如论文分析先输出：

```json
{
  "research_question": "",
  "method": "",
  "main_results": "",
  "why_it_matters": "",
  "limitations": "",
  "confidence": "",
  "evidence_refs": []
}
```

避免：

> 模型直接一次性自由发挥生成完整周报，完全无法中间检查。

建议流程：

```text
Candidate
↓
分类
↓
评分
↓
重点对象
↓
结构化分析
↓
事实检查
↓
Weekly Editor
↓
Markdown
```

---

# 22. 缓存与重复运行

人工验证期间会经常重复执行。

必须避免每次重新下载所有内容和重新调用所有模型。

建议支持：

```text
.cache/
```

并通过内容 hash / URL / arXiv ID 判断是否已有结果。

要求：

- 缓存不能保存 API Key；
- 缓存不能保存敏感 Header；
- 可以明确清空缓存重新执行。

---

# 23. Secrets

所有 API Key 只能从环境变量读取。

例如：

```text
OPENAI_API_KEY
GITHUB_TOKEN
```

不得：

- 写入源代码
- 写入 config
- 写入 README 示例值
- 输出到日志
- Commit 到仓库

提供：

```text
.env.example
```

仅包含变量名称。

---

# 24. 推荐目录结构

可以根据 Python 工程规范调整，但建议参考：

```text
embodied-intelligence-observatory/

README.md
LICENSE
CONTRIBUTING.md
pyproject.toml
.env.example

config/
    sources.yaml
    watchlist.yaml
    scoring.yaml

docs/
    architecture.md
    editorial_policy.md
    manual_run.md

src/
    embodied_observatory/
        collectors/
        parsers/
        normalization/
        dedup/
        ranking/
        research/
        llm/
        report/
        models/
        utils/

prompts/
    classify.md
    paper_analysis.md
    industry_analysis.md
    technology_analysis.md
    education_analysis.md
    weekly_editor.md
    fact_check.md

data/
    raw/
    normalized/
    candidates/

runs/

reports/
    2026/

tests/

latest.md
```

如果采用更合理的 `src layout`，可以调整。

---

# 25. 手动运行体验

当前阶段非常重要：

> 仓库维护者应该能够用一条命令完成一次周报生成。

例如设计成：

```bash
python -m embodied_observatory weekly \
  --start 2026-09-28 \
  --end 2026-10-04
```

或者：

```bash
eio weekly \
  --start 2026-09-28 \
  --end 2026-10-04
```

具体 CLI 名称由你决定。

至少提供：

### Collect

```bash
... collect --start YYYY-MM-DD --end YYYY-MM-DD
```

### Analyze

```bash
... analyze --week YYYY-WXX
```

### Report

```bash
... report --week YYYY-WXX
```

### Full Run

```bash
... weekly --start ... --end ...
```

### Dry Run

```bash
... weekly --start ... --end ... --dry-run
```

---

# 26. Dry Run

Dry Run 必须：

- 不覆盖正式周报；
- 不更新 `latest.md`；
- 不执行 Git commit；
- 输出到临时目录；
- 清楚显示本次将生成什么。

---

# 27. 人工审核流程

V0.1 建议流程：

```text
手动运行
↓
生成 draft
↓
人工阅读
↓
检查来源
↓
必要时修改
↓
人工 commit
↓
人工 push
```

第一阶段不要自动提交周报。

建议草稿先生成到：

```text
drafts/YYYY-WXX.md
```

人工确认后再通过命令：

```text
... publish --week YYYY-WXX
```

移动 / 复制到：

```text
reports/YYYY/YYYY-WXX.md
```

并更新：

```text
latest.md
```

如果这种机制实现成本很低，请实现。

---

# 28. 运行 3–4 周期间需要观察的指标

请在 README 或 `docs/manual_run.md` 中列出以下验证指标。

每周人工记录：

### 信息覆盖

- 是否漏掉行业公认的大新闻？
- robotics_arXiv_daily 是否正常？
- HF Daily Papers 是否正常？
- 教育类信息是否过少？
- 国内企业信息是否明显弱于国外？

### 内容质量

- Top 3–5 是否真的重要？
- 是否出现论文“看起来重要但实际一般”？
- AI 是否夸大论文结果？
- 是否过多复述 abstract？
- 是否过度依赖公司 PR？

### 去重

- 同一论文是否重复？
- 同一新闻多个媒体来源是否重复？
- 同一 Release 是否多次出现？

### 周报长度

观察：

- 总长度是否过长；
- 论文数量是否合适；
- 产业与教育比例是否合理。

### 成本

记录：

- 模型调用次数
- Token 量
- 预计 API 成本
- 哪些步骤最贵

### 稳定性

记录：

- 哪些 Collector 经常失败；
- 哪些网页容易改版；
- 哪些流程最耗时。

---

# 29. 未来自动化预留

虽然 V0.1 不实现自动调度，但架构需要方便未来加入：

```text
GitHub Actions
daily collect
weekly report
manual approval
publish
```

因此：

- CLI 要稳定；
- 配置要独立；
- Workflow 未来只负责调用 CLI；
- 不要把核心逻辑写在 GitHub Actions YAML 中。

未来 Workflow 理想状态：

```text
GitHub Actions
↓
调用同一套 Python CLI
```

本地运行与云端运行使用同一核心逻辑。

---

# 30. 日志

使用标准 logging。

至少支持：

```text
INFO
WARNING
ERROR
```

重要日志：

```text
source start
source success
source failed
items collected
items filtered
items deduplicated
LLM calls
report generated
warnings
```

不要打印：

- API Key
- Authorization Header
- 完整 Secrets

---

# 31. 错误处理

单一来源失败不能导致整个周报直接失败。

例如：

```text
Hugging Face Daily Papers unavailable
```

应该：

```text
WARNING
continue
```

但如果：

- 所有论文源都失败；
- 最终只有极少数据；
- 无法生成可信周报；

则应该停止生成正式 report，并明确报错。

---

# 32. 测试

至少实现单元测试：

- arXiv ID normalization
- URL normalization
- title normalization
- date range
- Candidate Schema
- dedup
- scoring
- source merge

集成测试：

```text
fixtures
↓
normalize
↓
dedup
↓
rank
↓
report
```

不要让绝大多数测试依赖实时网络。

---

# 33. README

README 以中文为主。

建议包括：

## 项目是什么

## 为什么做

## 内容覆盖

## 数据来源

## 项目架构

## 当前阶段

明确写：

> 当前为人工运行验证阶段，计划连续观察 3–4 周后再考虑全自动运行。

## 安装

## 环境变量

## 手动运行

## Dry Run

## 周报目录

## 编辑原则

## AI 使用说明

## 准确性声明

## 如何贡献 Source

## Roadmap

---

# 34. Editorial Policy

建议单独建立：

```text
docs/editorial_policy.md
```

写清楚：

### 纳入标准

### 排除标准

### Source Hierarchy

### 如何处理公司 PR

### 如何处理论文作者主张

### 如何表达不确定性

### 如何区分事实与评论

### AI 内容审核原则

### 修订与勘误机制

这个文件未来公开项目后会非常重要。

---

# 35. AI 透明度声明

README 和 Editorial Policy 都需要说明：

本项目使用：

- 自动化程序
- AI 模型

辅助：

- 信息收集
- 分类
- 摘要
- 内容组织
- 初步事实检查

但项目努力通过：

- 原始论文
- 官方来源
- 可追溯链接
- 人工审核

提升准确性。

提醒读者：

科研、采购、投资、教学等重要决策应查看原始来源。

---

# 36. 本次 Codex 实际执行步骤

请严格按以下顺序完成。

---

## Step 1：检查仓库

先查看当前仓库已有内容。

不要假设仓库完全为空。

不要覆盖已有有用文件。

---

## Step 2：先写架构

在大量编码前先创建：

```text
docs/architecture.md
```

至少说明：

- Pipeline
- Candidate Schema
- Collectors
- Dedup
- AI Boundary
- Ranking
- Report Generation
- Cache
- Error Handling
- Manual Run
- Future Automation Boundary

---

## Step 3：先跑通两类论文源

优先完成：

1. robotics_arXiv_daily
2. Hugging Face Daily Papers

完成：

```text
collect
↓
normalize
↓
dedup
↓
save
```

必须使用近期真实数据验证。

---

## Step 4：加入少量非论文来源

加入：

- 少量企业官方来源
- 少量开源项目
- 少量教育 / 政策来源

目标：

验证整体架构。

不是第一轮就覆盖整个行业。

---

## Step 5：完成 Candidate Schema

同时完成：

- serialization
- validation
- source merge
- evidence model

---

## Step 6：完成评分系统

配置放到：

```text
config/scoring.yaml
```

---

## Step 7：实现结构化 AI 分析

先产生 JSON。

再由程序生成 Markdown。

---

## Step 8：实现 Weekly Editor

将已经筛选、分析和验证的内容组织成最终周报。

不要让 Weekly Editor 再凭空引入新事实。

---

## Step 9：实现手动 CLI

保证仓库维护者可以运行完整流程。

---

## Step 10：实现 Draft → Publish

若实现成本合理：

```text
drafts/
↓
manual review
↓
publish command
↓
reports/
```

---

## Step 11：真实端到端运行

使用最近一个完整自然周。

生成第一份真实周报草稿。

不得完全使用 mock 数据冒充成功。

---

## Step 12：检查周报

重点人工 / 自动检查：

- 链接
- 重复项
- 论文信息
- 数字
- 日期
- 作者
- 公司名称
- 分类
- 事实 / 评论边界

---

## Step 13：运行测试

至少执行：

- lint
- unit tests
- integration tests
- dry run
- real weekly run

---

## Step 14：完善文档

包括：

```text
README.md
docs/architecture.md
docs/editorial_policy.md
docs/manual_run.md
```

---

# 37. 本次验收标准

完成前逐项确认。

## 核心功能

- [ ] robotics_arXiv_daily 可以获取指定日期范围数据
- [ ] HF Daily Papers 可以获取指定日期范围数据
- [ ] 两来源论文正确去重
- [ ] 保存统一 Candidate 数据
- [ ] 同一论文可以记录多个 source
- [ ] 有少量企业来源
- [ ] 有少量开源来源
- [ ] 有少量教育 / 政策来源
- [ ] 可以进行相关性筛选
- [ ] 可以进行五维评分
- [ ] 重点内容可以生成结构化分析
- [ ] 可以生成完整中文周报
- [ ] 周报可以追溯原始来源

## 工程

- [ ] 支持手动指定时间范围
- [ ] 支持 Dry Run
- [ ] 支持缓存
- [ ] 支持错误降级
- [ ] 有日志
- [ ] 有测试
- [ ] Secret 不进入仓库
- [ ] Prompt 独立管理

## 文档

- [ ] README 完整
- [ ] architecture 完整
- [ ] editorial policy 完整
- [ ] manual run 完整

## 自动化边界

- [ ] 没有周期 Cron
- [ ] 没有无人值守发布
- [ ] 没有自动社交媒体发布

---

# 38. 第一份真实周报的质量要求

第一份周报重点用于验证系统，不要求覆盖所有信息源。

但必须达到：

### 来源真实

每个重要事实都有来源。

### 论文真实

论文标题、作者、arXiv ID 正确。

### 结论克制

不夸张。

### 去重正常

同一论文 / 新闻不重复出现。

### 结构可读

普通具身智能从业者和学生能够读懂。

### 有判断

不能只是 RSS 聚合。

### 有教育栏目

确保项目形成自己的辨识度。

---

# 39. 完工后请输出 Codex 执行报告

不要只回复：

> Done

请提供完整报告。

---

## A. 实现内容

按模块说明。

---

## B. 实际数据源

列出：

- 成功
- 失败
- 尚未实现

---

## C. 第一次真实运行数据

例如：

```text
Raw items
Normalized
Deduplicated
Relevant candidates
Selected papers
Selected industry news
Selected open-source items
Selected education items
```

---

## D. 生成文件

列出主要输出文件。

---

## E. AI 调用

说明：

- 哪些步骤用了模型
- 哪些步骤没有使用模型

---

## F. 第一份周报质量观察

请主动指出：

- 哪些部分效果好
- 哪些部分质量一般
- 哪些信息可能漏掉
- 哪些栏目数据不足

---

## G. 成本

粗略说明：

- 一次完整 Weekly Run 的模型调用次数
- Token 主要消耗在哪
- 可以如何降低成本

---

## H. 已知问题

不要隐藏。

按：

```text
P0
P1
P2
```

分类。

---

## I. 接下来 3–4 周的人工验证建议

告诉维护者：

每周主要观察哪些指标。

---

## J. 暂时不要做的事情

再次确认：

> 当前不要自行加入云端自动定时执行。

只有在维护者明确提出：

> “现在开始做自动化版本”

以后，才进入 GitHub Actions / Cloud Automation 阶段。

---

# 40. 最终目标

这不是一次性的 AI 新闻摘要脚本。

目标是建立一个可以逐渐沉淀为长期公开项目的基础设施：

> **Embodied Intelligence Observatory**

它需要逐渐形成：

- 稳定的数据源
- 可解释的筛选标准
- 严谨的事实边界
- 可复用的数据资产
- 可靠的论文解读
- 产业观察
- 教育观察
- 连续的时间序列记录

V0.1 不追求庞大。

第一阶段成功的标准只有一个：

> **连续人工运行几周后，我们仍然愿意继续使用它，并且相信它生成的内容。**

如果高级功能影响这个目标，请优先做简单、稳定、透明的实现。
