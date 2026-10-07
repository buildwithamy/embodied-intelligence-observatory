from .models import Candidate


def escaped(text: str) -> str:
    return text.replace("[", "\\[").replace("]", "\\]").replace("<", "&lt;").replace(">", "&gt;")


def links(item: Candidate) -> str:
    rows = [f"- [原始来源]({item.url})"]
    seen = {item.url}
    if item.project_url:
        rows.append(f"- [Project]({item.project_url})")
    if item.github_url:
        rows.append(f"- [Code]({item.github_url})")
    for evidence in item.evidence:
        if evidence.url in seen or evidence.kind == "source_discovery":
            continue
        seen.add(evidence.url)
        rows.append(f"- [{escaped(evidence.id)} · {escaped(evidence.kind)}]({evidence.url})")
    rows.append("- 收录来源：" + "、".join(item.sources))
    return "\n".join(dict.fromkeys(rows))


def entry(item: Candidate) -> str:
    analysis = item.analysis
    if analysis is None or analysis.fact_check != "pass":
        return (f"### {escaped(item.title)}\n\n未完成证据解读与事实审核，仅保留线索。"
                f"规则预评分 {item.overall_score:.2f}/5，不能视为技术质量结论。\n\n{links(item)}\n")
    paper = item.source_type == "paper"
    labels = ("研究问题", "核心方法", "主要结果（作者报告）") if paper else (
        "发生了什么", "已确认的信息（官方声明）", "主要变化（官方声明）")
    rows = [f"### {escaped(analysis.chinese_title)}", "", escaped(item.title), "",
            f"日期：{item.published_at} · 标签：{' / '.join(item.tags) or item.source_type}", ""]
    if item.authors:
        names = "、".join(item.authors[:8])
        if len(item.authors) > 8:
            names += f"等 {len(item.authors)} 位（完整作者见原论文）"
        rows += ["作者：" + escaped(names), ""]
    for label, field in zip(labels, ("research_question", "method", "main_results")):
        rows += [f"**{label}**", "", getattr(analysis, field), "",
                 "证据：" + "、".join(analysis.claim_refs[field]), ""]
    rows += ["**为什么值得关注（观察站判断）**", "", analysis.why_it_matters, "",
             "**局限与待验证问题**", "", analysis.limitations, "",
             f"阅读层级：{analysis.read_depth} · 置信度：{analysis.confidence} · 解读来源：{analysis.origin}", "",
             "**Links / Sources**", "", links(item), ""]
    return "\n".join(rows)


def render(items: list[Candidate], all_items: list[Candidate], manifest: dict, resources: list[dict]) -> str:
    start, end = manifest["date_range"]["start"], manifest["date_range"]["end"]
    week = manifest["week"]
    reviewed = [c for c in items if c.analysis and c.analysis.fact_check == "pass"]
    rows = ["# Embodied Intelligence Weekly", "", f"具身智能周报 · {week} · 待人工审核草稿", "",
            f"时间范围：{start} ～ {end}", "",
            "本文由程序整理来源，并通过结构化解读辅助编辑。作者报告、官方声明与观察站判断分别标注。"
            "科研、采购、投资和教学决策请查看原始资料。", "",
            "## 本周速览", ""]
    for item in reviewed[:5]:
        rows.append(f"- **{escaped(item.analysis.chinese_title)}**：{item.analysis.why_it_matters}"
                    f" [查看来源]({item.url})")
    if not reviewed:
        rows.append("本次尚未完成可信解读，以下是待审线索，不能作为已完成周报。")
    rows += ["", "## 01｜本周焦点", "",
             "本期焦点指向下列正文条目；评估边界与证据见对应栏目，避免重复展开同一事件。", ""]
    for item in reviewed[:3]:
        rows.append(f"- [{escaped(item.analysis.chinese_title)}]({item.url}) — "
                    f"仍需观察：{item.analysis.limitations}")
    categories = [("02｜产业与公司", {"industry"}), ("03｜技术与开源", {"technology", "open_source"}),
                  ("04｜本周论文精选", {"paper"}), ("05｜教育与人才培养", {"education", "policy"})]
    for heading, types in categories:
        rows += ["", "## " + heading, ""]
        group = [c for c in items if c.source_type in types]
        rows += [entry(item) for item in group] if group else [
            "本期已接入来源未检出足够的相关信息。这反映采集覆盖，不能推断该领域本周没有进展。"]
        if "education" in types:
            rows += ["", "### 持续学习资源（非本周新增）", ""]
            for resource in resources:
                rows.append(f"- [{resource['title']}]({resource['url']})：{resource['note']}")
    rows += ["", "## 06｜本周值得继续观察", ""]
    watch = [c for c in all_items if c.big_news and c.id not in {s.id for s in items}][:5]
    for item in watch:
        rows.append(f"- [{escaped(item.title)}]({item.url})：触发重大事件二次检查；"
                    "尚未找到足够的一手资料验证其具身关联或重要程度。")
    for warning in manifest["warnings"]:
        rows.append("- 来源覆盖：" + warning)
    if not watch and not manifest["warnings"]:
        rows.append("- 已接入来源之外的国内企业、专业建设和商业订单，仍需要维护者按 watchlist 人工核验。")
    rows += ["", "## 07｜资源索引", ""]
    for label, predicate in [("Papers", lambda c: c.source_type == "paper"),
                             ("Code", lambda c: bool(c.github_url)),
                             ("Dataset", lambda c: False), ("Models", lambda c: False),
                             ("Reports", lambda c: c.source_type in {"industry", "technology"}),
                             ("Policy", lambda c: c.source_type == "policy")]:
        rows += ["### " + label, ""]
        resources_for_group = [c for c in items if predicate(c)]
        rows += [f"- [{escaped(c.title)}]({c.github_url if label.startswith('Code') else c.url})"
                 for c in resources_for_group] or ["本期无已核验条目。"]
        rows.append("")
    rows += ["### Courses", ""] + [f"- [{r['title']}]({r['url']})（持续资源）" for r in resources]
    rows += ["", "---", "",
             f"覆盖：尝试 {len(manifest['sources_attempted'])} 源，成功 {len(manifest['sources_success'])} 源，"
             f"失败 {len(manifest['sources_failed'])} 源；选入 {len(items)} 项，完成事实审核解读 {len(reviewed)} 项。",
             "来源成功仅表示本次请求与解析完成，不代表完整覆盖。无 API 模型调用时，解读来自显式导入的核验 JSON。",
             "本文件尚待维护者审核；publish 命令不会自动提交或推送。", ""]
    return "\n".join(rows)
