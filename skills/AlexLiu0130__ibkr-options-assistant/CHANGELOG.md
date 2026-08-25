# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.6] - 2026-05-15

### Added
- **`status_dashboard.py`** — at-a-glance snapshot of the entire IBKR
  Options Assistant state with three renderings from the same data:
    - `--output ansi` (default): colored, aligned ASCII for terminals
    - `--output telegram`: emoji-driven Markdown that survives non-monospace
      fonts (chat clients, mobile)
    - `--output json`: structured data for agents to recompose freely
  Quick mode is one IBKR session (~5s) covering portfolio Greeks,
  positions with ITM flags, this-week expiries, and Wheel stages.
  `--full` adds IV environment per held symbol and recent realized P&L.
  ClientId offset 20.
- README "At a glance" section in EN + 中文 with example output.
- SKILL.md workflow entry: "What's my account state right now?" / "Status
  update" tells the agent to use `status_dashboard.py` for one-glance
  account snapshots.

### Why
A user-facing snapshot that works equally well in three contexts:
sitting at the terminal, chatting in Telegram with Atlas, or any other
agent that wants the data raw. Single source of truth (one builder + three
renderers) avoids the maintenance overhead of separate scripts.

## [0.2.5] - 2026-05-14

### Fixed
- **ITM/OTM judgement bug (root cause was schema, not math).** Earlier
  versions of `portfolio_positions.py` and `options_daily.py` exposed the
  *option contract's* mid price as `market_price` at the top of every OPT
  entry while burying the *underlying spot* inside `greeks.und_price`.
  Agents reading the JSON compared the two top-level numbers (`market_price`
  vs `strike`) and reported the wrong ITM/OTM status. Each OPT entry now
  emits `option_price` (explicit rename of the contract price), `und_price`,
  `itm`, and `moneyness` (= `und_price - strike`) at the top level.
  `options_daily.py` propagates the same fields into the `expiry_warning`
  payload. When Greeks are unavailable, `und_price` and `itm` are `null`
  (never silently `false`).
- **Short-put `max_loss` formula** in `options_daily.py`. Was
  `-strike * 100`; correct is `-(strike - premium) * 100` (the credit
  received offsets the assignment-cost loss). Previously over-reported the
  worst case by the full premium amount on every short-put recommendation.
- **`options_chain.py` data freshness lie.** `data_type` was hard-coded to
  `"realtime"` regardless of `IBKR_MARKET_DATA_TYPE` or whether IBKR
  actually upgraded the feed. Now reflects the ticker's real
  `marketDataType` (`realtime` / `frozen` / `delayed` / `delayed-frozen`).
- **Double-counting between session and Flex fills** in `cost_basis.py` and
  `pnl_analytics.py`. When a Flex CSV overlapped the IBKR session's ~2-day
  window, the same fill landed in both lists, doubling premiums collected
  and realized P&L. Both scripts now deduplicate by
  `(symbol, right, strike, expiration, side, qty, price, trade_date)` with
  a per-tuple occurrence index, so legitimate same-day partial fills at the
  same price (TWS splits market orders across exchanges) are preserved.
- **`options_analyzer.py` falsy bugs**: `not all(prices)` rejected legal
  `price=0.0` (far-OTM bids) — switched to `is None` check. `type` field
  no longer claims `"credit"` when `all_priced=False`. `probability_of_profit`
  renamed to `pop_approx_first_leg` on multi-leg strategies to flag that
  it's a single-leg heuristic.
- **`wheel_tracker._current_stage`** now returns `"closed"` for the
  no-positions-but-has-journal case (was `"called_away"`, which is
  unverifiable from positions alone).
- **`trade.py` RTH auto-detection** — documented the early-close edge case
  (Black Friday / Christmas Eve / day before July 4 close at 13:00 ET).
  Auto-detection still uses the regular 09:30–16:00 window; use
  `--outside-rth` explicitly on those ~3 days/year.

### Why
Atlas (the consuming agent) reported reading wrong ITM/OTM status from
position output. Root-cause analysis showed it wasn't a math bug — the
script never told consumers *where to find* the underlying spot price.
Fixing this with schema (lift `und_price` to the top, add an explicit
`itm` boolean) prevents the next agent from making the same inference.

## [0.2.4] - 2026-05-14

### Changed
- **Renamed** the project from `ibkr-trader-toolkit` to `ibkr-options-assistant`.
  - GitHub repo renamed (old URL 301-redirects to the new one).
  - `SKILL.md` frontmatter `name:` updated; description, scripts, and behavior unchanged.
  - README titles and all references updated.

### Why
The old name overlapped with order-execution / bot-style IBKR skills and
buried the toolkit's actual positioning. This is an options-analysis
assistant designed to be driven by Claude (or another AI agent), not a
trading bot — the new name makes that distinction visible in search
results and skill catalogs.

## [0.2.3] - 2026-05-14

### Docs
- New "Security Model" section in `README.md` and `README.zh-CN.md` covering
  what the toolkit can do, the two trust boundaries the user controls
  (Gateway login + `trade.py` dual gates), how output data should be
  treated, and a recommended setup. No code changes.

