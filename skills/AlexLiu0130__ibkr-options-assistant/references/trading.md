# Trading Mode — `scripts/trade.py`

> **⚠️ WARNING — This script CAN move real money.**
>
> The rest of the toolkit is read-only by design. `trade.py` is the **only** script
> that calls `ib.placeOrder()`. Before you point it at a live account, test it
> against a **paper account** (`IBKR_PORT=4002`). Lose money on the paper account
> first so you don't lose it on the real one.

---

## How to enable trading

By default the toolkit is read-only. To send orders you must perform three
one-time setup steps, then satisfy two gates on every invocation.

### One-time setup

1. **Disable Gateway's Read-Only API toggle**

   In IB Gateway:

   ```
   Configure → Settings → API → Settings
   ```

   - **UN**check **"Read-Only API"**
   - Keep **"Enable ActiveX and Socket Clients"** checked
   - Keep **"Allow connections from localhost only"** checked (safer)
   - Click **OK** and **restart Gateway**

   If Read-Only API stays on, IBKR rejects orders with Error 2105. `trade.py`
   surfaces this clearly under `checks.gateway_readonly_off: false` and refuses
   to place an order.

2. **Use a username with trading rights**

   If you use a secondary user (recommended — see Operations Guide in the main
   README), make sure the secondary user has **trading rights**, not just
   view-only. You set this when creating the secondary user in Client Portal.

3. **Set `IBKR_TRADING_ENABLED=1` in your shell**

   ```bash
   export IBKR_TRADING_ENABLED=1
   ```

   Or add to your `.env` file (`.env.example` documents it). This is Gate 1.

---

## Two-gate safety design

Every order command checks **both gates**. Either gate failing → dry-run preview
only, no `placeOrder()` call. This is by design.

| Gate | What | Where it lives |
|---|---|---|
| 1 | `IBKR_TRADING_ENABLED=1` env var | Set once per shell session (or in `.env`) |
| 2 | `--confirm-trade` CLI flag | Pass per invocation. Must be re-typed each time. |

Why two? Gate 1 prevents accidentally running a trade command while you only
*meant* to query data. Gate 2 prevents a copy-pasted command from an old shell
history (where the env var is still set) from firing an order without your
explicit per-call consent.

### Dry-run output

