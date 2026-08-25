# IBKR 期权助手 (IBKR Options Assistant)

> 一套完整的 Interactive Brokers 期权与股票交易助手——实时 Greeks、McMillan/Overby 策略库、盈亏分析、Wheel 跟踪、财报预警、风险模拟。设计成可直接作为 Skill 接入 Claude Code。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![IBKR](https://img.shields.io/badge/broker-Interactive%20Brokers-red.svg)](https://www.interactivebrokers.com/)

> [English README](README.md)

<!-- screenshot: hero -->

---

## 目录

- [功能特性](#-功能特性)
- [一眼看全 — status_dashboard.py](#-一眼看全--status_dashboardpy)
- [环境要求](#-环境要求)
- [IBKR 行情订阅](#-ibkr-行情订阅)
- [快速开始](#-快速开始)
- [运维指南（双用户、自动重启）](#-运维指南)
- [安全模型](#-安全模型)
- [Claude Code 集成](#-claude-code-集成)
- [命令参考](#-命令参考)
- [配置](#-配置)
- [故障排查](#-故障排查)
- [进阶](#-进阶)
- [贡献](#-贡献)
- [许可证](#-许可证)
- [免责声明](#-免责声明)

---

## ✨ 功能特性

13 个专注的 Python 脚本。每个脚本都输出 JSON，便于 Claude（或其他 Agent）做推理；工具本身不会给出买卖信号。

**数据与行情**
- `market_quote.py` — 股票、ETF、期权的实时 bid/ask/last/IV/volume。
- `contracts.py` — 通用合约解析器（`SPY`、`AAPL 2026-06-19 200 C` 等）。
- `technical_indicators.py` — RSI、MA(20/50/200)、Bollinger、ATR，附文字摘要。

**期权分析**
- `options_chain.py` — 含 Greeks、OI、volume、IV 的完整期权链（按到期日组织）。
- `options_analyzer.py` — McMillan/Overby 策略推荐（4 层共 20+ 策略，IV 环境感知）。
- `options_daily.py` — 收盘后期权日报：预警、IV 环境、对应持仓的具体建议。

**组合与盈亏**
- `portfolio_positions.py` — 实时持仓 + 每条腿和组合级 Greeks。
- `pnl_analytics.py` — 已实现盈亏、胜率、最佳/最差交易（来自 `ib.executions` + 可选 Flex CSV）。
- `risk_simulator.py` — "加上这笔交易会怎样？"——执行前预览 Greeks 变化。

**策略自动化**
- `wheel_tracker.py` — 跟踪 wheel 周期（short put → 指派 → covered call → called away），含累计权利金与年化收益率。
- `earnings_calendar.py` — 组合标的的下一次财报日期，标记跨越财报的期权仓位。
- `alerts_monitor.py` — 基于 YAML 的阈值告警（delta、IV 分位、DTE、P&L），适合 cron 调度。

**连接层**
- `ib_client.py` — 共享的 IB Gateway 连接，自带 readonly 安全、按脚本 clientId 偏移、历史数据节流。

---

## 📺 一眼看全 — `status_dashboard.py`

一个命令、三种渲染，同一份数据。可以当终端快速健康检查，可以接 Telegram bot，也可以喂 JSON 给 agent。

```bash
status_dashboard.py                     # 终端彩色 ANSI
status_dashboard.py --output telegram   # Telegram 友好的 Markdown
status_dashboard.py --output json       # 给 agent 用的结构化数据
status_dashboard.py --full              # 多跑 IV 环境 + 近期盈亏
```

Telegram 渲染特意用 emoji 驱动，不依赖等宽对齐：

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

ANSI 输出在终端里带彩色，JSON 输出方便 agent 自由组织回复。

---

## 📋 环境要求

| 要求 | 备注 |
|---|---|
| **Python** | 3.10 或更高 |
| **IBKR 账户** | Live 或 paper 均可。Paper 账户用于学习已足够。 |
| **IB Gateway** | 从 [IBKR 官网](https://www.interactivebrokers.com/en/trading/ibgateway-stable.php) 免费下载。TWS 也行（端口不同）。 |
| **行情订阅** | 见[下一节](#-ibkr-行情订阅) —— 实时报价与 Greeks 需要订阅。延迟数据免费。 |
| **操作系统** | macOS / Linux / Windows。所有脚本都是纯 Python。 |

> **为什么用 IB Gateway，不用 TWS？** Gateway 是无界面的，内存占用低，是程序化访问的首选。TWS 也可以——把 `IBKR_PORT` 设为 `7497`（paper）或 `7496`（live）。

---

## 💳 IBKR 行情订阅

工具的价值在很大程度上取决于 **IBKR 给你推送什么数据**。订阅是按账户配置的：Client Portal → Settings → User Settings → Market Data Subscriptions。

### 各功能对订阅的需求

| 功能 | 所需订阅 | 延迟数据可用？ |
|---|---|---|
| 股票/ETF 价格 (`market_quote.py`) | 无 —— 实时需要 Snapshot 套餐，否则使用延迟 | ✅ 可用 |
| 组合持仓与 P&L (`portfolio_positions.py`、`pnl_analytics.py`) | 无 —— 账户数据始终可用 | ✅ 可用 |
| 期权链 bid/ask (`options_chain.py`) | **OPRA Top of Book** | ⚠️ 部分 —— 只有 bid/ask，无 Greeks |
| **期权 Greeks** (IV、delta、gamma、vega、theta) | **OPRA + 标的对应的股票交易所** | ❌ **不可** —— Greeks 必须实时 |
| 财报日历 (`earnings_calendar.py`) | 无 —— 使用 Nasdaq 公开 API | ✅ 可用 |
| 技术指标 (`technical_indicators.py`) | 无 —— 使用历史 bar（免费） | ✅ 可用 |

**IBKR API 文档的关键提示：**
> *"To receive live Greek values it is necessary to have market data subscriptions for both the option and the underlying contract."*

翻译：如果你只订阅了 OPRA 但没订阅（比如）NYSE ARCA，你可以拿到 SPY 期权的**报价**，但拿不到 SPY 期权的 **Greeks**——因为 IBKR 没有实时标的价格就算不出 delta/gamma。

### 推荐的订阅套餐

| 套餐 | 月费 | 减免条件 | 内容 |
|---|---|---|---|
| **免费（延迟）** | $0 | 始终 | 股票报价、bid/ask、组合数据、历史 bar。**无 Greeks**、无实时 IV 环境。 |
| **仅 OPRA** | $1.50 | 每月佣金 $20+ | 实时期权 bid/ask。仅当标的也订阅时才有 Greeks。 |
| **US Securities Bundle + OPRA** ⭐ 推荐 | $11.50 | 每月佣金 $30+ | 美股全部实时数据 + 期权数据 + 所有 US 上市标的的 Greeks。工具完整功能。 |

**Bundle 内容（US Securities Snapshot and Futures Value Bundle）：**
- 美股/ETF 整合的实时 NBBO
- 主要期货（CME、CBOT、COMEX、NYMEX）顶部行情
- OTC Markets 报价

> **佣金减免数学：** 如果你每周交易 1 手期权（~4 手合约 × $0.65 佣金 ≈ $2.60/周 = ~$10/月），已经走到一半了。每月两次往返期权交易通常就过了 $30 门槛。

### 怎么订阅

1. 登录 [IBKR Client Portal](https://www.interactivebrokers.com/sso/Login)
2. 右上角 Settings → User Settings → Market Data Subscriptions
3. 点击 "Configure"
4. 搜索并添加：
   - **"US Securities Snapshot and Futures Value Bundle"**（NL）
   - **"OPRA Top of Book"**（NL）
5. 确认接受
6. 通常 10 分钟内生效；重启 IB Gateway

### 工具如何处理缺失订阅

默认值 `IBKR_MARKET_DATA_TYPE=3`（delayed-smart）告诉 IBKR：
> *"如果我订阅了就给我实时；否则降级为延迟。"*

这意味着 **零订阅情况下工具也能第一天就用** —— 只是没 Greeks，除非升级订阅。不会出现 Error 10089 崩溃。

如果你想强制特定模式：
- `IBKR_MARKET_DATA_TYPE=1` —— 严格实时（未订阅会报错）
- `IBKR_MARKET_DATA_TYPE=3` —— 智能延迟（默认；已订阅自动升级到实时）
- `IBKR_MARKET_DATA_TYPE=4` —— 延迟冻结（上次缓存值，盘后有用）

**参考资料：**
- [IBKR Market Data Pricing](https://www.interactivebrokers.com/en/pricing/market-data-pricing.php)
- [TWS API: Option Greeks 文档](https://interactivebrokers.github.io/tws-api/option_computations.html)

---

## 🚀 快速开始

### 1. 安装 IB Gateway

从 [interactivebrokers.com/en/trading/ibgateway-stable.php](https://www.interactivebrokers.com/en/trading/ibgateway-stable.php) 下载并安装。打开并用 IBKR 凭据登录（测试用 **paper** 模式）。

<!-- screenshot: gateway-login -->

### 2. 启用 API

在 IB Gateway 里：

1. `Configure → Settings → API → Settings`
2. 勾选 **Enable ActiveX and Socket Clients**
3. 勾选 **Read-Only API**（推荐 —— 本工具就是只读设计）
4. **Socket 端口**：`4001`（live）或 `4002`（paper）。和 `.env` 里的 `IBKR_PORT` 对齐。
5. **Trusted IPs**：加上 `127.0.0.1`
6. 保持 **Allow connections from localhost only** 勾选 —— 安全且本工具不需要关闭
7. 点 **OK** 并重启 Gateway

<!-- screenshot: gateway-api-settings -->

### 3. 克隆并安装

```bash
git clone https://github.com/AlexLiu0130/ibkr-options-assistant.git
cd ibkr-options-assistant

python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
$EDITOR .env
```

需要确认的最小字段（默认通常就行）：

```ini
IBKR_HOST=127.0.0.1
IBKR_PORT=4001                  # 4002 paper、7497 TWS paper
IBKR_CLIENT_ID_BASE=11
IBKR_MARKET_DATA_TYPE=3         # 默认 3；订阅后自动升级到实时
```

### 5. 第一次调用

确保 Gateway 已登录后：

```bash
python scripts/market_quote.py SPY
```

预期输出（JSON）：

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

看到这个就成功了。接着试 `python scripts/portfolio_positions.py`。

---

## 🛠️ 运维指南

7×24 稳定运行会遇到两个 IBKR 不太提的运维问题。一次解决，以后不再操心。

### 问题 1：手机 App 会踢掉你的 Gateway 会话

**IBKR 同用户名只允许一个活跃会话。** 如果你的脚本在 Mac 上跑 IB Gateway，然后打开 IBKR Mobile 看组合，**手机登录会把 Gateway 踢下线** —— 你所有脚本都失败，直到重新登录 Gateway。

**解决：创建第二个用户（免费）**

API 用一个用户名（Gateway），手机/TWS 用另一个。它们共享同一个账户、看同一份持仓，但各自有独立会话。

**步骤：**

1. 用主用户名登录 [IBKR Client Portal](https://www.interactivebrokers.com/sso/Login)
2. 右上角头像 → **Settings**
3. **Account Settings** 下找到 **Users & Access Rights**
4. 点 **+** 添加用户
5. 在 *"Is this a secondary user for the primary account holder?"* 选 **"Yes"**
6. 填好表格（第二用户可只读，也可有交易权限 —— 自己选）
7. 提交。IBKR 通常 1 个工作日内批准
8. 退出，用新副用户名登录一次设置密码
9. **IB Gateway 用副用户名**；主用户名留给手机 App

**免费**，副用户对同一账户拥有完整只读权限。

**参考：** [Adding a Second User on IBKR](https://help.piranhaprofits.com/knowledge/how-to-create-a-second-user-why-do-i-need-it)

---

### 问题 2：Gateway 半夜挂掉，脚本 9 点失败

IB Gateway 每天会自动退出登录（IBKR 出于安全强制要求），有时连续运行几周也会崩。如果你依赖 cron 或晨间例行流程，需要它常驻。

**解决：用 launchd（macOS）或 systemd（Linux）自动重启**

#### macOS — launchd

创建 `~/Library/LaunchAgents/com.user.ibgateway.plist`：

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

加载：

```bash
launchctl load ~/Library/LaunchAgents/com.user.ibgateway.plist
```

Gateway 挂掉就自动重启。想停：`launchctl unload ~/Library/LaunchAgents/com.user.ibgateway.plist`。

> **注意：** Gateway 仍需通过 IBKR Mobile 每日 2FA。自动重启处理崩溃但处理不了每天那次登录提示 —— 设[Gateway 内自动重启](#enable-auto-restart-inside-gateway)（见下文）可跳过 7 天 2FA。

#### 在 Gateway 内开启自动重启

IB Gateway 里：**Configure → Lock and Exit → Auto Restart**。选一个每日重启时间（如 03:00 ET）。这样 Gateway 最多 7 天不需要 2FA。7 天后必须手动登录一次。

#### Linux — systemd

创建 `~/.config/systemd/user/ibgateway.service`：

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

### 问题 3：`Warning 2105: ushmds connection broken`

如果 `market_quote.py` 或 `technical_indicators.py` 卡住，Gateway 日志里看到这个，**说明 IBKR 的美股历史数据农场宕机**。服务端问题，通常 5–30 分钟自愈。

**你会看到：**

```
reqHistoricalData: Timeout for Stock(...)
RuntimeError: Historical data returned empty
```

**用日志诊断：**

```python
from ib_async import util
util.logToConsole()
# 看：Warning 2105, reqId -1: 历史市场数据场连接中断:ushmds
```

**`ushmds` 中断时仍可用的功能：**
- `options_chain.py`、`portfolio_positions.py`、`options_daily.py` —— 用实时行情（`hfarm`），不依赖历史数据
- `market_quote.py`、`technical_indicators.py` —— 依赖 `ushmds`，会超时

**变通方案：**
- 等（5–30 分钟，IBKR 通常自动恢复）
- 重启 IB Gateway，强制重连到另一个农场端点
- 自动化场景下，脚本应把历史数据错误当作软失败处理 —— 工具已经抛出明确的 `RuntimeError`，上层可捕获

---

## 🔐 安全模型

本工具会连接真实券商会话，安全边界值得明确写出来。绝大多数行为都是设计本意 —— 关键在于知道信任边界落在哪里。

### 工具能做什么

| 能力 | 涉及脚本 | 默认状态 |
|------|---------|---------|
| 读 IBKR 账户（持仓、余额、盈亏、行情） | 全部脚本 | **开** —— 任何分析都需要 |
| 下单 / 撤单 / 查单 | 仅 `trade.py` | **关** —— 需同时 `IBKR_TRADING_ENABLED=1` **且** `--confirm-trade` |
| 访问 `api.nasdaq.com`（设了 `FINNHUB_API_KEY` 时还有 `finnhub.io`） | `earnings_calendar.py` | 开 —— 公开 HTTPS，不会传输 IBKR 凭据 |
| 读写 `~/.ibkr_wheel_journal.json`、`~/.ibkr_alerts.yaml`、`~/.ibkr_flex/*.csv` | Wheel / alerts / Flex 相关 | 开 —— 都在 `$HOME` 下你自己的文件 |
| 执行配置文件里的任意代码 | **没有** | `alerts_monitor.py` 用 `ast.parse` 严格白名单解析条件，无 `eval`、无 `__import__`、无属性访问 |

16 个只读脚本调用 IBKR 用 `readonly=True`；只有 `trade.py` 用 `readonly=False`，且要双闸门都打开才生效。

### 信任边界

工具的权限由**你能控制的两层**决定，不是工具自己说了算：

1. **IB Gateway 登录** —— 当前会话登录的是哪个账户，工具能访问的就是哪个。想进一步缩小爆炸半径，可以用 paper 账户（`IBKR_PORT=4002`）或者专门给只读用的 IBKR 子用户。把 Gateway 的 "Read-Only API" 勾上，`trade.py` 即使两层软闸门都打开也下不出单。
2. **`trade.py` 内部的两道软闸门** —— `IBKR_TRADING_ENABLED`（环境变量）和 `--confirm-trade`（命令行 flag）。少任何一道，脚本就打印一份 dry-run payload 然后退出，根本不会连券商。额外的护栏拒绝超大单（名义 > $100k、期权 > 1000 张、股票 > 10000 股需 `--allow-large`），并支持 `IBKR_TRADING_BLOCKLIST` 拉黑标的。

### 工具输出的数据

只读脚本会把 JSON 打到 stdout（或 `--output FILE`），内容包括你的持仓、盈亏历史、Greeks、Flex 报表等券商衍生数据 —— 这就是工具的目的，Claude（或其他 agent）正是读这份 JSON 来推理你的组合。把这些输出当券商对账单对待：

- 不要把它贴到不信任的对话里，不要公开分享 `--output` 文件
- 工作时 agent 上下文窗口里也会有同样的数据 —— 那段对话本身也保持私密
- 工具本身不会上传任何东西，只跟 IBKR Gateway 和（可选的）Nasdaq / Finnhub 公开端点通信

### 推荐设置

- 在个人机器上跑，不要放共享基础设施
- IB Gateway 的 "Allow connections from localhost only" 保持勾上
- `IBKR_HOST=127.0.0.1` 默认值就够用，除非你有特殊远程 Gateway 需求
- 第一次跑用 paper 账户
- 不主动要用下单功能时，`trade.py` 的两道闸门都保持关闭

---

## 🤖 Claude Code 集成

本仓库带 `SKILL.md`，Claude Code 可以直接用。两种安装方式：

### 方式 A —— 软链接（推荐开发使用）

```bash
mkdir -p ~/.claude/skills
ln -s "$(pwd)" ~/.claude/skills/ibkr-options-assistant
```

重启 Claude Code。问：*"SPY 现在多少？"* —— Claude 会触发 `market_quote.py`，而不是去 web 搜索。

### 方式 B —— 插件

如果你用 Claude Code 插件系统，把 marketplace 指向这个仓库，并从插件管理器装 `ibkr-options-assistant`。

### 触发短语

Skill 描述（见 `SKILL.md`）经过调校，提到以下任一就会触发：期权策略、仓位风险、Greeks、IV、wheel、财报对期权影响、P&L 分析、股价。通常不需要说 "用 IBKR"。

---

## 📖 命令参考

所有脚本自动读取 `.env` 并支持 `--help`。每个脚本把 JSON 打到 stdout、日志打到 stderr —— 把 stdout 管道给 `jq` 或者用 `--output file.json`。

| 脚本 | 一句话 | 示例 |
|---|---|---|
| `market_quote.py` | 单标的实时报价 | `python scripts/market_quote.py SPY` |
| `options_chain.py` | 含 Greeks 的期权链 | `python scripts/options_chain.py AAPL --dte-min 7 --dte-max 45` |
| `portfolio_positions.py` | 实时持仓 + Greeks | `python scripts/portfolio_positions.py` |
| `options_analyzer.py` | 策略推荐 | `python scripts/options_analyzer.py SPY --outlook bullish --iv-context` |
| `options_daily.py` | 收盘后期权日报 | `python scripts/options_daily.py --output ~/daily.json` |
| `pnl_analytics.py` | 已实现盈亏汇总 | `python scripts/pnl_analytics.py --days 30 --by symbol` |
| `earnings_calendar.py` | 下次财报 + DTE | `python scripts/earnings_calendar.py AAPL ARM MU --days 30` |
| `risk_simulator.py` | 交易前 Greeks 预览 | `python scripts/risk_simulator.py --add "AAPL 200 2026-06-26 P SELL 2"` |
| `technical_indicators.py` | RSI / MA / BB / ATR | `python scripts/technical_indicators.py NVDA --indicators rsi,ma,bb` |
| `wheel_tracker.py` | Wheel 周期日志 | `python scripts/wheel_tracker.py --summary` |
| `alerts_monitor.py` | 阈值告警 | `python scripts/alerts_monitor.py --config ~/.ibkr_alerts.yaml` |
| `contracts.py` | （库）合约解析器 | 被其他脚本 import |
| `ib_client.py` | （库）共享连接 | 被其他脚本 import |

### 常用范式

**先保存期权链再离线分析**（避免重复打 IBKR）：

```bash
python scripts/options_chain.py AAPL --output /tmp/aapl_chain.json
python scripts/options_analyzer.py AAPL --outlook neutral \
       --chain-file /tmp/aapl_chain.json --iv-context
```

**Cron 每日告警检查**（工作日 9:33）：

```cron
33 9 * * 1-5 cd /path/to/ibkr-options-assistant && \
    .venv/bin/python scripts/alerts_monitor.py >> ~/.ibkr_alerts.log 2>&1
```

**交易前做风险检查**：

```bash
python scripts/risk_simulator.py \
    --add "SPY 600 2026-06-19 P SELL 1" \
    --add "SPY 580 2026-06-19 P BUY 1"
```

---

## 🔧 配置

所有配置在 `.env`（从 `.env.example` 复制而来）。

| 变量 | 默认 | 作用 |
|---|---|---|
| `IBKR_HOST` | `127.0.0.1` | Gateway 主机。基本上总是 localhost。 |
| `IBKR_PORT` | `4001` | `4001` Gateway live · `4002` Gateway paper · `7496` TWS live · `7497` TWS paper |
| `IBKR_CLIENT_ID_BASE` | `11` | 脚本在此基础上加偏移（7–16）；最终 clientId 必须在你所有 app 中唯一。 |
| `IBKR_MARKET_DATA_TYPE` | `3` | `1` 实时 · `2` 冻结 · `3` 延迟（默认 —— 订阅后自动升级实时）· `4` 延迟冻结 |
| `FINNHUB_API_KEY` | *(未设置)* | 可选。当 `yahoo-earnings-calendar` 不可用时降级使用。<https://finnhub.io> 免费申请。 |
| `IBKR_FLEX_TOKEN` | *(未设置)* | 可选。IBKR Flex Web Service token，用于完整历史 P&L（超出约 2 天的成交窗口）。 |
| `IBKR_FLEX_QUERY_ID` | *(未设置)* | 可选。Flex Query ID。 |

### ClientId 偏移

每个脚本预留一个唯一偏移，可并存：

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

`IBKR_CLIENT_ID_BASE=11`（默认）时，`market_quote.py` 用 clientId `18`。如果你在 TWS/Gateway 上跑**另一个**应用刚好占用 `18`，把 base 调高。

### 用户数据（不在仓库内）

这些文件在你的家目录、不入仓库：

- `~/.ibkr_wheel_journal.json` —— wheel 周期记录
- `~/.ibkr_alerts.yaml` —— 告警规则
- `~/.ibkr_flex/*.csv` —— Flex Statement 导出

---

## ❓ 故障排查

完整指南：[`references/troubleshooting.md`](references/troubleshooting.md)。覆盖 90% 首次运行问题的五个错误：

### 1. `clientId X already in use`

两个脚本（或一个脚本的两份拷贝）用同一个 clientId 连到 IB Gateway。要么：
- 等前一个脚本断开（通常几秒），**或**
- 把 `IBKR_CLIENT_ID_BASE` 调高到没人用的值，**或**
- 确认你不同时跑 TWS 和 Gateway，且 clientId 不重叠。

### 2. `Error 200: No security definition has been found`

合约没解析出来。原因：
- 代码拼错（`SPYY` → `SPY`）。
- 过期的期权日期。
- 行权价不存在（如 `599.5`，但只挂了 `599` 和 `600`）。
- 交易所路由 —— 某些代码需要传 `--exchange ARCA` 而非 `SMART`。

### 3. `Error 10091: subscription required`

你没有该交易所的实时行情订阅。两种修复：
- 切到延迟：`.env` 里 `IBKR_MARKET_DATA_TYPE=3`。
- 订阅（Account Management → Settings → Market Data Subscriptions）。

### 4. Connection refused / `TimeoutError`

Gateway 不可达。检查清单：
- Gateway 在跑且**已登录**？（未登录的 Gateway 不接受连接。）
- `.env` 里的端口和 Gateway `API → Settings → Socket port` 一致？
- `127.0.0.1` 在 **Trusted IPs** 里？
- 改完 API 设置后重启了 Gateway？（不重启不生效。）

### 5. `modelGreeks is None`

市场休市且没有缓存的延迟 Greeks 快照。要么等下次开盘，要么设 `IBKR_MARKET_DATA_TYPE=4`（延迟冻结）再试 —— 延迟冻结提供上次 session 的最后延迟快照。

---

## 📚 进阶

| 主题 | 文档 |
|---|---|
| 完整策略库（20+ McMillan/Overby 策略，含构造、IV 偏好、盈亏图） | [`references/strategies.md`](references/strategies.md) |
| Greeks 入门（Delta、Gamma、Vega、Theta、Rho —— 实务解读） | [`references/greeks_primer.md`](references/greeks_primer.md) |
| Wheel 策略深度（行权价/DTE 选择，roll-vs-assign 决策树） | [`references/wheel_strategy.md`](references/wheel_strategy.md) |
| 全部已知错误与修复 | [`references/troubleshooting.md`](references/troubleshooting.md) |

---

## 🤝 贡献

欢迎 PR 和 issue。保持简洁：

- 一个 PR 只做一件事。
- 新脚本要把 JSON 输出到 stdout、日志到 stderr，并预留唯一的 `CLIENT_ID_OFFSET`。
- 不硬编码路径 —— 从 `os.getenv()` 读配置。
- 脚本里不内置买卖建议；工具产出**数据**，由用户（或 Claude）做决策。

---

## 📜 许可证

[MIT](LICENSE)。随便用、fork、发布。

---

## ⚠️ 免责声明

**本软件仅用于教育和个人用途，不构成投资建议。**

- 工具是 **只读设计**：查询数据、做 Greeks 计算；不下单。仓库永远不调用 `placeOrder()`。
- 所有交易决策由你自己负责。期权交易包含可观亏损风险，并非适合所有投资者。
- `options_analyzer.py` 的推荐是从 outlook + 风险偏好到策略模板的教育性映射。它不考虑你的个人情况、资金或税务地位。
- `pnl_analytics.py` 展示的历史业绩不预测未来。
- IBKR 连接、行情质量、第三方 API（Yahoo、Finnhub）都可能失败。下单前关键数字以经纪商 UI 为准。

使用本软件即表示你同意：作者和贡献者不对任何交易损失、漏单或数据错误承担责任。
