# NOTICE

## Attribution

This project, **Stock-Analysis-3D**, is a derivative work based on:

- **[Stock-Analysis-Skill](https://github.com/liusai0820/Stock-Analysis-Skill)** by [@liusai0820](https://github.com/liusai0820) (Yzz)
  - License: MIT
  - The original project provided the foundational architecture, technical
    indicator calculations, graceful data-source degradation strategy, and
    the overall Claude Code skill packaging.

The original project itself acknowledges inspiration from:

- **[daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis)** by [@ZhuLinsen](https://github.com/ZhuLinsen)

We preserve and honor those acknowledgments — credit propagates upstream.

## What's New in Stock-Analysis-3D

Stock-Analysis-3D upgrades the original from a single-dimension (technical)
scoring system to a three-dimensional composite scoring framework:

```
Score 100 = Technical 50 + Fundamental 30 + News 20
```

### Major Additions

1. **Fundamental scoring (30 pts)** — Six dimensions × 5 pts each:
   - PE valuation
   - PB valuation
   - ROE (return on equity)
   - Revenue YoY growth
   - Gross margin
   - Debt-to-asset ratio
2. **News sentiment scoring (20 pts)** — Three dimensions filled by Claude
   based on WebSearch results:
   - News sentiment (10 pts)
   - Institutional actions (5 pts)
   - Capital flow (5 pts)
3. **Multi-source fundamentals fetcher** — akshare → efinance → yfinance
   graceful degradation for A-share, HK, and US markets.
4. **Recalibrated signal tiers** — 80+/65/50/35/20/<20 thresholds aligned
   with the 100-point composite scale.
5. **3D decision dashboard output format** — Per-stock card now displays
   technical / fundamental / news breakdowns separately.

### Files Modified from Upstream

- `references/stock_data_fetcher.py` — Added ~590 lines for fundamentals
  and 3D composite scoring.
- `SKILL.md` — New 3D workflow, news scoring instructions for Claude.
- `references/output-format-template.md` — 3D dashboard format.

### Files Preserved Unchanged

- `references/analysis-prompt-template.md` — Original Claude analysis
  framework retained as-is.

## License

This project remains under the **MIT License**, the same license as the
original. Both copyright notices are preserved in [LICENSE](./LICENSE).

## How to Sync Upstream

If the original Stock-Analysis-Skill repository receives improvements you
want to incorporate:

```bash
git remote add upstream https://github.com/liusai0820/Stock-Analysis-Skill.git
git fetch upstream
git merge upstream/main
# Resolve conflicts in stock_data_fetcher.py and SKILL.md as needed
```

The `pre-3d-refactor` tag in this repository points to the unmodified state
of the upstream code at the time of forking, which makes three-way merges
cleaner.
