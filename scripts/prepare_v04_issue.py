"""Prepare a reviewable W40 draft and pending selection, without approving or publishing."""
import copy
import hashlib
import json
from pathlib import Path

import yaml

from embodied_observatory.pipeline import load_json, write_json

ROOT = Path(__file__).resolve().parents[1]


def story(ident, title, deck, event, paragraphs, applications, education, questions, limits):
    return {'id': ident, 'title': title, 'deck': deck, 'refs': ['event:' + event],
            'paragraphs': paragraphs, 'why_now': deck, 'applications': applications,
            'education': education, 'questions': questions, 'limits': limits}


def main():
    issue = copy.deepcopy(load_json(ROOT / 'data/editorial/2026-W40-v03.json'))
    issue['schema_version'] = '0.4'
    additions = [
        story('qualcomm-picknik', '高通拟收购 PickNik，MoveIt 将怎样接入芯片平台？',
            '9 月 23 日公布的协议，把机器人操作软件与 Dragonwing、Arduino 的集成放到了下一步计划中。',
            'qualcomm-picknik-agreement-20260923', [
                '高通宣布签署收购 PickNik 的协议，交易仍需满足通常交割条件。PickNik 长期维护基于 ROS 的机器人操作框架 MoveIt；高通计划加强 MoveIt、商业版 MoveIt Pro 与 Dragonwing 机器人平台的集成，并从 Arduino VENTUNO Q 开发板开始推进适配。',
                '公告表示，MoveIt 1 和 MoveIt 2 将保持现有许可下的开源与社区驱动，并继续支持第三方硬件。对开发者而言，值得跟踪的是运动规划、感知和端侧计算的接口能否更容易集成，以及社区承诺是否体现在后续代码和路线图中。'],
            ['用现有 MoveIt 工程检查接口兼容与硬件支持，记录迁移工作量。', '关注公开代码、第三方驱动和社区路线图的后续变化。'],
            '将规划框架、控制器与计算平台分开画出依赖关系，再比较不同硬件上的适配步骤。',
            ['平台集成能减少哪些开发工作？', '社区治理与第三方硬件支持会怎样落实？'],
            '公告未披露交易金额。拟收购与集成计划不能当作已完成交割或已取得性能收益；商业 MoveIt Pro 与开源 MoveIt 需要分清。'),
        story('cognex-realsense', 'Cognex 拟收购 RealSense，机器人深度视觉有了新归属计划',
            '9 月 22 日，Cognex 公布约 5 亿美元的收购协议，计划连接工业机器视觉与机器人深度感知。',
            'cognex-realsense-agreement-20260922', [
                'Cognex 宣布已签订收购 RealSense 的最终协议，对价约 5 亿美元，预计在 2026 年第四季度交割，仍需满足条件。RealSense 的深度相机和视觉技术用于机械臂、移动机器人、四足与人形机器人；Cognex 希望把这部分能力接入已有工业视觉产品和客户渠道。',
                '按公告安排，RealSense 将在交割前把人脸认证产品线分拆成独立公司。此次变化首先是业务与渠道整合，是否会带来更好的机器人感知与导航表现，仍需具体产品和任务评测。'],
            ['继续检查相机驱动、SDK、供货和产品支持的实际变化。', '在自己的光照、距离和材质条件下测量深度误差与导航表现。'],
            '用深度相机比较反光、遮挡与弱光条件下的测量误差，再讨论错误如何传到抓取和导航。',
            ['整合后的视觉工具链能否减少现场适配工作？', '机器人客户与原有开发者能得到哪些持续支持？'],
            '约 5 亿美元为拟收购对价；员工留任和股票安排另列。收入与市场增长数字属于公司预测，不能当作已实现业绩。'),
        story('amd-world-labs', 'AMD 拟收购 World Labs，空间模型走近算力',
            '9 月 28 日，双方宣布签署收购协议。值得跟踪的是模型研究与计算路线图如何结合，交易尚未完成。',
            'amd-world-labs-agreement', [
                'AMD 与 World Labs 公告确认双方已签订最终协议。AMD 的 8-K 披露，协议于 9 月 26 日签署，拟以约 82 亿美元的 AMD 普通股购买 World Labs 全部股权；9 月 28 日是公开披露日期。双方预计交易在 2026 年底前完成，仍需监管批准及其他交割条件。',
                'World Labs 表示，两家公司此前已围绕 AMD GPU 的模型训练与推理优化展开合作。AMD 希望借助空间模型研究理解机器人、仿真和 physical AI 对计算的需求，并据此完善硬件、软件与系统路线图。相关研究对机器人数据和仿真的帮助，目前仍需实际评测。'],
            ['关注模型、仿真和算力接口是否出现可用的新工具。', '评估空间模型时，检查几何一致性、物理约束和动作交互，避免只看生成画面。'],
            '把这次协议作为技术栈案例，画出模型、仿真、训练与推理的依赖关系，再区分已公布事实和待实现计划。',
            ['空间模型是否会改变机器人训练数据的来源？', '新计算平台能否改善闭环交互的延迟与成本？'],
            '这是拟收购协议，不是已完成交割。约 82 亿美元是交易对价，不是机器人业务收入；技术收益尚未经过独立真机验证。'),
        story('flux3-action', 'FLUX 3 Action：把未来画面与动作一起预测',
            '9 月 23 日，Black Forest Labs 公布机器人动作模型与适配路径。开放权重带来了试验入口，也需要检查许可和机器人数据要求。',
            'bfl-flux3-action', [
                'FLUX 3 Action 是一个 7B 世界动作模型，用扩散 Transformer 联合预测未来视频与动作。模型生成动作片段，执行其中一部分后重新观察和规划；开发者提供 LeRobot 集成、SO-101 检查点及微调方法。',
                '开发者报告，使用 DROID 数据微调后的模型在 RoboLab-120 中取得 42.92% 成功率。这是指定评测协议下的结果，不能直接代表工厂或家庭任务。SO-101 示例也使用了约 200 个遥操作 episode 适配，仍然需要机器人数据。'],
            ['在相同任务、相同数据预算下，与已有策略比较完整任务成功率和推理耗时。', '运行检查点前阅读 FLUX Kommunity License v1.0，确认自己的使用范围。'],
            '在低成本机械臂上记录视频预测、动作执行与重规划分别在哪些环节失败。',
            ['未来视频预测得更准，动作执行是否也会改善？', '适配数据量和执行频率会怎样改变结果？'],
            '开放权重不等于没有使用限制。评测和适配结果来自开发者，未独立复现；视频生成能力不能直接当作物理可靠性。'),
        story('intrinsic-core', 'Intrinsic Core 开源，先从 CNC 上下料试起',
            '9 月 22 日发布的核心平台，把本地运行时、实时控制、数字孪生与参考应用放到了公开代码中。',
            'intrinsic-core-20260922', [
                'Intrinsic Core 提供 ROS 兼容的本地运行时、SDK 和硬件无关的实时控制框架，代码采用 Apache 2.0 许可。发布内容包括数字孪生，以及面向 CNC 机床上下料的 OMTS 参考方案。',
                '参考方案把仿真、相机标定、姿态估计、运动规划、抓取与驱动配置接到同一任务中。它为学习和验证系统集成提供了入口，但公开的是平台核心部分，不能据此认定 Flowstate、高级模型和企业云服务全部免费开放。'],
            ['先在仿真中跑通参考方案，再检查真实设备的驱动、标定和控制周期。', '用失败记录和人工干预次数评估适配工作量。'],
            '把 CNC 上下料拆成感知、规划、控制和设备通信四个实验，逐段验收后再集成。',
            ['参考配置换到其他机械臂后需要改哪些接口？', '仿真中的成功能否稳定迁移到真机？'],
            '开源框架和参考设计不等于已验证的客户部署业绩，也不代替现场安全验收。'),
        story('microsoft-offloading', '机器人推理放在哪里？Microsoft 给出试验工具',
            '9 月 23 日，Physical AI Toolchain 增加推理卸载能力，支持把工作负载放到机器人、边缘 GPU 或云端。',
            'microsoft-offloaded-physical-ai-inference', [
                'Microsoft 的工具用容器和 Kubernetes 组织机器人与远端计算资源，并连接 ROS2 和 LeRobot。发布示例包括 SO-101 和 UR10e；研究团队讨论了移动操作中的语义建图、规划、导航和操作工作负载。',
                '9 月的新进展是工具能力公告。作为依据的 MSR-TR-2026-14 技术报告发表于 3 月，不能当成本期新论文。实验提示，把计算移出机器人可能改善特定工作负载的表现和续航，但网络时延、上行带宽、视频压缩与 GPU 竞争也会改变闭环结果。'],
            ['用同一任务比较端侧、边缘和云端的延迟、成功率、续航与断网行为。', '将控制链路与可卸载的模型推理分开设计，并测量网络变差时的表现。'],
            '固定策略和硬件，逐步增加网络延迟，记录任务成功率与人工接管，避免只比较模型单次推理速度。',
            ['什么时候远端计算的收益会被网络开销抵消？', '多机器人共享 GPU 时，调度是否会破坏稳定节拍？'],
            '报告中的收益依赖指定平台和实验条件；不能推导所有机器人都应上云，更不能把工具支持当作安全认证。'),
        story('light-o1', 'Light-O1：从人类动作视频学起，再适配机器人',
            '9 月 21 日，亮源新创发布人类动作预训练方案。需要分开看预训练规律、仿真成绩与真机演示。',
            'lightorigins-light-o1', [
                'Light-O1 将人类视频转成结构化动作，用于预训练全身智能模型，再使用机器人数据适配本体和任务。团队公开了不同数据规模下的预训练实验，并提供 Preview 权重和代码入口。',
                '公司报告，在模拟 RoboCasa 的 GR-1 机器人上，24 个任务的宏平均成功率为 79.3%，每个任务评测 50 次。跨本体缩放实验另外使用留出集动作 token 损失和开环全身姿态误差；这些指标都不能直接当作跨任务真机成功率。'],
            ['固定机器人适配数据，检验增加人类动作预训练是否改善未见任务。', '分别记录仿真成功率、开环动作误差和真机完整任务表现。'],
            '让学生解释每项评测指标测到了什么，再设计一个能够检验迁移收益的对照实验。',
            ['人类视频中的动作先验能否减少真机数据需求？', '不同本体的动作表达和接触条件如何影响适配？'],
            '数据和结果来自公司公开材料，未独立复现。79.3% 是特定模拟任务的宏平均，不是家庭或工厂的真机成功率。'),
    ]
    issue['stories'].extend(additions)
    issue['signals'][1] = {'title': 'AMD 拟收购 World Labs',
        'fact': '双方签署约 82 亿美元股票交易协议，仍待审批与交割。',
        'meaning': '空间模型研究与算力路线图的结合，值得持续跟踪。',
        'refs': ['event:amd-world-labs-agreement'], 'tags': ['资本', '空间智能']}
    issue['signals'][2] = {'title': '动作模型与推理工具有新进展',
        'fact': 'FLUX 3 Action 公布权重；Microsoft 增加机器人推理卸载。',
        'meaning': '模型适配、执行延迟与网络条件需要一起评估。',
        'refs': ['event:bfl-flux3-action', 'event:microsoft-offloaded-physical-ai-inference'], 'tags': ['模型', '工具链']}
    issue['cover_label'] = '封面回看 · 家庭机器人'
    new_briefs = [{'title': s['title'], 'fact': s['paragraphs'][0], 'meaning': s['limits'],
                   'refs': s['refs'], 'tags': ['最近两周']} for s in additions]
    # Old stories remain in the editorial source as optional reviewed copy. Selection chooses the homepage.
    sima = {'title': 'SiMa.ai 披露 1.5 亿美元 C 轮融资',
            'fact': '9 月 28 日，公司披露本轮融资 1.5 亿美元、累计融资 5 亿美元、估值 14.5 亿美元。',
            'meaning': '资金将用于软件与下一代端侧芯片。1000 dense TOPS 是计划在 2028 年上半年推出的硬件目标，不是现售产品指标。',
            'refs': ['event:sima-series-c-20260928'], 'tags': ['资本', '端侧计算']}
    issue['quick_read'] = new_briefs + [sima] + issue['quick_read'][:5]
    issue['methodology'] += (' V0.4 另外对 09-21～10-04 执行中英开放新闻发现，'
        '媒体和行业报道用于发现线索，重要结论回到原始公告、技术稿或监管文件。'
        '新闻按战略影响、跨生态影响、规模、技术意义、证据与时效独立评分；'
        'Audit 和 Selection 决定首页与回溯内容。搜索执行不代表全网覆盖，未核验线索不作为已确认新闻。')
    issue['monthly_comparison'] = ('本期对最近 14 天执行开放发现，并保留最近 60 天内仍有背景意义的重大事件。'
        '目前没有完整上月基线，不能据此计算行业增长或判断成熟度；较早事件也不按近期媒体报道刷新日期。')
    path = ROOT / 'data/editorial/2026-W40-v04.json'
    write_json(path, issue)
    gate = load_json(ROOT / 'runs/2026-W40/editorial_audit.json')
    candidates = load_json(ROOT / 'runs/2026-W40/news_candidates.json')
    known = {c['id']: c for c in candidates}
    story_ids = {s['refs'][0].removeprefix('event:'): s['id'] for s in additions}
    selected_top = gate['suggested_top_stories']
    active = [c for c in candidates if c['verification'] == 'confirmed' and c['event_ref']
              and c['state'] != 'archived' and c['event_date'] >= '2026-08-06']
    selection = {'issue': '2026-W40', 'audit_sha256': gate['audit_sha256'],
        'review': {'status': 'pending', 'reviewer': '', 'reviewed_at': '', 'issue_sha256': ''},
        'top_stories': [{'id': ident, 'selected': True, 'tier': known[ident]['proposed_tier'],
                         'order': n, 'story_id': story_ids[ident], 'reason': known[ident]['why_it_matters']}
                        for n, ident in enumerate(selected_top, 1)],
        'briefing': [{'id': c['id'], 'selected': True} for c in active],
        'recent_major': [{'id': c['id'], 'selected': True} for c in active if c['proposed_tier'] in {'S', 'A'}],
        'exclude': [], 's_tier_exceptions': [],
        'cover_note': '保留已认可的家庭泛化封面，标为回看；新增重大新闻出现在首屏信号、速读和Top Stories。'}
    selection_path = ROOT / 'runs/2026-W40/editorial_selection.yaml'
    existing = yaml.safe_load(selection_path.read_text(encoding='utf-8'))
    if existing.get('review', {}).get('status') == 'approved':
        raise ValueError('Refusing to replace an approved human selection')
    selection_path.write_text(yaml.safe_dump(selection, allow_unicode=True, sort_keys=False), encoding='utf-8')
    original = load_json(ROOT / 'runs/2026-W40-deepseek-polish.json')
    inherited = {key: original[key] for key in ('week', 'provider', 'model', 'calls', 'usage', 'successful_calls',
                                              'failed_calls', 'usage_complete')}
    inherited.update(status='reviewed_applied', issue_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                     candidates_sha256=original['candidates_sha256'],
                     provenance='Retained V0.3 copy; V0.4 additions reviewed by Codex without new model calls.',
                     baseline_issue_sha256=hashlib.sha256((ROOT / 'data/editorial/2026-W40-v03.json').read_bytes()).hexdigest(),
                     editorial_additions=[s['id'] for s in additions])
    write_json(ROOT / 'runs/2026-W40-v04-copy-edit.json', inherited)
    print(json.dumps({'issue': str(path), 'top_stories': selected_top, 'status': 'pending_human_selection'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
