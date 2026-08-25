# IBKR Options Assistant

> A complete options & stock trading assistant for Interactive Brokers — real-time Greeks, McMillan/Overby strategy library, P&L analytics, Wheel tracking, earnings warnings, and risk simulation. Designed to plug straight into Claude Code as a skill.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![IBKR](https://img.shields.io/badge/broker-Interactive%20Brokers-red.svg)](https://www.interactivebrokers.com/)

> [中文版 README](README.zh-CN.md)

<!-- screenshot: hero -->

---

## Table of Contents

- [Features](#-features)
- [At a glance — status_dashboard.py](#-at-a-glance--status_dashboardpy)
- [Requirements](#-requirements)
- [IBKR Market Data Subscriptions](#-ibkr-market-data-subscriptions)
- [Quick Start](#-quick-start)
- [Operations Guide (Second User, Auto-Restart)](#-operations-guide)
- [Trading Mode (Optional)](#-trading-mode-optional)
- [Security Model](#-security-model)
- [Claude Code Integration](#-claude-code-integration)
- [Command Reference](#-command-reference)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [Advanced](#-advanced)
- [Contributing](#-contributing)
- [License](#-license)
- [Disclaimer](#-disclaimer)

---

## ✨ Features

17 focused Python scripts. Read-only scripts output JSON so Claude (or any other agent) can reason about the data. Only `trade.py` can place orders, and only when both safety gates are explicitly opened.

**Data & quotes**
- `market_quote.py` — Real-time bid/ask/last/IV/volume for stocks, ETFs, options.
- `contracts.py` — Universal contract resolver (`SPY`, `AAPL 2026-06-19 200 C`, etc.).
- `technical_indicators.py` — RSI, MA(20/50/200), Bollinger, ATR with text summary.

**Options analysis**
- `options_chain.py` — Full option chain with Greeks, OI, volume, IV per expiry.
- `options_analyzer.py` — McMillan/Overby strategy recommender (20+ strategies across 4 tiers, IV-aware).
- `options_daily.py` — End-of-day options report: warnings, IV environment, position-specific suggestions.

**Portfolio & P&L**
- `portfolio_positions.py` — Live positions with per-leg and portfolio-level Greeks.
- `pnl_analytics.py` — Realized P&L, win rate, best/worst trades (from `ib.executions` + optional Flex CSV).
- `flex_import.py` — Parse IBKR Flex Statement CSV/XML history into normalized JSON.
- `cost_basis.py` — **Premium-adjusted** effective cost basis (the wheel-trader number IBKR doesn't compute).
- `concentration.py` — HHI, sector mix, top-N concentration risk metrics.
- `risk_simulator.py` — "What if I add this trade?" Greeks delta preview before execution.

**Strategy automation**
- `wheel_tracker.py` — Track wheel cycles (short put → assignment → covered call → called away) with cumulative premium and annualized yield.
- `earnings_calendar.py` — Next earnings date for portfolio symbols, flags options positions expiring across earnings.
- `alerts_monitor.py` — YAML-driven threshold alerts (delta, IV percentile, DTE, P&L) for cron use.

**Trade execution (opt-in)**
- `trade.py` — Stocks, single-leg options, multi-leg combos, futures, FX. Dual-gate safety (`IBKR_TRADING_ENABLED=1` + `--confirm-trade`). See [Trading Mode](#-trading-mode-optional).

**Connection layer**
- `ib_client.py` — Shared IB Gateway connection with readonly safety, per-script clientId offsets, and historical-data pacing.

---

## 📺 At a glance — `status_dashboard.py`

One command, three renderings, same data. Use it as a quick health check,
drop it into a Telegram bot, or feed JSON to an agent.

```bash
status_dashboard.py                     # rich ANSI for terminals
status_dashboard.py --output telegram   # Telegram-friendly markdown
status_dashboard.py --output json       # structured for agents
status_dashboard.py --full              # also fetch IV env + recent P&L
```

The Telegram rendering is intentionally emoji-driven so it survives
non-monospace fonts:

```
🤖 IBKR Options Assistant
🟢 2026-05-15 09:32 ET (RTH)

组合 Greeks
Δ +1240 · Γ -45 · Vega -380 · Θ +210
🟢 未实现 $+2,340.50

持仓 (1 stk + 2 opt)
📊 SPY +100 STK 🟢 $+1,240
🟢 MU -1P 110 05/23 Δ-32 🟢 $+220
🔴 AAPL -2P 200 06/19 Δ-65 🔴 $-380

本周到期 (≤7d)
⏰ MU -P 110 DTE 5 🟢

Wheel 状态
🟡 AAPL short_put · 累计 $1,450 · 年化 18.3%
🔵 SPY covered_call · 累计 $820 · 年化 12.7%
```

ANSI/JSON outputs show the same data with terminal colors or structured fields.

---

## 📋 Requirements

| Requirement | Notes |
|---|---|
| **Python** | 3.10 or newer |
| **IBKR account** | Live or paper. Paper account is fine for learning. |
| **IB Gateway** | Free download from [IBKR](https://www.interactivebrokers.com/en/trading/ibgateway-stable.php). TWS also works (different port). |
| **Market data subscriptions** | See [next section](#-ibkr-market-data-subscriptions) — needed for realtime quotes & Greeks. Delayed data is free. |
| **OS** | macOS / Linux / Windows. All scripts are pure Python. |

> **Why IB Gateway, not TWS?** Gateway is headless, uses less memory, and is the standard choice for programmatic access. TWS works too — set `IBKR_PORT=7497` (paper) or `7496` (live).

---

## 💳 IBKR Market Data Subscriptions

This toolkit's value depends heavily on **what data IBKR will send you**. Subscriptions are configured per account at Client Portal → Settings → User Settings → Market Data Subscriptions.

### What each feature needs

| Feature | Subscriptions needed | Works on delayed? |
|---------|---------------------|-------------------|
| Stock/ETF price (`market_quote.py`) | None — Snapshot bundle for realtime, otherwise delayed | ✅ Yes |
| Portfolio positions & P&L (`portfolio_positions.py`, `pnl_analytics.py`) | None — account data is always available | ✅ Yes |
| Option chain bid/ask (`options_chain.py`) | **OPRA Top of Book** | ⚠️ Partial — bid/ask only, no Greeks |
| **Option Greeks** (IV, delta, gamma, vega, theta) | **OPRA + the underlying's stock exchange** | ❌ **No** — Greeks require realtime |
| Earnings calendar (`earnings_calendar.py`) | None — uses Nasdaq public API | ✅ Yes |
| Technical indicators (`technical_indicators.py`) | None — uses historical bars (free) | ✅ Yes |

**Key insight from IBKR API docs:**
> *"To receive live Greek values it is necessary to have market data subscriptions for both the option and the underlying contract."*

Translation: if you only subscribe to OPRA but not (say) NYSE ARCA, you get SPY option **prices** but not SPY option **Greeks** — because IBKR can't compute delta/gamma without realtime underlying.

### Recommended bundles for this toolkit

| Bundle | Monthly cost | Waived if | What you get |
|--------|--------------|-----------|--------------|
| **Free (delayed)** | $0 | always | Stock prices, bid/ask, portfolio data, historical bars. **No Greeks**, no live IV environment. |
| **OPRA only** | $1.50 | $20+ commissions/mo | Realtime option bid/ask. Greeks only for symbols whose underlying you also subscribe to. |
| **US Securities Bundle + OPRA** ⭐ recommended | $11.50 | $30+ commissions/mo | Realtime stock + option data + Greeks for all US-listed symbols. The toolkit's full feature set. |

**Bundle contents (US Securities Snapshot and Futures Value Bundle):**
- Consolidated realtime NBBO for US stocks/ETFs
- Top-of-book for major futures (CME, CBOT, COMEX, NYMEX)
- OTC Markets quotes

> **Commission waiver math:** If you trade 1 lot of options per week (~4 contracts × $0.65 commission ≈ $2.60/wk = ~$10/mo), you're partway there. Two roundtrip options trades per month usually clears the $30 threshold.

### How to subscribe

1. Log into [IBKR Client Portal](https://www.interactivebrokers.com/sso/Login)
2. Settings (top right) → User Settings → Market Data Subscriptions
3. Click "Configure"
4. Search and add:
   - **"US Securities Snapshot and Futures Value Bundle"** (NL)
   - **"OPRA Top of Book"** (NL)
5. Confirm and accept
6. Subscriptions usually activate within 10 minutes; restart IB Gateway

### How the toolkit handles missing subscriptions

The default `IBKR_MARKET_DATA_TYPE=3` (delayed-smart) tells IBKR:
> *"Give me realtime if I'm subscribed; fall back to delayed if I'm not."*

This means **the toolkit works on day one with $0 subscriptions** — you just won't have Greeks until you upgrade. No Error 10089 crashes.

If you ever want to force a specific mode:
- `IBKR_MARKET_DATA_TYPE=1` — strict realtime (errors on unsubscribed)
- `IBKR_MARKET_DATA_TYPE=3` — smart delayed (default; auto-upgrades)
- `IBKR_MARKET_DATA_TYPE=4` — delayed-frozen (last cached value, useful after-hours)

**Sources:**
- [IBKR Market Data Pricing](https://www.interactivebrokers.com/en/pricing/market-data-pricing.php)
- [TWS API: Option Greeks docs](https://interactivebrokers.github.io/tws-api/option_computations.html)

---

## 🚀 Quick Start

### 1. Install IB Gateway

Download from [interactivebrokers.com/en/trading/ibgateway-stable.php](https://www.interactivebrokers.com/en/trading/ibgateway-stable.php) and install. Launch it and log in with your IBKR credentials (use **paper** mode for testing).

<!-- screenshot: gateway-login -->

### 2. Enable the API

Inside IB Gateway:

1. `Configure → Settings → API → Settings`
2. Check **Enable ActiveX and Socket Clients**
3. Check **Read-Only API** (recommended — this toolkit is read-only by design)
4. **Socket port**: `4001` (live) or `4002` (paper). Match this to `IBKR_PORT` in your `.env`.
5. **Trusted IPs**: add `127.0.0.1`
6. Leave **Allow connections from localhost only** checked — it's safer and the toolkit doesn't need it disabled.
7. Click **OK** and restart Gateway.

<!-- screenshot: gateway-api-settings -->

### 3. Clone & install

```bash
git clone https://github.com/AlexLiu0130/ibkr-options-assistant.git
cd ibkr-options-assistant

python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
$EDITOR .env
```

Minimum fields to review (defaults usually work):

```ini
IBKR_HOST=127.0.0.1
IBKR_PORT=4001                  # 4002 if paper, 7497 if TWS paper
IBKR_CLIENT_ID_BASE=11
IBKR_MARKET_DATA_TYPE=3         # default 3; auto-upgrades to realtime when subscribed
```

### 5. First call

With Gateway logged in:

```bash
python scripts/market_quote.py SPY
```

Expected output (JSON):

```json
{
  "symbol": "SPY",
  "last": 612.34,
  "bid": 612.31,
  "ask": 612.35,
  "volume": 28931402,
  "timestamp": "2026-05-12 10:14:22"
}
```

If you see this — you're done. Try `python scripts/portfolio_positions.py` next.

---

## 🛠️ Operations Guide

Running this toolkit 24/7 reliably hits two operational problems IBKR doesn't talk about loudly. Solve them once, never think about them again.

### Problem 1: Mobile app kills your Gateway session

**IBKR allows only one active session per username.** If your script runs IB Gateway on the Mac and then you open IBKR Mobile to check your portfolio, **the mobile login kicks the Gateway out** — all your scripts fail until you log Gateway back in.

**Solution: Create a second user (free)**

Use one username for the API (Gateway) and another for the mobile/TWS. They share the same account and see the same positions, but each has its own login session.

**Steps:**

1. Log into [IBKR Client Portal](https://www.interactivebrokers.com/sso/Login) with your primary username
2. Profile icon (top right) → **Settings**
3. Under **Account Settings**, find **Users & Access Rights**
4. Click **+** to add a user
5. Select **"Yes"** for *"Is this a secondary user for the primary account holder?"*
6. Complete the form (the second user can be view-only or have trading rights — your choice)
7. Submit. IBKR usually approves within 1 business day
8. Logout, log in with the new secondary username once to set the password
9. **Use the secondary username in IB Gateway**; keep the primary for the mobile app

This is **free** and the second user has full read access to the same account.

**Source:** [Adding a Second User on IBKR](https://help.piranhaprofits.com/knowledge/how-to-create-a-second-user-why-do-i-need-it)

---

### Problem 2: Gateway dies overnight, scripts fail at 9am

IB Gateway auto-logs-out daily (IBKR forces it for security) and sometimes crashes after weeks of uptime. If you rely on cron jobs or a morning routine, you want it always-on.

**Solution: Auto-restart with launchd (macOS) or systemd (Linux)**

#### macOS — launchd

Create `~/Library/LaunchAgents/com.user.ibgateway.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTD/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.ibgateway</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/IB Gateway 10.30/ibgateway.app/Contents/MacOS/JavaApplicationStub</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/ibgateway.out.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/ibgateway.err.log</string>
</dict>
</plist>
```

Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.user.ibgateway.plist
```

It will auto-restart Gateway whenever it dies. To stop: `launchctl unload ~/Library/LaunchAgents/com.user.ibgateway.plist`.

> **Note:** Gateway still requires daily 2FA via IBKR Mobile. Auto-restart handles crashes but not the once-a-day login prompt — set [auto-restart inside Gateway](#enable-auto-restart-inside-gateway) (see below) to skip 2FA for 7 days.

#### Enable auto-restart inside Gateway

In IB Gateway: **Configure → Lock and Exit → Auto Restart**. Pick a daily restart time (e.g. 03:00 ET). This keeps Gateway running for up to a week without re-entering 2FA. After 7 days you have to log in manually once.

#### Linux — systemd

Create `~/.config/systemd/user/ibgateway.service`:

```ini
[Unit]
Description=IB Gateway
After=network.target

[Service]
ExecStart=/opt/ibgateway/ibgateway
Restart=always
RestartSec=30

[Install]
WantedBy=default.target
```

```bash
systemctl --user enable --now ibgateway
```

---

### Problem 3: `Warning 2105: ushmds connection broken`

If `market_quote.py` or `technical_indicators.py` hangs and you see this in Gateway logs, **IBKR's US historical-data farm is down**. It's a server-side outage; usually self-heals in 5–30 minutes.

**What you'll see:**

```
reqHistoricalData: Timeout for Stock(...)
RuntimeError: Historical data returned empty
```

**Diagnose by enabling logs:**

```python
from ib_async import util
util.logToConsole()
# look for: Warning 2105, reqId -1: 历史市场数据场连接中断:ushmds
```

**What still works during a `ushmds` outage:**
- `options_chain.py`, `portfolio_positions.py`, `options_daily.py` — they use realtime market data (`hfarm`), not historical
- `market_quote.py`, `technical_indicators.py` — these need `ushmds`, will time out

**Workarounds:**
- Wait it out (5–30 min, IBKR usually recovers automatically)
- Restart IB Gateway to force-reconnect to a different farm endpoint
- For automation, scripts should treat historical-data errors as soft failures — the toolkit already raises a clear `RuntimeError` you can catch upstream

---

## 💱 Trading Mode (Optional)

The 13 core scripts in this toolkit are **read-only by design** — they query
data and compute Greeks, but never call `ib.placeOrder()`. If you want to
actually place orders, opt in by using `scripts/trade.py`, the **one** script
in the repo that sends orders.

`trade.py` supports stocks, single-leg options, multi-leg option combos,
futures, and FX. Every order command requires **two safety gates**:

1. `IBKR_TRADING_ENABLED=1` env var (set per shell)
2. `--confirm-trade` CLI flag (set per invocation)

Without both, the script runs in dry-run mode — it qualifies the contract,
runs pre-flight checks (Gateway readonly toggle, buying power, notional &
quantity guardrails, blocklist), and prints exactly what it *would* have sent,
without calling `placeOrder()`.

**Quick example (dry-run):**

```bash
python scripts/trade.py option MU 2026-06-12 720 P 2 \
    --action SELL --order-type LMT --limit-price 14.50
# → mode: "dry_run", result: "DRY_RUN_NO_ORDER_PLACED"
```

**Quick example (live, paper account first!):**

```bash
export IBKR_PORT=4002          # paper
export IBKR_TRADING_ENABLED=1  # Gate 1
python scripts/trade.py option MU 2026-06-12 720 P 2 \
    --action SELL --order-type LMT --limit-price 14.50 \
    --confirm-trade             # Gate 2
```

Built-in guardrails reject notionals > $100k, stock qty > 10,000, option qty
> 1,000, and any symbol in `IBKR_TRADING_BLOCKLIST` — override with
`--allow-large`.

⚠️ **Test on paper (`IBKR_PORT=4002`) before pointing at live.** Full docs,
all subcommands, cancel/list-orders workflow, and bilingual reference in
[`references/trading.md`](references/trading.md).

---

## 🔐 Security Model

This toolkit talks to a live broker session, so the security posture is worth
stating explicitly. Most of it is by design — what matters is knowing where
the trust boundaries are.

### What the toolkit can do

| Capability | Which scripts | Default state |
|------------|---------------|---------------|
| Read your IBKR account (positions, balances, P&L, market data) | All scripts | **On** — required for any analysis |
| Place / cancel / list orders against your IBKR account | `trade.py` only | **Off** — needs `IBKR_TRADING_ENABLED=1` **and** `--confirm-trade` |
| Call `api.nasdaq.com` (and `finnhub.io` if `FINNHUB_API_KEY` set) | `earnings_calendar.py` | On — public HTTPS, no IBKR credentials transmitted |
| Read / write `~/.ibkr_wheel_journal.json`, `~/.ibkr_alerts.yaml`, `~/.ibkr_flex/*.csv` | Wheel / alerts / Flex scripts | On — user-owned files in `$HOME` |
| Evaluate arbitrary code from config files | **None** | `alerts_monitor.py` parses conditions via `ast.parse` with a strict whitelist (no `eval`, no `__import__`, no attribute access) |

The 16 non-trading scripts open the IBKR connection with `readonly=True`. Only
`trade.py` uses `readonly=False`, and only after both gates are open.

### Trust boundaries

The toolkit's authority is bounded by **two layers you control**, not by the toolkit itself:

1. **The IB Gateway login** — your gateway session decides which account is reachable. Use a paper trading account (`IBKR_PORT=4002`) or a dedicated read-only IBKR sub-user if you want to cap blast radius further. Leaving Gateway's "Read-Only API" toggle enabled prevents `trade.py` from working at all, even with both software gates opened.
2. **The two software gates inside `trade.py`** — `IBKR_TRADING_ENABLED` (env) and `--confirm-trade` (CLI flag). Missing either one and the script prints a dry-run payload and exits without contacting the broker. Additional guardrails refuse oversized orders (`--allow-large` required for notional > $100k, options qty > 1000, stock qty > 10000) and honor `IBKR_TRADING_BLOCKLIST` for tickers you never want touched.

### Data the toolkit emits

Read-only scripts emit JSON to stdout (or to `--output FILE`) containing your
positions, P&L history, Greeks, Flex statement contents, and similar
broker-derived data. This is the toolkit's purpose — Claude (or any other
agent) reads that JSON to reason about your portfolio. Treat the output the
same way you'd treat a brokerage statement:

- Don't paste it into untrusted chats or share `--output` files publicly.
- The agent context window will contain the same data while you're working — keep that conversation private.
- Nothing is uploaded by the toolkit itself; it only talks to the IBKR Gateway and (optionally) Nasdaq / Finnhub public endpoints.

### Recommended setup

- Run on a personal machine, not shared infrastructure.
- Keep IB Gateway's "Allow connections from localhost only" checked.
- Default `IBKR_HOST=127.0.0.1` is correct unless you specifically need a remote Gateway.
- Use a paper account during initial testing.
- Leave `trade.py`'s safety gates closed unless you explicitly want order execution.

---

## 🤖 Claude Code Integration

This repo ships a `SKILL.md` so Claude Code can use it directly. Two ways to install:

### Option A — Symlink (recommended for development)

```bash
mkdir -p ~/.claude/skills
ln -s "$(pwd)" ~/.claude/skills/ibkr-options-assistant
```

Restart Claude Code. Ask: *"What's SPY trading at right now?"* — Claude will trigger `market_quote.py` instead of doing a web search.

### Option B — Plugin

If you use the Claude Code plugin system, point the marketplace at this repo and install `ibkr-options-assistant` from your plugin manager.

### Trigger phrases

The skill description (see `SKILL.md`) is tuned to fire whenever you mention any of: options strategy, position risk, Greeks, IV, wheel, earnings impact on options, P&L analysis, or stock price. You usually don't need to say "use IBKR".

---

## 📖 Command Reference

All scripts read `.env` automatically and accept `--help`. Every script prints JSON to stdout and logs to stderr — pipe stdout into `jq` or `--output file.json`.

| Script | One-liner | Example |
|---|---|---|
| `market_quote.py` | Real-time quote for one symbol | `python scripts/market_quote.py SPY` |
| `options_chain.py` | Option chain with Greeks | `python scripts/options_chain.py AAPL --dte-min 7 --dte-max 45` |
| `portfolio_positions.py` | Live positions + Greeks | `python scripts/portfolio_positions.py` |
| `options_analyzer.py` | Strategy recommender | `python scripts/options_analyzer.py SPY --outlook bullish --iv-context` |
| `options_daily.py` | End-of-day options report | `python scripts/options_daily.py --output ~/daily.json` |
| `pnl_analytics.py` | Realized P&L summary | `python scripts/pnl_analytics.py --days 30 --by symbol` |
| `earnings_calendar.py` | Next earnings + DTE | `python scripts/earnings_calendar.py AAPL ARM MU --days 30` |
| `risk_simulator.py` | Pre-trade Greeks preview | `python scripts/risk_simulator.py --add "AAPL 200 2026-06-26 P SELL 2"` |
| `technical_indicators.py` | RSI / MA / BB / ATR | `python scripts/technical_indicators.py NVDA --indicators rsi,ma,bb` |
| `wheel_tracker.py` | Wheel cycle journal | `python scripts/wheel_tracker.py summary` |
| `alerts_monitor.py` | Threshold alerts | `python scripts/alerts_monitor.py --config ~/.ibkr_alerts.yaml` |
| `cost_basis.py` | Premium-adjusted cost basis (wheel) | `python scripts/cost_basis.py MU --portfolio-file /tmp/portfolio.json` |
| `concentration.py` | HHI / sector / top-N concentration | `python scripts/concentration.py` |
| `flex_import.py` | Parse IBKR Flex CSV/XML history | `python scripts/flex_import.py --flex-dir ~/.ibkr_flex --since 2026-01-01` |
| `trade.py` | **Place orders (opt-in)** — see [Trading Mode](#-trading-mode-optional) | `python scripts/trade.py stock AAPL 1` (dry-run by default) |
| `contracts.py` | (library) contract resolver | imported by other scripts |
| `ib_client.py` | (library) shared connection | imported by other scripts |

### Common patterns

**Save a chain then analyze offline** (avoids hammering IBKR):

```bash
python scripts/options_chain.py AAPL --output /tmp/aapl_chain.json
python scripts/options_analyzer.py AAPL --outlook neutral \
       --chain-file /tmp/aapl_chain.json --iv-context
```

**Cron a daily alerts check** (every weekday at 9:33am):

```cron
33 9 * * 1-5 cd /path/to/ibkr-options-assistant && \
    .venv/bin/python scripts/alerts_monitor.py >> ~/.ibkr_alerts.log 2>&1
```

**Risk-check before a trade**:

```bash
python scripts/risk_simulator.py \
    --add "SPY 600 2026-06-19 P SELL 1" \
    --add "SPY 580 2026-06-19 P BUY 1"
```

---

## 🔧 Configuration

All configuration lives in `.env` (copied from `.env.example`).

| Variable | Default | Purpose |
|---|---|---|
| `IBKR_HOST` | `127.0.0.1` | Gateway host. Almost always localhost. |
| `IBKR_PORT` | `4001` | `4001` Gateway live · `4002` Gateway paper · `7496` TWS live · `7497` TWS paper |
| `IBKR_CLIENT_ID_BASE` | `11` | Scripts add an offset (7–16); the resulting clientId must be unique across all your apps. |
| `IBKR_MARKET_DATA_TYPE` | `3` | `1` realtime · `2` frozen · `3` delayed (default — auto-upgrades to realtime when subscribed) · `4` delayed-frozen |
| `FINNHUB_API_KEY` | *(unset)* | Optional. Falls back when `yahoo-earnings-calendar` is unavailable. Free at <https://finnhub.io>. |
| `IBKR_FLEX_TOKEN` | *(unset)* | Optional. IBKR Flex Web Service token for full historical P&L (beyond the ~2-day execution window). |
| `IBKR_FLEX_QUERY_ID` | *(unset)* | Optional. Flex Query ID. |

### ClientId offsets

Each script reserves a unique offset so they can coexist:

```
market_quote.py        offset 7   → clientId = base + 7
options_chain.py       offset 8
portfolio_positions.py offset 9
options_analyzer.py    offset 10
options_daily.py       offset 11
pnl_analytics.py       offset 12
risk_simulator.py      offset 13
technical_indicators   offset 14
wheel_tracker.py       offset 15
alerts_monitor.py      offset 16
```

With `IBKR_CLIENT_ID_BASE=11` (default), `market_quote.py` uses clientId `18`. If you run TWS/Gateway with **another** app on clientId `18`, raise the base.

### User data (outside the repo)

These files live in your home dir and are not committed:

- `~/.ibkr_wheel_journal.json` — wheel cycle entries
- `~/.ibkr_alerts.yaml` — alert rules
- `~/.ibkr_flex/*.csv` — Flex Statement exports

---

## ❓ Troubleshooting

Full guide: [`references/troubleshooting.md`](references/troubleshooting.md). The five issues that cover 90% of first-run problems:

### 1. `clientId X already in use`

Two scripts (or two copies of one script) hit IB Gateway with the same clientId. Either:
- Wait for the previous script to disconnect (usually a couple of seconds), **or**
- Raise `IBKR_CLIENT_ID_BASE` to a value no other app uses, **or**
- Confirm you don't have TWS *and* Gateway running at the same time on overlapping clientIds.

### 2. `Error 200: No security definition has been found`

The contract didn't resolve. Causes:
- Typo in the symbol (`SPYY` → `SPY`).
- Expired option date.
- Strike doesn't exist (e.g. `599.5` when only `599` and `600` are listed).
- Exchange routing — for some tickers you need to pass `--exchange ARCA` instead of `SMART`.

### 3. `Error 10091: subscription required`

You don't have a real-time market-data subscription for that exchange. Two fixes:
- Switch to delayed: `IBKR_MARKET_DATA_TYPE=3` in `.env`.
- Subscribe (Account Management → Settings → Market Data Subscriptions).

### 4. Connection refused / `TimeoutError`

Gateway isn't reachable. Checklist:
- Is Gateway running and **logged in**? (A logged-out Gateway doesn't accept connections.)
- Is the port in `.env` the same as Gateway's `API → Settings → Socket port`?
- Is `127.0.0.1` in **Trusted IPs**?
- Restart Gateway after changing API settings — they don't take effect live.

### 5. `modelGreeks is None`

The market is closed and there's no cached delayed-Greeks snapshot. Either wait for the next open, or set `IBKR_MARKET_DATA_TYPE=4` (delayed-frozen) and retry — delayed-frozen serves the last delayed snapshot from previous session.

---

## 📚 Advanced

| Topic | Doc |
|---|---|
| Full strategy library (20+ McMillan/Overby strategies with construction, IV preference, P&L profile) | [`references/strategies.md`](references/strategies.md) |
| Greeks primer (Delta, Gamma, Vega, Theta, Rho — practical interpretation) | [`references/greeks_primer.md`](references/greeks_primer.md) |
| Wheel strategy in depth (strike/DTE selection, roll-vs-assign decision tree) | [`references/wheel_strategy.md`](references/wheel_strategy.md) |
| All known errors and fixes | [`references/troubleshooting.md`](references/troubleshooting.md) |

---

## 🤝 Contributing

PRs and issues welcome. Keep it minimal:

- One concern per PR.
- New scripts should output JSON to stdout, log to stderr, and reserve a unique `CLIENT_ID_OFFSET`.
- No hard-coded paths — read configuration from `os.getenv()`.
- No buy/sell recommendations baked into the scripts; the toolkit produces *data*, the user (or Claude) makes decisions.

---

## 📜 License

[MIT](LICENSE). Use it, fork it, ship it.

---

## ⚠️ Disclaimer

**This software is for educational and personal use only. It is not financial advice.**

- The toolkit is **read-only by design**: it queries data and does Greeks math; it does not place orders. The repo never calls `placeOrder()`.
- All trading decisions are yours. Options trading involves substantial risk of loss and is not appropriate for every investor.
- The `options_analyzer.py` recommendations are educational mappings from outlook + risk profile → strategy templates. They do not consider your personal situation, capital, or tax position.
- Past performance shown by `pnl_analytics.py` does not predict future results.
- IBKR connectivity, market data quality, and third-party APIs (Yahoo, Finnhub) can fail. Verify critical numbers against your broker's UI before acting.

By using this software you agree that the authors and contributors are not liable for any trading losses, missed trades, or data errors.
