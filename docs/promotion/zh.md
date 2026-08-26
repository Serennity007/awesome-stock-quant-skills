# 推广文案（中文：V2EX / 即刻 / 知乎）

## V2EX 分享

**标题**：做了个 A 股/量化 AI Skill 合集：收录 16 个开源交易 Skill + 2 个自己写的（巴菲特选股已实跑，附真实输出）

各位好，整理了一个炒股/量化方向的 Claude Code (Agent) Skills 合集：
https://github.com/Serennity007/awesome-stock-quant-skills

- 收录了 GitHub 上 16 个许可合规（MIT/Apache-2.0/BSD/CC0）的股票分析、选股、量化交易 Skill，全部保留原 LICENSE 和溯源文件；无 License/GPL 的项目只进索引不转载
- 自己写了 2 个原创 Skill：
  - **buffett-value-investing**：按巴菲特标准（连续 5 年 ROE>15%、毛利率稳定、低负债、现金流为正、估值历史分位）给 A 股打分。实跑示例：贵州茅台 100 分、五粮液 94 分、招商银行 47 分（金融股高杠杆被正确扣分）
  - **technical-pattern-recognition**：均线排列、MACD 金叉死叉、放量突破新高、缩量回踩，输出信号表
- 原创 Skill 全部基于 akshare 免费数据，README 里附的是真实运行输出，不是编的
- GitHub Action 每天自动跑一遍 20 只代表股的筛股，结果提交到 reports/ 目录
- 中英日三语文档

初衷：这类 Skill 散落在各处、质量参差，这个仓库把能合规转载的收齐、把不能转的索引清楚，并附一份实测对比表（哪些真的能跑、哪些要付费 key）。欢迎试用和提 issue。

## 即刻

整理了一个「炒股 AI Skill」合集仓库 🏗️ 收录 GitHub 上 16 个开源的股票分析/量化交易 Skill（只收 MIT/Apache 等许可合规的，附溯源），另写了 2 个原创 Skill：一个按巴菲特标准给 A 股打分（实测茅台 100 分、招行 47 分——金融股高杠杆正确被刷掉），一个做技术形态识别。全部基于 akshare 免费数据，README 附真实运行输出，还有 GitHub Action 每天自动生成筛股报告。中英日三语。链接：https://github.com/Serennity007/awesome-stock-quant-skills

## 知乎（回答「有哪些好用的量化/选股 AI 工具」类问题）

推荐一个我自建的合集仓库 awesome-stock-quant-skills。它做了三件事：

1. **收录**：把 GitHub 上许可合规（MIT/Apache-2.0/BSD/CC0）的 16 个股票分析/量化交易 Agent Skill 收进来，每个都保留原 LICENSE 和 SOURCE.md 溯源；许可不允许转载的项目只给索引链接。
2. **实测**：写了一份逐个检查表，标明每个 Skill 是否有标准 SKILL.md、依赖什么、要不要付费 API key、本次是否真的跑通了（需要 QMT/IBKR 等外部环境的如实标注"未实测"）。
3. **原创**：补了两个自己写的 Skill 并给出真实运行输出——巴菲特式价值选股（600519 实测 100/100，打分细项全透明）和技术形态识别（MACD 金叉/放量突破等信号表）。数据全部走 akshare 免费接口，不依赖任何付费 key，clone 下来 pip install akshare 就能跑。另有一个 GitHub Action 每天 UTC 01:00 自动跑 20 只代表股的筛股并把报告提交回仓库。

仓库中英日三语，仅供学习研究，不构成投资建议。地址：https://github.com/Serennity007/awesome-stock-quant-skills