When gates fail (or you're testing), you get JSON like:

```json
{
  "mode": "dry_run",
  "order": { ... },
  "contract": { ... },
  "checks": {
    "trading_env_enabled": false,
    "confirm_flag_passed": false,
    "gateway_readonly_off": true,
    ...
    "notes": [
      "Gate 1 not passed: set IBKR_TRADING_ENABLED=1 ...",
      "Gate 2 not passed: add --confirm-trade ..."
    ]
  },
  "result": "DRY_RUN_NO_ORDER_PLACED"
}
```

`mode` is `"dry_run"` or `"live"`. **Always check this field** in any
automated pipeline.

---

## Hard guardrails

The script refuses orders that match any of these unless you pass `--allow-large`:

| Guardrail | Threshold |
|---|---|
| Notional > **$100,000** | Estimated as `qty × price × multiplier` (multiplier=100 for options) |
| Stock quantity > **10,000 shares** | |
| Option quantity > **1,000 contracts** | |
| Symbol in `IBKR_TRADING_BLOCKLIST` env var (comma-separated, e.g. `TSLA,GME`) | No override — must remove from list |

Stop-loss missing on LMT/MKT orders is only a **warning** (some MKT orders are
intentional). It appears in `checks.notes`.

### Blocklist example

```bash
export IBKR_TRADING_BLOCKLIST="TSLA,GME,AMC"
```

Any symbol on this list rejects with `blocklist_ok: false`. To trade it,
remove it from the env var.

---

## Subcommand examples

### Stock

```bash
# Dry run (no env, no flag)
python scripts/trade.py stock AAPL 100 --action BUY --order-type MKT

# Live buy at limit
IBKR_TRADING_ENABLED=1 python scripts/trade.py stock AAPL 100 \
    --action BUY --order-type LMT --limit-price 250.50 --tif GTC \
    --confirm-trade
```

### Single-leg option

```bash
# Sell 2 cash-secured puts at $14.50 limit
IBKR_TRADING_ENABLED=1 python scripts/trade.py option MU 2026-06-12 720 P 2 \
    --action SELL --order-type LMT --limit-price 14.50 \
    --confirm-trade
```

`EXPIRY` accepts both `2026-06-12` and `20260612`. `RIGHT` is `C` or `P`.

### Multi-leg combo (bull put spread)

```bash
# Sell the 600 put, buy the 590 put → net credit $2.50
IBKR_TRADING_ENABLED=1 python scripts/trade.py combo \
    --leg "SPY 2026-06-26 600 P SELL 1" \
    --leg "SPY 2026-06-26 590 P BUY 1" \
    --order-type LMT --limit-price 2.50 \
    --confirm-trade
```

Each `--leg` is `"SYMBOL EXPIRY STRIKE RIGHT ACTION QTY"`. All legs must share
the same underlying. `--limit-price` is the **net** debit (positive) or credit
(negative) per spread unit.

### Futures

```bash
# Buy 1 ES front-month at market
IBKR_TRADING_ENABLED=1 python scripts/trade.py future ES 1 \
    --action BUY --order-type MKT --confirm-trade

# Specific contract month
IBKR_TRADING_ENABLED=1 python scripts/trade.py future ES 1 \
    --last-trade-month 202609 --action BUY --order-type LMT --limit-price 6200 \
    --confirm-trade
```

### Forex

```bash
IBKR_TRADING_ENABLED=1 python scripts/trade.py forex EURUSD 25000 \
    --action BUY --order-type LMT --limit-price 1.0850 \
    --confirm-trade
```

---

## Managing open orders

### List

```bash
python scripts/trade.py list-orders
```

(No gates needed — listing is read-only.)

Output:

```json
{
  "open_orders": [
    {
      "order_id": 7,
      "symbol": "AAPL",
      "sec_type": "STK",
      "action": "BUY",
      "order_type": "LMT",
      "quantity": 100,
      "limit_price": 250.50,
      "tif": "GTC",
      "status": "Submitted",
      "filled": 0,
      "remaining": 100
    }
  ],
  "count": 1
}
```

### Cancel

```bash
python scripts/trade.py cancel 7
```

(No gates needed — cancelling reduces risk.)

---

## What happens on a real `placeOrder`

After both gates pass and all pre-flight checks succeed, `trade.py`:

1. Calls `ib.placeOrder(contract, order)`
2. Waits up to 8 seconds for an initial status update
3. Returns the result block:

```json
{
  "mode": "live",
  "order": { ... },
  "contract": { ... },
  "checks": { ... },
  "result": {
    "order_id": 12,
    "perm_id": 1862341087,
    "status": "Submitted",
    "filled_qty": 0,
    "remaining_qty": 100,
    "avg_fill_price": 0,
    "log": [ ... last 5 status updates ... ]
  }
}
```

If the status is still `PreSubmitted` or `Submitted` when we return, the order
is **alive on IBKR's side** — use `list-orders` to track it, or use Gateway's
own Orders panel.

---

## Concerns & FAQ

**Q: Why `readonly=False` on the IBKR connection?**
A: To place orders. `ib_client.ib_connect()` defaults to `readonly=True`; we
explicitly override for this script and only this script. The 13 read-only
scripts all stay `readonly=True`.

**Q: What if the order partially fills?**
A: The 8-second wait returns whatever state the order is in. If `status` is
`Submitted` with `remaining > 0`, the order is still working — re-poll via
`list-orders` or cancel via `cancel ORDER_ID`.

**Q: Combo legs all on the same side?**
A: Each `ComboLeg` carries its own `action` (BUY/SELL). The outer order on the
`Bag` is always `BUY 1` of the spread — the *bag's* action is just the
direction of "buy this combination as defined by the legs". For a spread you
sell (credit spread), set the legs as documented in `parsed_legs`.

**Q: Can I cancel-all?**
A: Not as one command — pull `list-orders`, then loop `cancel ORDER_ID` per row.
This is deliberate to avoid wiping a portfolio with a typo.

---

## 中文版

> **⚠️ 警告 —— 此脚本会动真金白银。**
>
> 工具包其它脚本全部只读。`trade.py` 是**唯一**会调 `ib.placeOrder()` 的脚本。
> 在指向实盘账户之前，先用**模拟账户**（`IBKR_PORT=4002`）跑通。先在模拟盘亏过
> 钱，实盘就不会亏同一笔。

---

### 开启交易模式

工具包默认只读。要发单，需做三步一次性配置，然后每次调用满足两道闸门。

#### 一次性配置

1. **关掉 Gateway 的 "Read-Only API" 选项**

   IB Gateway 里：

   ```
   Configure → Settings → API → Settings
   ```

   - **取消勾选** **"Read-Only API"**
   - 保留勾选 **"Enable ActiveX and Socket Clients"**
   - 保留勾选 **"Allow connections from localhost only"**（更安全）
   - 点 **OK**，**重启 Gateway**

   如果 Read-Only API 还开着，IBKR 会返回 Error 2105 拒单。`trade.py` 会在
   `checks.gateway_readonly_off: false` 字段里清楚提示，并拒绝下单。

2. **使用有交易权限的用户名**

   如果你用副用户（推荐做法，见主 README 的 Operations Guide），确保副用户
   有**交易权限**而不是只读。这个在 Client Portal 创建副用户时设置。

3. **shell 里设置 `IBKR_TRADING_ENABLED=1`**

   ```bash
   export IBKR_TRADING_ENABLED=1
   ```

   或写进 `.env`（参考 `.env.example`）。这是闸门 1。

---

### 两道闸门安全设计

每次下单命令都会同时检查**两道闸门**，任一不过 → 仅 dry-run 预览，**不会**调
`placeOrder()`。这是设计如此。

| 闸门 | 内容 | 位置 |
|---|---|---|
| 1 | 环境变量 `IBKR_TRADING_ENABLED=1` | 每个 shell 会话设一次（或写在 `.env`） |
| 2 | CLI 标志 `--confirm-trade` | **每次**调用必须重新输入 |

为什么两道？闸门 1 防止你只想查数据时不小心跑了交易命令。闸门 2 防止从旧 shell
历史里粘出来的命令（环境变量还在）不经你当次明确同意就把单子发出去。

### Dry-run 输出示例

闸门不过（或你在测试）时，JSON 输出长这样：

```json
{
  "mode": "dry_run",
  "order": { ... },
  "contract": { ... },
  "checks": {
    "trading_env_enabled": false,
    "confirm_flag_passed": false,
    ...
    "notes": [
      "Gate 1 not passed: set IBKR_TRADING_ENABLED=1 ...",
      "Gate 2 not passed: add --confirm-trade ..."
    ]
  },
  "result": "DRY_RUN_NO_ORDER_PLACED"
}
```

`mode` 取 `"dry_run"` 或 `"live"`。**自动化流程一定要检查这个字段**。

---

### 硬性风控

下列任一条件触发即拒单，除非加 `--allow-large`：

| 风控项 | 阈值 |
|---|---|
| 名义金额 > **$100,000** | 估算 `数量 × 价 × 乘数`（期权乘数 = 100） |
| 股票数量 > **10,000 股** | |
| 期权数量 > **1,000 合约** | |
| 标的在 `IBKR_TRADING_BLOCKLIST`（逗号分隔，比如 `TSLA,GME`） | 不可强行覆盖，必须从列表移除 |

LMT/MKT 单子没设止损只会**警告**（有些 MKT 是有意为之），不会拒单。警告会在
`checks.notes` 里出现。

#### 黑名单示例

```bash
export IBKR_TRADING_BLOCKLIST="TSLA,GME,AMC"
```

名单内标的会 `blocklist_ok: false`。要交易就从环境变量里删掉。

---

### 子命令示例

#### 股票

```bash
# 干跑（既没设环境变量也没加 flag）
python scripts/trade.py stock AAPL 100 --action BUY --order-type MKT

# 实盘限价买
IBKR_TRADING_ENABLED=1 python scripts/trade.py stock AAPL 100 \
    --action BUY --order-type LMT --limit-price 250.50 --tif GTC \
    --confirm-trade
```

#### 单腿期权

```bash
# 卖 2 张现金担保 put，限价 $14.50
IBKR_TRADING_ENABLED=1 python scripts/trade.py option MU 2026-06-12 720 P 2 \
    --action SELL --order-type LMT --limit-price 14.50 \
    --confirm-trade
```

`EXPIRY` 接受 `2026-06-12` 或 `20260612`。`RIGHT` 取 `C` 或 `P`。

#### 多腿组合（牛市价差）

```bash
# 卖 600 put，买 590 put → 净收 $2.50
IBKR_TRADING_ENABLED=1 python scripts/trade.py combo \
    --leg "SPY 2026-06-26 600 P SELL 1" \
    --leg "SPY 2026-06-26 590 P BUY 1" \
    --order-type LMT --limit-price 2.50 \
    --confirm-trade
```

每个 `--leg` 格式 `"SYMBOL EXPIRY STRIKE RIGHT ACTION QTY"`。所有腿必须同标的。
`--limit-price` 是每份组合的**净**借方（正）或贷方（负）。

#### 期货

```bash
# 买 1 张 ES 主力，市价
IBKR_TRADING_ENABLED=1 python scripts/trade.py future ES 1 \
    --action BUY --order-type MKT --confirm-trade

# 指定合约月
IBKR_TRADING_ENABLED=1 python scripts/trade.py future ES 1 \
    --last-trade-month 202609 --action BUY --order-type LMT --limit-price 6200 \
    --confirm-trade
```

#### 外汇

```bash
IBKR_TRADING_ENABLED=1 python scripts/trade.py forex EURUSD 25000 \
    --action BUY --order-type LMT --limit-price 1.0850 \
    --confirm-trade
```

---

### 管理在场订单

#### 列出

```bash
python scripts/trade.py list-orders
```

（不需闸门，列单本来就只读。）

#### 撤单

```bash
python scripts/trade.py cancel 7
```

（不需闸门，撤单是降风险动作。）

---

### 实盘 `placeOrder` 发生了什么

两道闸门 + 所有 pre-flight 检查都通过后，`trade.py`：

1. 调 `ib.placeOrder(contract, order)`
2. 最多等 8 秒拿到首个状态更新
3. 返回 `result` 块（包含 `order_id`、`status`、`filled_qty` 等）

如果返回时状态还是 `PreSubmitted` 或 `Submitted`，说明订单**已经在 IBKR 那边
挂着**——用 `list-orders` 跟踪，或者直接在 Gateway 的 Orders 面板看。

---

### 常见疑问

**问：为什么连接用 `readonly=False`？**
答：因为要发单。`ib_client.ib_connect()` 默认 `readonly=True`，我们**只在这一
个脚本**显式覆盖。其它 13 个只读脚本保持 `readonly=True`。

**问：部分成交怎么办？**
答：8 秒等待返回时拿到的就是当时的状态。如果是 `Submitted` 且 `remaining > 0`，
单子还在工作——用 `list-orders` 重新查，或 `cancel ORDER_ID` 撤掉。

**问：能一键全撤吗？**
答：不能。需要先 `list-orders` 然后循环 `cancel ORDER_ID`。这是故意的，避免一
个手误把整个组合都炸了。
