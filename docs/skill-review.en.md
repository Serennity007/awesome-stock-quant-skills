# Collected Skills Review (skill-review)

**[中文](skill-review.md) | [English](skill-review.en.md) | [日本語](skill-review.ja.md)**

Review date: 2026-08-26. Method: structured inspection on a local machine (Windows + Python 3.11) — installable dependencies were actually installed and runnable ones actually run. Skills requiring paid API keys or external environments (QMT / IBKR broker terminals) are honestly marked "requires external environment, not tested". No test results were fabricated.

## Checklist

| Skill | Standard SKILL.md | Scripts/Dependencies | API keys required | Tested this round | One-line verdict |
|---|---|---|---|---|---|
| simonlin1212__a-stock-data | ✅ (1) | Python scripts + baostock/akshare/requests | None (baostock/akshare are free) | ❌ Not tested | Full-stack A-share data skill; well structured with dual data sources as fallbacks. |
| wbh604__UZI-Skill | ✅ (4 skill dirs) | run.py one-shot entry; deps akshare/yfinance/baostock/ddgs/playwright | None hard-required (web-search dimension uses ddgs) | ⚠️ Partially tested: deps installed, `run.py 600519.SH` launched, passed its network self-check and entered data collection (21/22 dimensions cached); the full pipeline timed out after 15 min behind the local proxy | The most comprehensive A-share deep-analysis skill and highly engineered, but heavy dependencies and a long full run. |
| BitSoulTech__BitSoulStockSkill | ✅ (in bitsoulstockskill/ subdir) | Python screening/factor/backtest scripts | None (public data sources) | ❌ Not tested | Screening + factors + backtesting in one; core directory collected, assets not included. |
| fadewalk__serenity-stock-choke | ✅ | scripts/a_stock_query.py | OpenAI-compatible key required | ❌ Requires paid key, not tested | "Choke-point" themed screening with an original angle, but depends on an LLM key. |
| shouldnotappearcalm__a-share-skill | ✅ (5 sub-skills) | Python scripts + akshare/baostock | None | ❌ Not tested | Clean data/analysis/paper-trading split; complete pipeline coverage. |
| StanleyChanH__Tushare-Finance-Skill | ✅ | Python + tushare | Tushare Pro token (points-based) | ❌ Requires paid token, not tested | Tushare wrappers with full API docs; the token is a hard gate. |
| Geralt-L__Stock-Analysis-3D | ✅ | references/stock_data_fetcher.py, multi-source (akshare/yfinance/efinance/tushare) | None hard-required (tushare optional) | ❌ Not tested | Clear 3-dimension scoring framework with sensible data-source redundancy. |
| atorber__qmt-trading-skill | ✅ (22 sub-skills) | Python + xtquant | QMT broker terminal required | ❌ Requires external environment (QMT), not tested | 21+ QMT live-trading/data-bridge skills; first choice for live trading, but requires a local QMT install. |
| staruhub__a-share-analyst | ✅ (in Geek-skills subdir) | Prompt-based, with references/scripts | None | ❌ Not tested | Analyst-persona prompt skill; lightweight and approachable. |
| tradermonty__claude-trading-skills | ✅ (72 SKILL.md) | Many Python scripts (yfinance/requests), most with tests | None hard-required (free US data) | ❌ Not tested | Broadest US-stock/CANSLIM/event-driven coverage, ships its own tests — good engineering discipline. |
| agiprolabs__claude-trading-skills | ✅ (67 SKILL.md) | Python scripts | Some need on-chain API keys (Birdeye/Helius) | ❌ Requires paid keys (some skills), not tested | Crypto/Solana-heavy; large in number but a different domain from A-shares. |
| zubair-trabzada__ai-trading-claude | ✅ (15) | Pure prompts (no Python scripts) + 5 agents | None | ➖ N/A (nothing executable), structure checked | Prompt-based trading skill set; well structured, zero dependencies. |
| yennanliu__InvestSkill | ✅ (27) | Prompt-based (DCF/filings/competitors etc.) | Some need OpenAI/Anthropic keys | ❌ Requires paid keys, not tested | US fundamental-analysis skill set with fine-grained topics. |
| tellmefrankie__ai-investment-skills | ✅ (5) | Prompts + some scripts | OpenAI/Anthropic keys required | ❌ Requires paid keys, not tested | Handy small skills: options flow, news sentiment, price alerts. |
| cruisekkk__trading-ledger | ✅ | Pure prompt/log templates (demo is a Remotion frontend, not a runtime dependency) | None | ➖ N/A (no executable scripts), structure checked | Trade-journaling skill; simple, practical, zero dependencies. |
| AlexLiu0130__ibkr-options-assistant | ✅ | Python + ib_insync (complete requirements.txt) | IBKR TWS/Gateway required | ❌ Requires external environment (IBKR), not tested | Complete options position/concentration/cost-basis scripts for IBKR users. |

## Summary

- **Fully tested this round**: only this repo's original skills `buffett-value-investing` and `technical-pattern-recognition` (see their docs/demo).
- **Partially tested**: `wbh604__UZI-Skill` (entry launches, data collection partially completed, full pipeline timed out).
- **Zero-dependency, usable as-is** (prompt-based, structure checked): `zubair-trabzada__ai-trading-claude`, `cruisekkk__trading-ledger`.
- **Requires paid keys or external environments, not tested**: Tushare token (StanleyChanH), OpenAI/Anthropic keys (fadewalk, tellmefrankie, parts of yennanliu), QMT (atorber), IBKR (AlexLiu0130), on-chain API keys (parts of agiprolabs).
- **The rest**: structure checks passed (compliant SKILL.md, clear dependencies); not individually executed this round.

> Note: "not tested" says nothing about quality — it only means an end-to-end run was not completed in this local environment. Original authors and users are welcome to contribute test results (PRs to update this table).
