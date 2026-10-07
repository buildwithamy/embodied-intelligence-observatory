# V0.3：从研究记录到读者周刊

保留V0.1原始数据、候选、证据与CLI。新增「重大事件记忆 → 独立大新闻审计 → 编辑判断与影响 → 网页/Markdown」路径，网页以变化、应用与教学启示为阅读顺序。

## 时间与记忆

本期周窗口2026-09-28～10-04，最近30天09-05～10-04。Weekly New / Recent Major / Persistent Major分别标注；旧事件不因跨周失去价值，也不能改写为本周新发布。持久事件默认S级60天、A级45天、B级7天，超30天延续必须注明继续保留的理由；后续事实单独保留更新时间。没有旧期基线时明确为首期回溯，不制造月度增量。每期审计保留事件快照，网页重建读取快照，不将以后更新泄漏到历史周刊。

data/major_events.json使用Pydantic模型，保存事件日期、首次发现、事实更新、重要性、状态、原文与解释。编辑导入保留first_seen，拒绝事件时间倒退；归档不删除原记录。未确认线索留审计队列，不能成为已确认Top Story。

## 独立Major News Audit

普通Collector不承担穷尽大新闻的职责。每期需独立查看Companies/Product/Models/Open Source/Capital/Policy/Education的一手渠道；审计的实际查阅记录与未覆盖领域输出runs/YYYY-WXX-major-news-audit.json。当前采用Codex/维护者执行公开资料核验后显式导入的模式，不伪称全网自动审计。来源不可达、时间不符或无法确认均留队列。

## 编辑模型

IssueEditorial包含一句话、3个主要变化、速读、Top Stories、场景影响、课程建议与研究问题。每条均绑定major event或已审核paper ID。事实取自引用来源；应用与教育影响均标明为编辑判断。矩阵采用「直接研究 / 潜在关联 / —」定性标记，不生成商业成熟度分数。

## 阅读与视觉

静态HTML+本地CSS/少量JS，无依赖远程图片/字体。原创HTML/CSS时间线、定性矩阵与原创SVG技术→场景关系、样本研究主题分布共四类信息视觉；论文默认折叠，审计细节统一折叠。桌面与手机真实浏览器截图验收。

## 运行边界

新增major-audit与edition手动CLI，输入为独立核验记录与编辑JSON。edition默认生成静态本地site与draft；显式--archive按用户本次要求写reports/YYYY/YYYY-WXX.md，不更新latest或外部发布。Dry Run写临时目录并仅读取正式记忆。没有Cron、自动push、云端发布或社媒任务。