### Why
ClawScan ASI03 (Identity and Privilege Abuse) and ASI06 (Memory and
Context Poisoning) flag the toolkit's intrinsic broker-account access
and JSON output as risk surface. Both are design-intent rather than
defects — ClawScan itself notes "purpose-aligned" on ASI06. Documenting
the security model explicitly lets users and reviewers see that the
trust boundaries are deliberate and where they can be tightened
further. The `clawscan-note` published alongside this release covers
the same ground for automated review.

## [0.2.2] - 2026-05-14

### Security
- `alerts_monitor.py` no longer uses `eval()` to evaluate rule conditions.
  Conditions are now parsed with `ast.parse(mode="eval")` and walked by a
  small interpreter that only accepts: the documented variables
  (`price`, `delta`, `iv`, `dte`, `unrealized_pnl`), numeric literals,
  comparisons (`< <= > >= == !=`), boolean operators (`and / or / not`),
  arithmetic (`+ - * /`, unary `-`), and the calls `abs / min / max /
  round`. Attribute access, indexing, other function calls, lambdas, and
  comprehensions are rejected at parse time, eliminating the
  ClawScan ASI05 "unrevised eval()" finding.

### Why
ClawScan flagged the eval-based path as high-risk even with restricted
globals, because eval-based alert rules are materially riskier than a
restricted parser, especially for a script documented as cron-friendly.
The new evaluator preserves every condition shown in the docs while
removing the attack surface.

## [0.2.1] - 2026-05-14

### Added
- `trade.py` now supports extended-hours order routing. By default, the
  script auto-detects whether the current time is inside US/Eastern Regular
  Trading Hours (09:30–16:00 weekdays) and sets `outsideRth=True` on the
  order when placed off-hours. Two explicit flags override this:
    - `--outside-rth` — force outsideRth=True (pre/post-market, overnight)
    - `--rth-only` — force outsideRth=False (RTH-only routing)
  Both flags work for `stock`, `option`, `combo`, `future`, and `forex`
  subcommands.
- Order payload JSON now includes an `outside_rth` field, and the dry-run
  preview shows the resolved value plus the reason (auto-detection or
  explicit flag).

### Why
Without `outsideRth=True`, orders submitted off-hours sit on IBKR's gateway
until 09:30 ET (Warning 399). With it, orders can route to ECNs during the
pre/post-market sessions (04:00–09:30 and 16:00–20:00 ET) and to overnight
sessions where supported. Auto-detection is the default so users don't
have to remember the flag in normal use.

## [0.2.0] - 2026-05-14

### Added
- **`cost_basis.py`** — premium-adjusted effective cost basis for wheel positions
  (subtracts collected premium from broker avg cost). Discovers held stocks via
  `--portfolio-file` or accepts symbols positionally. Pulls option fills from
  `ib.fills()` and optional `~/.ibkr_flex/*.csv`. ClientId offset 17.
- **`concentration.py`** — HHI, top-3/top-5 concentration %, sector breakdown
  with built-in ~70-ticker GICS map, plus actionable warnings (top-3 > 30%,
  any sector > 20%, single position > 20%). Reuses `portfolio_positions` fetch.
  ClientId offset 18.
- **`flex_import.py`** — parses both CSV and XML IBKR Flex Statement files via
  `ibflex` library (or plain `csv` fallback). Normalizes trades into a unified
  JSON schema consumable by `pnl_analytics.py` / `cost_basis.py`. Supports
  `--since` and `--symbol` filters.
- **`trade.py`** — opt-in order execution for stocks, single-leg options,
  multi-leg combos (BAG/ComboLeg), futures, and FX. **Dual-gate safety**:
  refuses to place orders unless both `IBKR_TRADING_ENABLED=1` is set AND
  `--confirm-trade` is passed. Subcommands: `stock`, `option`, `combo`,
  `future`, `forex`, `cancel`, `list-orders`. Guardrails: notional > $100k,
  options qty > 1000, stock qty > 10000 require `--allow-large`; blocklist
  via `IBKR_TRADING_BLOCKLIST`. ClientId offset 19; the only script that uses
  `readonly=False`.
- **`references/trading.md`** — bilingual (EN + 中文) documentation of trading
  setup, both safety gates, the Gateway "Read-Only API" toggle, and full
  examples for each subcommand.
- **`references/options_book_summary.md`** — 500-line operational-rules
  reference distilled from McMillan / Overby / Natenberg / Sinclair. 13
  sections covering IV environment playbook, strike/DTE selection, adjustment
  decision trees, position sizing, skew interpretation, earnings IV crush,
  volatility estimators, Greeks-vs-Greeks math, common mistakes.
- **`README.zh-CN.md`** — full Chinese translation of the README. Both
  versions cross-link from the top.
- 5th SKILL.md workflow: "Should I roll position X?" — covers portfolio
  confirm, roll candidate chain survey, and decision tree pointer.
