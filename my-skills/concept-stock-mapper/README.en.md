# 🎯 Theme Keyword → Concept Stock Mapper | Type a Theme, Get Its Players Instantly

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (East Money / 10jqka public APIs)

Feed it a hot-theme keyword and get a concept-stock list in seconds. Feed it multiple keywords and compare which theme is stronger right now. Fuzzy-matches East Money / 10jqka concept boards, pulls constituents, and sorts them by gain, turnover, or main-force capital — the fastest way to answer “which stocks belong to this theme, and which sub-theme is winning?” after a news alert.

## Typical scenarios

- You see news about `"controlled nuclear fusion"`, `"commercial aerospace"`, `"solid-state batteries"`, etc., and want to know the related stocks immediately.
- Compare `"commercial aerospace"` vs `"low-altitude economy"` to see which board is stronger right now: board gain, net capital inflow, and top constituent gains.
- Identify internal structure within a theme: leaders (limit-up or largest gainers), mid-caps (large turnover, moderate turnover rate), and laggards (small gain, low turnover).

## Dependencies

```bash
pip install akshare pandas
```

Verified environment: Python 3.11 + akshare 1.18.96 + pandas.

## Command-line usage

```bash
# Single theme, top 15 by gain
python scripts/concept_mapper.py --keywords 商业航天

# Multi-theme comparison, sorted by main-force net inflow
python scripts/concept_mapper.py --keywords 商业航天,核聚变,固态电池 --top 15 --sort main_force --out result.csv

# Sorted by turnover rate
python scripts/concept_mapper.py --keywords 固态电池 --top 20 --sort turnover
```

## Parameters

| Parameter | Default | Description |
|---|---|---|
| `--keywords` | required | Comma-separated theme keywords, e.g. `商业航天,核聚变` |
| `--top` | 15 | Number of constituents to output per theme |
| `--sort` | `change_pct` | Sort dimension: `change_pct` (gain), `turnover` (turnover rate), `main_force` (main-force net inflow) |
| `--out` | `concept_stocks.csv` | Output CSV path |
| `--no-proxy` | — | Kept for backward compatibility; the script now disables system proxies by default |

## Data sources and fallback strategy

1. **Concept board matching**: fuzzy-match via `akshare.stock_board_concept_name_ths()` using the 10jqka concept list.
2. **Theme strength**: use `akshare.stock_board_concept_info_ths()` to fetch board gain, net capital inflow, turnover, etc.
3. **Constituent details**:
   - First try `akshare.stock_board_concept_cons_em()` (East Money constituents, includes main-force data).
   - If that fails due to network or data-source issues, fall back to scraping the 10jqka concept detail page (code, name, close, gain, turnover, amount).
4. **Main-force capital**:
   - When the East Money constituent interface is available, use its main-force net inflow field directly.
   - If scraping the 10jqka individual-stock capital-flow page fails, the script retries once; if it still fails, **turnover amount** is used as a proxy for capital activity, and the CSV `note` column is annotated accordingly.
5. **Proxy handling**: the script disables system proxies by default (clears `HTTP_PROXY`/`HTTPS_PROXY` environment variables) to avoid local proxies such as `127.0.0.1:7890` breaking East Money / 10jqka requests. The old `--no-proxy` flag is kept for compatibility but is no longer required.

## Output

The terminal prints a theme-strength comparison table and the top N constituents for each theme. The CSV adds `theme_rank` (rank within the theme) and `note` (fallback annotation) columns.

## Risk notes

- Theme rotation is fast; today's hot theme may fade tomorrow. The output is only a snapshot.
- `Leader stocks` often hit limit-up or gap up sharply; chasing them carries very high risk.
- Constituents may be included just because they ride the theme hype; verify fundamentals and theme purity manually.

## Disclaimer

This skill is for study and research only, not investment advice. All data comes from public interfaces; users must judge for themselves and bear their own risks.
