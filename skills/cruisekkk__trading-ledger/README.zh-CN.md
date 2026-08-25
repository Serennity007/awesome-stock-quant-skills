# trading-ledger · 交易账本

[English](README.md) | **简体中文**

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE) [![Works with: Claude Code · Claude.ai](https://img.shields.io/badge/works%20with-Claude%20Code%20·%20Claude.ai-d97757)](#安装) [![Notion 模板](https://img.shields.io/badge/Notion%20模板-中文%20·%20EN-black?logo=notion)](https://spiral-jump-106.notion.site/5f92910834c44321af7661f98f062e27)

**一个逼你在入场那一刻把理由说出口的账本。** 随口报一笔交易——*"135 买了 500 股 NVDA，止损 128，赌财报后回调到位"*——AI 写进你自己的 Notion 数据库：标的、数量、价格，**以及所有表格式日志都留不住的东西：你的入场理由、交易计划、当时的情绪**。不说理由？它会追问。全部的诀窍就这一个。

```
你:   今早买了一张 TSM 7月的 call，理由跟财报前那笔一样
AI:   记好了 ✅ TSM 0731C475 · 做多 · 持仓中
      ❓ 待确认：几张、单价多少？
      ❓ 计划呢——拿到财报，还是有止损位？
你:   1张 18.50，拿到财报
AI:   已更新 ✅ 理由：博财报前上涨 · 计划：拿到财报
```

到复盘日说一句 *"复盘交易"*，它把每笔已平仓的交易过三个问题：**理由兑现了吗？按计划执行了吗？情绪单占比多少？** 按计划止损的亏单，比撞大运的盈单得分高——它会直说。

<table>
<tr>
<th width="50%">💬 网页 / 手机 · Claude.ai</th>
<th width="50%">⌨️ 终端 · Claude Code</th>
</tr>
<tr>
<td width="50%"><img src="./assets/demo-web.gif" alt="claude.ai 演示：一句话记一笔——抓住理由，追问缺失的目标价" width="100%" /></td>
<td width="50%"><img src="./assets/demo-terminal.gif" alt="终端演示：平仓自动配对持仓行，按你自己的计划给执行打分" width="100%" /></td>
</tr>
</table>

## 为什么

《金融怪杰》系列访谈里反复出现的那个习惯朴素得很：把每笔交易的决策过程写下来，定期回看。不是为了记盈亏——券商替你记着呢——而是因为**入场理由过夜就失真**。一周后你真的想不起来那笔是基于论点买的还是凭感觉买的，而你的记忆只会替你美化。

所有交易日志工具的死穴：它是个表格，而表格活不过三天。这个东西搭在你已有的习惯上——你反正整天泡在 AI 对话里。成交那一刻顺嘴一句话，决策现场就被固定下来了，来不及被事后修饰。

## 它是什么

一个 **Claude skill**（一份 `SKILL.md` 指令）+ 你自己的 **Notion 数据库**。没有服务器、没有后端，数据都在你的 Notion 里。手机 / 电脑 / 网页，有 Claude 的地方就能记。**注意：** skill / connector 目前需要 Claude **付费**档。

姊妹项目：[time-ledger](https://github.com/cruisekkk/time-ledger)——同一套方法（Notion 当真相源 + skill 解析自然语言 + 拿不准批量问而不是瞎猜），用在「时间花哪了」上。

## 安装

**第 0 步——复制 Notion 模板**：[🇨🇳 中文](https://spiral-jump-106.notion.site/5f92910834c44321af7661f98f062e27) · [🇬🇧 English](https://spiral-jump-106.notion.site/5ac095dfaafb4fd389875db6a5c7193a)。一键 duplicate，字段、视图、示例行都带好了。

然后挑你的入口：

**⌨️ 终端 · Claude Code**

```bash
git clone https://github.com/cruisekkk/trading-ledger.git
mkdir -p ~/.claude/skills/trading-ledger
cp trading-ledger/SKILL.zh-CN.md ~/.claude/skills/trading-ledger/SKILL.md
```

装 **Notion MCP connector**（授权你的「交易账本」库），重启 Claude Code，然后：`claude -p "记一笔：今天210买了200股AAPL，理由是……"`

**💬 网页 / 手机 · Claude.ai**

1. **Settings → Capabilities** → 打开 **Code execution and file creation**（*"Required for skills"*）。
2. **Settings → Skills → Add → Write skill instructions** —— 把 [`SKILL.zh-CN.md`](./SKILL.zh-CN.md) 的 name、description、正文贴进去（或把文件夹打成 zip 用 **Upload a skill**）。
3. **Settings → Connectors → Notion** —— 授权你的「交易账本」库。
4. 直接说 *"记一笔：……"* ——手机 app 也一样用，而成交往往就发生在手机上。

**两种装法都不用贴任何 id。** skill 按库名找到你的账本（标题里保留「交易账本」或 `trading-ledger`），自己读 id、自己写行——拿不准就问，绝不瞎填。Claude.ai 上第一次写入会弹一个**授权确认**（Notion 写入工具默认需要批准），是正常流程不是卡住了。

> **想改造？** 不同市场、加个币种列、换你自己的情绪标签——先改 Notion 库的字段，再把 skill 指令里的枚举改成一致即可。

## 用法

- **开仓**：报成交 → 记下标的/数量/价格/理由/计划/情绪，没说理由会当场追问。
- **平仓**：*"89 把 TSM 平了"* → 找到对应持仓行，补平仓价/盈亏，并拿**你自己的计划**给执行打分：按计划 / 提前止盈 / 拖延止损 / 临时起意。
- **批量整理**：*"整理交易账本"* → 所有待确认行的疑问攒成一条消息一起问。
- **复盘**：*"复盘交易"* → 每笔已平仓交易过「理由 vs 实际 vs 执行」，持仓单再加一问：*当初的理由今天还成立吗？* 配一个每周定时提醒，金融怪杰的习惯就自动跑起来了。

## 诚实的局限

- 交易得你自己报——它不读券商数据。（故意的：券商知道你的成交，只有你知道你的理由。）
- 打分的诚实度取决于输入的诚实度。三天后补写的"入场理由"已经违背了这个工具的意义——skill 会提醒，但拦不住你。

## 免责声明

这是一个记录工具。它记录并映照**你自己的**决策；它**不**产生交易信号、行情数据或投资建议，skill 指令里明确写死了不给买卖建议。交易有亏损风险。本项目的任何内容都不构成投资建议。

## License

MIT——见 [LICENSE](./LICENSE)。随便 fork、随便用、欢迎发你自己的版本。

---

*如果这个账本对你有用，点个 ⭐ 能让更多人看到它。Bug、想法、你自己的复盘仪式 → [反馈楼](https://github.com/cruisekkk/trading-ledger/issues/1)。*