- `Trading Mode (Optional)` section in README pointing to `references/trading.md`.
- `CHANGELOG.md` (this file) at repo root.
- Module-level constant `IBKR_REALIZED_PNL_SENTINEL_THRESHOLD` in
  `pnl_analytics.py` documenting the IBKR sentinel-value cutoff.

### Changed
- **All scripts normalized to English-first.** Module docstrings, `log()`
  strings, inline comments, and argparse help text translated from Chinese
  to English. The Chinese strategy display names in `options_analyzer.py`'s
  `STRATEGIES[*].name_cn` JSON output keys are intentionally preserved.
- `risk_simulator.py` concentration warning threshold lowered from 50% to 30% to
  match the SKILL.md workflow documentation.
- `wheel_tracker.py` annualized-return math no longer multiplies capital by the
  number of journal entries (rolls reuse capital, they don't multiply it). Now
  uses the latest entry's strike × 100 as the open-leg capital.
- README's `IBKR_MARKET_DATA_TYPE` default documented as `3` in both the Quick
  Start example and the Configuration table, matching `.env.example`.
- README API setup step clarified: "Leave 'Allow connections from localhost
  only' checked — it's safer and the toolkit doesn't need it disabled."
- GitHub repo description updated to remove the stale "Streamlit dashboard"
  mention.
- `references/wheel_strategy.md` examples now use the actual positional
  subcommand syntax (`wheel_tracker.py add-entry ...` and
  `wheel_tracker.py summary`) instead of the non-existent `--add-entry` flag.
- `requirements.txt` adds `ibflex>=0.16` and upper bounds on `pandas` (<3) and
  `numpy` (<3).
- SKILL.md Operating Constraints table updated: "Smart data type" replaces
  the stale "Real-time by default" claim that contradicted the `=3` default.

## [0.1.4] - 2026-05-14

### Added
- Operations Guide section in README: second-user setup to keep Gateway alive
  when using the mobile app, launchd/systemd auto-restart recipes, and triage
  for the `ushmds` (US historical-data farm) outage.

## [0.1.3] - 2026-05-14

### Added
- Comprehensive IBKR market data subscription guide in README: per-feature
  subscription requirements, recommended bundles, commission-waiver math.

## [0.1.2] - 2026-05-14

### Changed
- Default `IBKR_MARKET_DATA_TYPE` is now `3` (delayed-smart). IBKR auto-upgrades
  to realtime for subscribed instruments and falls back to delayed otherwise,
  avoiding Error 10089 ("subscription required") on day one.

## [0.1.1] - 2026-05-13

### Changed
- SKILL.md rewritten for readability on the ClawHub web view.

### Removed
- Streamlit dashboard (out of scope for a Claude Code skill; the toolkit emits
  JSON for the agent to reason about, not a UI to look at).

### Fixed
- `earnings_calendar.py` now uses the Nasdaq public API instead of the
  deprecated yahoo-earnings-calendar source.
- `options_analyzer.py` no longer crashes when a strategy's max-loss is
  unlimited (e.g. naked calls).

## [0.1.0] - 2026-05-12

### Added
- Initial release of IBKR Trader Toolkit.
- 13 Python scripts covering market quotes, option chains, portfolio Greeks,
  McMillan/Overby strategy recommender, P&L analytics, risk simulator, wheel
  tracker, earnings calendar, technical indicators, and YAML-driven alerts.
- Shared `ib_client.py` connection layer with readonly safety, per-script
  clientId offsets, and historical-data pacing.
- SKILL.md so Claude Code can use the toolkit directly.
- Reference docs: full strategy library, Greeks primer, wheel strategy guide,
  troubleshooting.

[Unreleased]: https://github.com/AlexLiu0130/ibkr-options-assistant/compare/v0.2.6...HEAD
[0.2.6]: https://github.com/AlexLiu0130/ibkr-options-assistant/releases/tag/v0.2.6
[0.2.5]: https://github.com/AlexLiu0130/ibkr-options-assistant/releases/tag/v0.2.5
[0.2.4]: https://github.com/AlexLiu0130/ibkr-options-assistant/releases/tag/v0.2.4
[0.2.3]: https://github.com/AlexLiu0130/ibkr-options-assistant/releases/tag/v0.2.3
[0.2.2]: https://github.com/AlexLiu0130/ibkr-options-assistant/releases/tag/v0.2.2
[0.2.1]: https://github.com/AlexLiu0130/ibkr-options-assistant/releases/tag/v0.2.1
[0.2.0]: https://github.com/AlexLiu0130/ibkr-options-assistant/releases/tag/v0.2.0
[0.1.4]: https://github.com/AlexLiu0130/ibkr-options-assistant/releases/tag/v0.1.4
[0.1.3]: https://github.com/AlexLiu0130/ibkr-options-assistant/releases/tag/v0.1.3
[0.1.2]: https://github.com/AlexLiu0130/ibkr-options-assistant/releases/tag/v0.1.2
[0.1.1]: https://github.com/AlexLiu0130/ibkr-options-assistant/releases/tag/v0.1.1
[0.1.0]: https://github.com/AlexLiu0130/ibkr-options-assistant/releases/tag/v0.1.0
