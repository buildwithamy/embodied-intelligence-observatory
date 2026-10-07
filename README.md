# 全球具身智能观察

看具身智能在真实场景里走到了哪一步：哪些产品能买，哪些工具能用，学校该教什么。

双周刊，中文为主，每期附英文摘要。写给三类读者：算法工程师和开发者，产品经理和项目经理，教育工作者。

## 创刊号：人形机器人落地的两本账

第 1 期 · 2026.09.24–10.07 · **[在线阅读](https://buildwithamy.github.io/embodied-intelligence-observatory/)**

[![创刊号首屏：人形机器人落地的两本账，中国在数台数，美国在算单台账](docs/images/issue-01-cover.jpg)](https://buildwithamy.github.io/embodied-intelligence-observatory/)

国庆前后，智元把 300 多台机器人送进长隆，又在 100 家门店各放了一台；银河通用的新品上线一天，预订过了 200 台。太平洋另一边，Agility 把 Digit 的账摊开给投资人看：月费 8,500 美元，1,000 台订单要一项技能一项技能地兑现。两本账都缺同一页：这些机器人每天到底干了多少活。

| 栏目 | 本期看点 |
|---|---|
| 格局 | AMD 82 亿美元买下李飞飞的 World Labs；MoveIt 和 RealSense 同一周易主 |
| 产品 | 一张人形价格表：7.9 万元到 20 万美元 |
| 本期一张图 | 你看到的“台数”，停在哪一级 |
| 场景 | 十个场景，谁走到了小批量；六格证据卡和承诺兑现台账 |
| 技术 | 这两周能上手的模型和工具，附三个动手实验 |
| 教育 | 九所高校开招，第一节实验课怎么上 |
| 研究与故事线 | 四篇和现场有关的论文，四条持续追踪的主线 |
| 深度 | Digit 的两本账，附一个能拖动的回本计算器 |

页面支持浅色和深色模式，可以按“研发 / 产品与项目 / 教育”切换分角色要点。

## 怎么做

- **选题**：先看落地证据和可用性，再看能力边界和影响面，标准见 [改进方案 V2](docs/EIO_改进方案_V2.md)。重大投融资单独判断，先看对行业的影响，再看金额。
- **证据等级**：每条标注“官方 / 公司自述 / 媒体 / 说明”，并附原文链接。
- **AI 使用**：资料整理、写作和插画由 AI 辅助完成，编辑审阅后发布。插画源文件保留 C2PA 内容凭证。
- **节奏**：两周一期，周末发布。第 2 期窗口为 10.08–10.18。

## 仓库结构

| 路径 | 内容 |
|---|---|
| `site/previews/issue-01/` | 创刊号页面；`src/` 下是页面模板、原创插画和构建脚本 |
| `docs/EIO_改进方案_V2.md` | 定位、栏目、选题标准和文风规范 |
| `HANDOFF.md` | 维护交接说明 |
| `src/`、`config/`、`prompts/`、`tests/` | V0.4 新闻发现流水线（Python），后续改造成每日抓取 |
| `docs/history/` | V0.1–V0.4 的任务书和过程记录 |
| `.github/workflows/pages.yml` | 构建页面并部署到 GitHub Pages |

## 本地预览

```bash
python site/previews/issue-01/src/build.py
python -m http.server 8000 --directory site/previews/issue-01
```

然后打开 <http://localhost:8000>。改了 `src/page.html` 或 `src/art/` 后重新运行第一条命令；推送到 `main` 后，Actions 会自动构建并发布。

V0.4 流水线的安装和测试（Windows 把 `.venv/bin/python` 换成 `.venv\Scripts\python`）：

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest -q
```

用法见 [运行指南](docs/manual_run.md) 和 [架构说明](docs/architecture.md)。W40 的抓取数据和原文快照含第三方文章全文，没有放进公开仓库，依赖它们的回归测试会自动跳过。

## 路线图

1. **内容格式与渲染器**：每期写一份 Markdown，正文用可视化块描述图表，渲染器沿用创刊号的羊皮卷主题。
2. **事件库与实体库**：产品、场景、工具、故事线和承诺台账跨期累积；GitHub Actions 每日抓取。
3. **常设页面**：场景地图、产品库、工具表、故事线和往期归档。

## 参与

发现漏掉的事件、写错的数字，或者想推荐信源，欢迎[提 Issue](https://github.com/buildwithamy/embodied-intelligence-observatory/issues)。

## 许可

- 代码（`src/`、`tests/`、`scripts/`、构建脚本和工作流）：[MIT](LICENSE)
- 刊物内容（文字、图表数据和原创插画）：[CC BY-NC-SA 4.0](LICENSE-CONTENT.md)
- 引用的第三方资料版权归原作者所有，本刊只做摘录并附链接。
