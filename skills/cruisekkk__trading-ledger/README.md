# trading-ledger

**English** | [简体中文](README.zh-CN.md)

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE) [![Works with: Claude Code · Claude.ai](https://img.shields.io/badge/works%20with-Claude%20Code%20·%20Claude.ai-d97757)](#install) [![Notion template](https://img.shields.io/badge/Notion%20template-EN%20·%20中文-black?logo=notion)](https://spiral-jump-106.notion.site/5ac095dfaafb4fd389875db6a5c7193a)

**A journal that makes you say your reason out loud at the moment of entry.** You report a trade in plain language — *"bought 500 NVDA at 135, stop at 128, betting on the post-earnings dip filling"* — and an AI writes it to your own Notion database: ticker, size, price, **and the part every spreadsheet journal loses: your thesis, your plan, and how you felt**. If you don't state a reason, it asks. That's the whole trick.

```
You:  bought 1 TSM July call this morning, same thesis as before earnings
AI:   Logged ✅ TSM 0731C475 · Long · Open
      ❓ To-confirm: how many contracts, at what price?
      ❓ And the plan — holding through earnings, or is there a stop?
You:  1 contract at 18.50, holding to earnings
AI:   Updated ✅ Thesis: pre-earnings run-up · Plan: hold through earnings
```

Then, on review day: *"review my trades"* — and it walks every closed trade through three questions: **did the thesis play out? did you follow the plan? which trades were emotion-tagged?** A per-plan loss grades better than a lucky win, and it says so.

<table>
<tr>
<th width="50%">💬 Web / phone · Claude.ai</th>
<th width="50%">⌨️ Terminal · Claude Code</th>
</tr>
<tr>
<td width="50%"><img src="./assets/demo-web.gif" alt="claude.ai demo: log a trade in one sentence — it captures the thesis and asks for the missing target" width="100%" /></td>
<td width="50%"><img src="./assets/demo-terminal.gif" alt="terminal demo: closing a trade matches the open row and grades execution against your own plan" width="100%" /></td>
</tr>
</table>

## Why

The habit that keeps surfacing in the *Market Wizards* interviews is unglamorous: a written record of every trade's decision process, reviewed on a schedule. Not to track P&L — the broker does that — but because **the entry reason decays overnight**. A week later you genuinely cannot remember whether you bought on a thesis or on a feeling, and your memory will flatter you.

The problem with every journaling tool: it's a form, and forms die in three days. This rides a habit you already have — you're in an AI chat anyway. One sentence at the moment of the fill, and the moment is captured before it can be revised.

## What it is

A **Claude skill** (a single `SKILL.md` of instructions) + your own **Notion database**. No server, no backend, your data stays in your Notion. Capture anywhere you have Claude (phone / laptop / chat). **Heads up:** the skill / connector setup currently needs the **paid** tier of Claude.

Sister project: [time-ledger](https://github.com/cruisekkk/time-ledger) — same method (Notion as source of truth + a skill that parses plain language + batch-asks instead of guessing), applied to where your hours go.

## Install

**Step 0 — duplicate the Notion template**: [🇬🇧 English](https://spiral-jump-106.notion.site/5ac095dfaafb4fd389875db6a5c7193a) · [🇨🇳 中文](https://spiral-jump-106.notion.site/5f92910834c44321af7661f98f062e27). One click; fields, views, and example rows included.

Then pick your surface:

**⌨️ Terminal · Claude Code**

```bash
git clone https://github.com/cruisekkk/trading-ledger.git
mkdir -p ~/.claude/skills/trading-ledger
cp trading-ledger/SKILL.md ~/.claude/skills/trading-ledger/SKILL.md
```

Add the **Notion MCP connector** (grant your `trading-ledger` database), restart Claude Code, then: `claude -p "log a trade: bought 200 AAPL at 210 today, thesis is ..."`

**💬 Web / phone · Claude.ai**

1. **Settings → Capabilities** → turn on **Code execution and file creation** (*"Required for skills"*).
2. **Settings → Skills → Add → Write skill instructions** — paste the name, description, and body from [`SKILL.md`](./SKILL.md) (or zip the folder and use **Upload a skill**).
3. **Settings → Connectors → Notion** — grant access to your `trading-ledger` database.
4. Just say *"log a trade: ..."* — works from the phone app too, which is where fills actually happen.

**No id to paste, either way.** The skill finds your database by title (keep `trading-ledger` / `交易账本` in it), reads its id, and writes the row — asking instead of guessing when unsure. On Claude.ai the first write pops an **approve** prompt (Notion's write tools default to *needs approval*) — expected, not a hang.

> **Customize** — different markets, another currency column, your own emotion labels? Change the fields in your Notion database, then mirror them in the skill's instructions (the select values must match).

## Usage

- **Open**: report the fill → it records ticker / size / price / thesis / plan / emotion, and asks for the thesis if you didn't give one.
- **Close**: *"closed the TSM position at 89"* → it finds the open row, fills exit / P&L, and grades the execution against your own plan: per plan / early exit / delayed stop / impulse.
- **Batch reconcile**: *"tidy up my trading ledger"* → every to-confirm row's questions, batched into one message.
- **Review**: *"review my trades"* → thesis vs outcome vs execution for every closed trade, plus the question that matters for open ones: *does the entry thesis still hold today?* Pair it with a weekly reminder and it becomes the Market Wizards habit on rails.

## Honest limitations

- You have to actually report the trades — it doesn't read your broker. (On purpose: the broker knows your fills, only you know your reasons.)
- The grading is only as honest as your inputs. If you backfill the thesis three days later, you've defeated the point — the skill nags about this, but it can't stop you.

## Disclaimer

This is a journaling tool. It records and mirrors your own decisions; it does **not** produce trading signals, price data, or investment advice, and the skill is explicitly instructed never to recommend a buy or sell. Trading involves risk of loss. Nothing here is financial advice.

## License

MIT — see [LICENSE](./LICENSE). Fork it, use it, ship your own version.

---

*If trading-ledger is useful, a ⭐ helps more people find it. Bugs, ideas, your own review rituals → [the feedback thread](https://github.com/cruisekkk/trading-ledger/issues/1).*
