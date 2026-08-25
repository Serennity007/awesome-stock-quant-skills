"""
trade.py — IBKR trading execution script (the ONLY script in this toolkit that places orders).

⚠️  SAFETY: This script CAN move real money. Test on paper first (IBKR_PORT=4002).

Two-gate design (BOTH must pass before any order is sent):
  Gate 1 — environment:        IBKR_TRADING_ENABLED=1   must be set
  Gate 2 — per-invocation flag: --confirm-trade          must be passed on CLI

Without both gates, the script does a dry-run preview and prints a JSON describing
the order it WOULD have placed. No `ib.placeOrder()` call is reached.

Connection uses CLIENT_ID_OFFSET=19 and readonly=False (the only script that does).
The script also verifies Gateway's "Read-Only API" toggle is OFF — if it's on,
IBKR raises Error 2105 / rejects the order. We surface that error clearly.

Subcommands:
  stock SYMBOL QTY ...
  option SYMBOL EXPIRY STRIKE RIGHT QTY ...
  combo --leg "..." --leg "..." ...
  future SYMBOL [LASTTRADEMONTH] QTY ...
  forex PAIR QTY ...
  cancel ORDER_ID
  list-orders

Output is always JSON to stdout, logs to stderr. See references/trading.md for details.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional

from ib_async import (
    Bag,
    ComboLeg,
    Contract,
    ContFuture,
    Forex,
    Future,
    LimitOrder,
    MarketOrder,
    Option,
    Order,
    Stock,
    StopOrder,
)

from contracts import resolve, us_stock
from ib_client import ib_connect, log

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

CLIENT_ID_OFFSET = 19  # reserved for trade.py

# Guardrails (override required via --allow-large)
MAX_NOTIONAL_USD = 100_000
MAX_STOCK_QTY = 10_000
MAX_OPTION_QTY = 1_000

# Env vars
ENV_ENABLED = "IBKR_TRADING_ENABLED"
ENV_BLOCKLIST = "IBKR_TRADING_BLOCKLIST"

# Order wait — how long we listen for a status update after placeOrder
ORDER_STATUS_TIMEOUT_SEC = 8.0


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def _normalize_expiry(expiry: str) -> str:
    """Accept '2026-06-26' or '20260626' → return 'YYYYMMDD'."""
    s = expiry.strip().replace("-", "").replace("/", "")
    if len(s) != 8 or not s.isdigit():
        raise ValueError(f"Invalid expiry '{expiry}' — must be YYYY-MM-DD or YYYYMMDD")
    return s


def _normalize_right(right: str) -> str:
    r = right.strip().upper()
    if r in ("C", "CALL"):
        return "C"
    if r in ("P", "PUT"):
        return "P"
    raise ValueError(f"Invalid right '{right}' — must be C or P")


def _normalize_action(action: str) -> str:
    a = action.strip().upper()
    if a not in ("BUY", "SELL"):
        raise ValueError(f"Invalid action '{action}' — must be BUY or SELL")
    return a


def _contract_dict(c: Contract) -> dict[str, Any]:
    """Serialize an IBKR contract to a JSON-friendly dict."""
    base: dict[str, Any] = {
        "secType": c.secType,
        "symbol": c.symbol,
        "exchange": c.exchange,
        "currency": c.currency,
        "conId": getattr(c, "conId", 0),
    }
    for attr in (
        "primaryExchange",
        "lastTradeDateOrContractMonth",
        "strike",
        "right",
        "multiplier",
        "tradingClass",
        "localSymbol",
    ):
        v = getattr(c, attr, None)
        if v:
            base[attr] = v
    if isinstance(c, Bag):
        base["comboLegs"] = [
            {
                "conId": leg.conId,
                "ratio": leg.ratio,
                "action": leg.action,
                "exchange": leg.exchange,
            }
            for leg in (c.comboLegs or [])
        ]
    return base


def _resolve_outside_rth(args) -> tuple[bool, str]:
    """Decide whether to set order.outsideRth based on CLI flags.

    Returns (outside_rth_bool, reason_str). The reason is appended to checks.notes
    so the user can see exactly why their order was tagged a certain way.

    Flag precedence (mutually exclusive in argparse):
      --outside-rth       → always True (explicit override)
      --rth-only          → always False (explicit override)
      --auto-rth (default) → True iff current time is outside US/Eastern RTH (09:30–16:00 Mon–Fri)
    """
    if getattr(args, "outside_rth", False):
        return True, "outsideRth=True (explicit --outside-rth)"
    if getattr(args, "rth_only", False):
        return False, "outsideRth=False (explicit --rth-only)"

    # Auto mode: check if NOW is outside US/Eastern regular trading hours.
    try:
        from zoneinfo import ZoneInfo
        et_now = datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        # Fallback: assume RTH (safer default — no extended-hours fills)
        return False, "outsideRth=False (auto, tz unavailable)"

    is_weekday = et_now.weekday() < 5
    in_rth = is_weekday and (
        (et_now.hour, et_now.minute) >= (9, 30)
        and (et_now.hour, et_now.minute) < (16, 0)
    )
    # NOTE: early-close days (Black Friday, Christmas Eve, day before July 4)
    # close at 13:00 ET. We do NOT hardcode the NYSE calendar — on those
    # afternoons (~3 days/year) `auto` may incorrectly return RTH. Use
    # `--outside-rth` explicitly if a same-day order isn't filling.
    if in_rth:
        return False, f"outsideRth=False (auto, RTH: ET {et_now:%H:%M})"
    else:
        return True, f"outsideRth=True (auto, extended-hours: ET {et_now:%H:%M %a})"


def _order_payload(
    *,
    symbol: str,
    sec_type: str,
    action: Optional[str],
    quantity: float,
    order_type: str,
    limit_price: Optional[float],
    stop_price: Optional[float],
    tif: str,
    outside_rth: bool = False,
) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "sec_type": sec_type,
        "action": action,
        "quantity": quantity,
        "order_type": order_type,
        "limit_price": limit_price,
        "stop_price": stop_price,
        "tif": tif,
        "outside_rth": outside_rth,
    }


def _build_order(
    *,
    action: str,
    quantity: float,
    order_type: str,
    limit_price: Optional[float],
    stop_price: Optional[float],
    tif: str,
    outside_rth: bool = False,
) -> Order:
    """Build an ib_async Order object from CLI args."""
    ot = order_type.upper()
    if ot == "MKT":
        o = MarketOrder(action, quantity)
    elif ot == "LMT":
        if limit_price is None:
            raise ValueError("--limit-price is required when --order-type=LMT")
        o = LimitOrder(action, quantity, limit_price)
    elif ot == "STP":
        if stop_price is None:
            raise ValueError("--stop-price is required when --order-type=STP")
        o = StopOrder(action, quantity, stop_price)
    else:
        raise ValueError(f"Unknown --order-type '{order_type}' (use MKT|LMT|STP)")
    o.tif = tif.upper()
    if outside_rth:
        o.outsideRth = True
    return o


# ─────────────────────────────────────────────────────────────
# Gates & pre-flight checks
# ─────────────────────────────────────────────────────────────


@dataclass
class Checks:
    trading_env_enabled: bool = False
    confirm_flag_passed: bool = False
    gateway_readonly_off: Optional[bool] = None  # None = unknown until probed
    buying_power_ok: Optional[bool] = None
    notional_ok: bool = True
    quantity_ok: bool = True
    blocklist_ok: bool = True
    notes: list[str] = field(default_factory=list)

    def gates_pass(self) -> bool:
        """The two safety gates. Both must be True for a live order."""
        return self.trading_env_enabled and self.confirm_flag_passed


def _check_env_gate() -> bool:
    return os.getenv(ENV_ENABLED, "") == "1"


def _check_blocklist(symbol: str) -> bool:
    raw = os.getenv(ENV_BLOCKLIST, "")
    if not raw.strip():
        return True
    blocked = {s.strip().upper() for s in raw.split(",") if s.strip()}
    return symbol.upper() not in blocked


def _check_gateway_readonly(ib) -> tuple[bool, str]:
    """
    Probe whether Gateway's "Read-Only API" is ON by calling reqAccountSummary —
    if it's on, IBKR sends Error 2105 / reqMktData errors during a placeOrder.
    We can't directly query the flag, but we can connect with readonly=False and
    fetch account summary. If summary fails or returns 0 rows, surface a warning.
    """
    try:
        summary = ib.accountSummary()
        if not summary:
            return False, "accountSummary() returned empty — Gateway may be in read-only mode"
        return True, "accountSummary OK"
    except Exception as e:
        return False, f"accountSummary failed: {type(e).__name__}: {e}"


def _check_buying_power(ib, notional: float) -> tuple[bool, float, str]:
    """Return (ok, buying_power, currency). ok=True if notional <= buying_power."""
    try:
        summary = ib.accountSummary()
    except Exception as e:
        return False, 0.0, f"accountSummary failed: {e}"

    bp = 0.0
    currency = "USD"
    for row in summary:
        if row.tag == "BuyingPower":
            try:
                bp = float(row.value)
                currency = row.currency or "USD"
            except (ValueError, TypeError):
                pass
            break
    if bp <= 0:
        return False, bp, "BuyingPower not available (paper account or empty)"
    return notional <= bp, bp, currency


def _estimate_notional(
    *,
    sec_type: str,
    quantity: float,
    limit_price: Optional[float],
    market_price_hint: Optional[float] = None,
    multiplier: int = 1,
) -> Optional[float]:
    """Best-effort notional estimate. Returns None if we can't price (e.g. MKT order with no hint)."""
    price = limit_price if limit_price is not None else market_price_hint
    if price is None:
        return None
    return abs(quantity) * abs(price) * multiplier


# ─────────────────────────────────────────────────────────────
# Order placement / waiting
# ─────────────────────────────────────────────────────────────


def _place_and_wait(ib, contract: Contract, order: Order) -> dict[str, Any]:
    """Place an order and wait briefly for an initial status update."""
    trade = ib.placeOrder(contract, order)
    deadline = time.monotonic() + ORDER_STATUS_TIMEOUT_SEC
    while time.monotonic() < deadline:
        ib.sleep(0.25)
        st = trade.orderStatus.status
        # Terminal-ish states we can return immediately on
        if st in ("Filled", "Cancelled", "ApiCancelled", "Inactive", "PreSubmitted", "Submitted"):
            break
    return {
        "order_id": trade.order.orderId,
        "perm_id": getattr(trade.order, "permId", 0),
        "status": trade.orderStatus.status,
        "filled_qty": float(trade.orderStatus.filled or 0),
        "remaining_qty": float(trade.orderStatus.remaining or 0),
        "avg_fill_price": float(trade.orderStatus.avgFillPrice or 0),
        "log": [
            {"time": str(e.time), "status": e.status, "message": e.message}
            for e in trade.log[-5:]
        ],
    }


# ─────────────────────────────────────────────────────────────
# Subcommand implementations
# ─────────────────────────────────────────────────────────────


def cmd_stock(args, ib, checks: Checks) -> dict[str, Any]:
    action = _normalize_action(args.action)
    qty = args.quantity

    contract = us_stock(args.symbol)
    ib.qualifyContracts(contract)

    checks.quantity_ok = qty <= MAX_STOCK_QTY or args.allow_large
    if not checks.quantity_ok:
        checks.notes.append(
            f"Quantity {qty} > {MAX_STOCK_QTY} shares — pass --allow-large to override"
        )

    checks.blocklist_ok = _check_blocklist(args.symbol)
    if not checks.blocklist_ok:
        checks.notes.append(f"Symbol {args.symbol} is in {ENV_BLOCKLIST}")

    notional = _estimate_notional(
        sec_type="STK", quantity=qty, limit_price=args.limit_price
    )
    if notional is not None:
        checks.notional_ok = notional <= MAX_NOTIONAL_USD or args.allow_large
        if not checks.notional_ok:
            checks.notes.append(
                f"Notional ~${notional:,.0f} > ${MAX_NOTIONAL_USD:,} — pass --allow-large to override"
            )

    outside_rth, rth_reason = _resolve_outside_rth(args)
    checks.notes.append(rth_reason)

    order = _build_order(
        action=action,
        quantity=qty,
        order_type=args.order_type,
        limit_price=args.limit_price,
        stop_price=args.stop_price,
        tif=args.tif,
        outside_rth=outside_rth,
    )

    payload = _order_payload(
        symbol=args.symbol,
        sec_type="STK",
        action=action,
        quantity=qty,
        order_type=args.order_type.upper(),
        limit_price=args.limit_price,
        stop_price=args.stop_price,
        tif=args.tif.upper(),
        outside_rth=outside_rth,
    )

    if args.order_type.upper() != "STP":
        checks.notes.append(
            "WARNING: no stop-loss set on this order — consider --order-type STP follow-up"
        )

    return _finalize(args, ib, contract, order, payload, checks, notional)


def cmd_option(args, ib, checks: Checks) -> dict[str, Any]:
    action = _normalize_action(args.action)
    qty = args.quantity
    expiry = _normalize_expiry(args.expiry)
    right = _normalize_right(args.right)
    strike = float(args.strike)

    contract = Option(args.symbol.upper(), expiry, strike, right, "SMART", currency="USD")
    contract.multiplier = "100"
    ib.qualifyContracts(contract)

    checks.quantity_ok = qty <= MAX_OPTION_QTY or args.allow_large
    if not checks.quantity_ok:
        checks.notes.append(
            f"Quantity {qty} > {MAX_OPTION_QTY} contracts — pass --allow-large to override"
        )

    checks.blocklist_ok = _check_blocklist(args.symbol)
    if not checks.blocklist_ok:
        checks.notes.append(f"Symbol {args.symbol} is in {ENV_BLOCKLIST}")

    # Options multiplier = 100
    notional = _estimate_notional(
        sec_type="OPT", quantity=qty, limit_price=args.limit_price, multiplier=100
    )
    if notional is not None:
        checks.notional_ok = notional <= MAX_NOTIONAL_USD or args.allow_large
        if not checks.notional_ok:
            checks.notes.append(
                f"Notional ~${notional:,.0f} > ${MAX_NOTIONAL_USD:,} — pass --allow-large to override"
            )

    outside_rth, rth_reason = _resolve_outside_rth(args)
    checks.notes.append(rth_reason)

    order = _build_order(
        action=action,
        quantity=qty,
        order_type=args.order_type,
        limit_price=args.limit_price,
        stop_price=None,
        tif=args.tif,
        outside_rth=outside_rth,
    )

    payload = _order_payload(
        symbol=f"{args.symbol} {expiry} {strike} {right}",
        sec_type="OPT",
        action=action,
        quantity=qty,
        order_type=args.order_type.upper(),
        limit_price=args.limit_price,
        stop_price=None,
        tif=args.tif.upper(),
        outside_rth=outside_rth,
    )

    return _finalize(args, ib, contract, order, payload, checks, notional)


def cmd_combo(args, ib, checks: Checks) -> dict[str, Any]:
    if len(args.leg) < 2:
        raise ValueError("--leg must be provided at least twice for a combo")

    # Parse legs: "SYMBOL EXPIRY STRIKE RIGHT ACTION QTY"
    parsed_legs = []
    underlyings = set()
    for raw in args.leg:
        parts = raw.split()
        if len(parts) != 6:
            raise ValueError(
                f"Bad --leg '{raw}' — expected 'SYMBOL EXPIRY STRIKE RIGHT ACTION QTY'"
            )
        sym, expiry, strike, right, leg_action, leg_qty = parts
        parsed_legs.append({
            "symbol": sym.upper(),
            "expiry": _normalize_expiry(expiry),
            "strike": float(strike),
            "right": _normalize_right(right),
            "action": _normalize_action(leg_action),
            "qty": int(leg_qty),
        })
        underlyings.add(sym.upper())

    if len(underlyings) > 1:
        raise ValueError(
            f"All combo legs must share the same underlying — got {sorted(underlyings)}"
        )
    underlying = underlyings.pop()

    # Qualify each leg's option contract to get its conId
    combo_legs = []
    qualified_opts = []
    for leg in parsed_legs:
        opt = Option(
            underlying, leg["expiry"], leg["strike"], leg["right"], "SMART", currency="USD"
        )
        opt.multiplier = "100"
        ib.qualifyContracts(opt)
        if not opt.conId:
            raise RuntimeError(
                f"qualifyContracts failed for leg {leg} — contract not found"
            )
        qualified_opts.append(opt)
        cleg = ComboLeg()
        cleg.conId = opt.conId
        cleg.ratio = leg["qty"]
        cleg.action = leg["action"]
        cleg.exchange = "SMART"
        combo_legs.append(cleg)

    bag = Bag(symbol=underlying, exchange="SMART", currency="USD", comboLegs=combo_legs)

    # Total notional for combo = sum over legs (rough — uses limit_price as net premium)
    total_qty = sum(leg["qty"] for leg in parsed_legs)
    checks.quantity_ok = total_qty <= MAX_OPTION_QTY or args.allow_large
    if not checks.quantity_ok:
        checks.notes.append(
            f"Total leg quantity {total_qty} > {MAX_OPTION_QTY} — pass --allow-large to override"
        )

    checks.blocklist_ok = _check_blocklist(underlying)
    if not checks.blocklist_ok:
        checks.notes.append(f"Symbol {underlying} is in {ENV_BLOCKLIST}")

    # For combos, BUY = pay debit, SELL = collect credit. We model as a BUY of the bag
    # at net premium = limit_price. Sign of limit_price ⇒ debit (positive) or credit (negative).
    # ib_async convention: place order on bag with positive total qty=1 (the spread "unit").
    # Each leg's own action+ratio in ComboLeg handles direction.
    spread_action = "BUY"  # The bag itself is bought; leg actions specify direction inside
    spread_qty = 1  # Number of spread units; combine via leg ratios

    notional = None
    if args.limit_price is not None:
        # Net premium × 100 multiplier × spread units
        notional = abs(args.limit_price) * 100 * spread_qty
        checks.notional_ok = notional <= MAX_NOTIONAL_USD or args.allow_large
        if not checks.notional_ok:
            checks.notes.append(
                f"Notional ~${notional:,.0f} > ${MAX_NOTIONAL_USD:,} — pass --allow-large to override"
            )

    outside_rth, rth_reason = _resolve_outside_rth(args)
    checks.notes.append(rth_reason)

    order = _build_order(
        action=spread_action,
        quantity=spread_qty,
        order_type=args.order_type,
        limit_price=args.limit_price,
        stop_price=None,
        tif=args.tif,
        outside_rth=outside_rth,
    )

    payload = _order_payload(
        symbol=f"{underlying} COMBO ({len(parsed_legs)} legs)",
        sec_type="BAG",
        action=spread_action,
        quantity=spread_qty,
        order_type=args.order_type.upper(),
        limit_price=args.limit_price,
        stop_price=None,
        tif=args.tif.upper(),
        outside_rth=outside_rth,
    )
    payload["legs"] = parsed_legs

    return _finalize(args, ib, bag, order, payload, checks, notional)


def cmd_future(args, ib, checks: Checks) -> dict[str, Any]:
    action = _normalize_action(args.action)
    qty = args.quantity

    if args.last_trade_month:
        # Specific contract month — try to look up via FUTURES table for exchange/symbol
        try:
            from contracts import FUTURES
            if args.symbol.upper() in FUTURES:
                ibkr_sym, exchange, _ = FUTURES[args.symbol.upper()]
                contract = Future(ibkr_sym, args.last_trade_month, exchange, currency="USD")
            else:
                contract = Future(args.symbol.upper(), args.last_trade_month, "SMART")
        except ImportError:
            contract = Future(args.symbol.upper(), args.last_trade_month, "SMART")
    else:
        contract = resolve(args.symbol)
        if not isinstance(contract, (Future, ContFuture)):
            raise ValueError(
                f"Could not resolve {args.symbol} to a futures contract — "
                "try passing --last-trade-month YYYYMM explicitly"
            )

    ib.qualifyContracts(contract)

    checks.blocklist_ok = _check_blocklist(args.symbol)
    if not checks.blocklist_ok:
        checks.notes.append(f"Symbol {args.symbol} is in {ENV_BLOCKLIST}")

    # Futures notional is hard to estimate without contract spec; skip
    notional = None

    outside_rth, rth_reason = _resolve_outside_rth(args)
    checks.notes.append(rth_reason)

    order = _build_order(
        action=action,
        quantity=qty,
        order_type=args.order_type,
        limit_price=args.limit_price,
        stop_price=args.stop_price,
        tif=args.tif,
        outside_rth=outside_rth,
    )

    payload = _order_payload(
        symbol=args.symbol,
        sec_type="FUT",
        action=action,
        quantity=qty,
        order_type=args.order_type.upper(),
        limit_price=args.limit_price,
        stop_price=args.stop_price,
        tif=args.tif.upper(),
        outside_rth=outside_rth,
    )

    return _finalize(args, ib, contract, order, payload, checks, notional)


def cmd_forex(args, ib, checks: Checks) -> dict[str, Any]:
    action = _normalize_action(args.action)
    qty = args.quantity

    pair = args.symbol.upper().replace("/", "").replace("-", "")
    if len(pair) != 6 or not pair.isalpha():
        raise ValueError(f"Bad FX pair '{args.symbol}' — expected 6 letters (e.g. EURUSD)")

    contract = Forex(pair)
    ib.qualifyContracts(contract)

    checks.blocklist_ok = _check_blocklist(pair)
    if not checks.blocklist_ok:
        checks.notes.append(f"Pair {pair} is in {ENV_BLOCKLIST}")

    notional = _estimate_notional(
        sec_type="CASH", quantity=qty, limit_price=args.limit_price
    )
    if notional is not None:
        checks.notional_ok = notional <= MAX_NOTIONAL_USD or args.allow_large
        if not checks.notional_ok:
            checks.notes.append(
                f"Notional ~${notional:,.0f} > ${MAX_NOTIONAL_USD:,} — pass --allow-large to override"
            )

    outside_rth, rth_reason = _resolve_outside_rth(args)
    checks.notes.append(rth_reason)

    order = _build_order(
        action=action,
        quantity=qty,
        order_type=args.order_type,
        limit_price=args.limit_price,
        stop_price=args.stop_price,
        tif=args.tif,
        outside_rth=outside_rth,
    )

    payload = _order_payload(
        symbol=pair,
        sec_type="CASH",
        action=action,
        quantity=qty,
        order_type=args.order_type.upper(),
        limit_price=args.limit_price,
        stop_price=args.stop_price,
        tif=args.tif.upper(),
        outside_rth=outside_rth,
    )

    return _finalize(args, ib, contract, order, payload, checks, notional)


def cmd_cancel(args, ib) -> dict[str, Any]:
    target_id = args.order_id
    open_trades = ib.openTrades()
    for tr in open_trades:
        if tr.order.orderId == target_id:
            ib.cancelOrder(tr.order)
            ib.sleep(1.0)
            return {
                "mode": "live",
                "action": "cancel",
                "order_id": target_id,
                "status_after_cancel": tr.orderStatus.status,
            }
    return {
        "mode": "live",
        "action": "cancel",
        "order_id": target_id,
        "error": f"Order ID {target_id} not found in open orders",
    }


def cmd_list_orders(args, ib) -> dict[str, Any]:
    trades = ib.openTrades()
    out = []
    for tr in trades:
        c = tr.contract
        out.append({
            "order_id": tr.order.orderId,
            "perm_id": getattr(tr.order, "permId", 0),
            "symbol": c.symbol,
            "sec_type": c.secType,
            "expiry": getattr(c, "lastTradeDateOrContractMonth", "") or None,
            "strike": getattr(c, "strike", 0) or None,
            "right": getattr(c, "right", "") or None,
            "action": tr.order.action,
            "order_type": tr.order.orderType,
            "quantity": float(tr.order.totalQuantity),
            "limit_price": getattr(tr.order, "lmtPrice", 0) or None,
            "stop_price": getattr(tr.order, "auxPrice", 0) or None,
            "tif": tr.order.tif,
            "status": tr.orderStatus.status,
            "filled": float(tr.orderStatus.filled or 0),
            "remaining": float(tr.orderStatus.remaining or 0),
        })
    return {"open_orders": out, "count": len(out)}


# ─────────────────────────────────────────────────────────────
# Finalize: dry-run vs live decision + JSON output assembly
# ─────────────────────────────────────────────────────────────


def _finalize(
    args,
    ib,
    contract: Contract,
    order: Order,
    order_payload: dict[str, Any],
    checks: Checks,
    notional: Optional[float],
) -> dict[str, Any]:
    """Last stop before placeOrder. Builds the result dict and gates the call."""
    # Pre-flight: gateway readonly probe
    ro_ok, ro_msg = _check_gateway_readonly(ib)
    checks.gateway_readonly_off = ro_ok
    if not ro_ok:
        checks.notes.append(
            f"Gateway readonly check: {ro_msg}. "
            "Make sure 'Read-Only API' is UNCHECKED in Gateway → Configure → Settings → API → Settings."
        )

    # Pre-flight: buying power
    if notional is not None:
        bp_ok, bp_val, bp_currency = _check_buying_power(ib, notional)
        checks.buying_power_ok = bp_ok
        checks.notes.append(
            f"BuyingPower={bp_val:,.2f} {bp_currency}, "
            f"estimated notional={notional:,.2f}, ok={bp_ok}"
        )
    else:
        # Can't estimate notional (MKT order with no hint or futures) — leave None
        checks.buying_power_ok = None
        checks.notes.append("Notional not estimable — skipping BuyingPower check")

    # Decide mode
    all_hard_ok = (
        checks.gates_pass()
        and checks.quantity_ok
        and checks.notional_ok
        and checks.blocklist_ok
        and (checks.gateway_readonly_off is True)
        and (checks.buying_power_ok in (True, None))
    )

    result: dict[str, Any]
    if not all_hard_ok:
        mode = "dry_run"
        result = "DRY_RUN_NO_ORDER_PLACED"
        if not checks.trading_env_enabled:
            checks.notes.append(
                f"Gate 1 not passed: set {ENV_ENABLED}=1 to allow live trading "
                "(see references/trading.md)"
            )
        if not checks.confirm_flag_passed:
            checks.notes.append("Gate 2 not passed: add --confirm-trade to place a live order")
    else:
        mode = "live"
        try:
            result = _place_and_wait(ib, contract, order)
        except Exception as e:
            mode = "error"
            result = {
                "error": f"{type(e).__name__}: {e}",
                "hint": "Common cause: Gateway 'Read-Only API' is ON. Disable it and restart Gateway.",
            }

    return {
        "mode": mode,
        "order": order_payload,
        "contract": _contract_dict(contract),
        "checks": {
            "trading_env_enabled": checks.trading_env_enabled,
            "confirm_flag_passed": checks.confirm_flag_passed,
            "gateway_readonly_off": checks.gateway_readonly_off,
            "buying_power_ok": checks.buying_power_ok,
            "notional_ok": checks.notional_ok,
            "quantity_ok": checks.quantity_ok,
            "blocklist_ok": checks.blocklist_ok,
            "notes": checks.notes,
        },
        "result": result,
    }


# ─────────────────────────────────────────────────────────────
# Argparse setup
# ─────────────────────────────────────────────────────────────


def _add_common_order_flags(p: argparse.ArgumentParser, *, default_action: str = "BUY"):
    p.add_argument("--action", default=default_action, choices=["BUY", "SELL", "buy", "sell"])
    p.add_argument("--order-type", default="MKT", choices=["MKT", "LMT", "STP", "mkt", "lmt", "stp"])
    p.add_argument("--limit-price", type=float, default=None)
    p.add_argument("--stop-price", type=float, default=None)
    p.add_argument("--tif", default="DAY", choices=["DAY", "GTC", "day", "gtc"])
    rth = p.add_mutually_exclusive_group()
    rth.add_argument(
        "--outside-rth",
        action="store_true",
        help="Allow fills outside Regular Trading Hours (pre/post-market, overnight). "
             "Overrides --auto-rth detection.",
    )
    rth.add_argument(
        "--rth-only",
        action="store_true",
        help="Restrict to Regular Trading Hours (09:30–16:00 ET) even if placed off-hours. "
             "Overrides --auto-rth.",
    )
    p.add_argument(
        "--allow-large",
        action="store_true",
        help="Override notional/quantity guardrails (use with caution)",
    )
    p.add_argument(
        "--confirm-trade",
        action="store_true",
        help="REQUIRED to actually send the order (Gate 2). Without this flag, dry-run only.",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="trade.py",
        description="IBKR trading execution — see references/trading.md before use.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # stock
    sp = sub.add_parser("stock", help="Place a stock/ETF order")
    sp.add_argument("symbol")
    sp.add_argument("quantity", type=float)
    _add_common_order_flags(sp)

    # option
    op = sub.add_parser("option", help="Place a single-leg option order")
    op.add_argument("symbol")
    op.add_argument("expiry", help="YYYY-MM-DD or YYYYMMDD")
    op.add_argument("strike", type=float)
    op.add_argument("right", help="C or P")
    op.add_argument("quantity", type=float)
    _add_common_order_flags(op)

    # combo
    cp = sub.add_parser("combo", help="Place a multi-leg option spread (BAG)")
    cp.add_argument(
        "--leg",
        action="append",
        required=True,
        help='Quoted: "SYMBOL EXPIRY STRIKE RIGHT ACTION QTY"  (repeat per leg)',
    )
    cp.add_argument("--order-type", default="LMT", choices=["MKT", "LMT", "mkt", "lmt"])
    cp.add_argument("--limit-price", type=float, default=None,
                    help="Net debit (positive) or credit (negative) per spread unit")
    cp.add_argument("--tif", default="DAY", choices=["DAY", "GTC", "day", "gtc"])
    cp_rth = cp.add_mutually_exclusive_group()
    cp_rth.add_argument("--outside-rth", action="store_true",
                        help="Allow fills outside RTH (pre/post-market).")
    cp_rth.add_argument("--rth-only", action="store_true",
                        help="Restrict to RTH only.")
    cp.add_argument("--allow-large", action="store_true")
    cp.add_argument("--confirm-trade", action="store_true")

    # future
    fp = sub.add_parser("future", help="Place a futures order")
    fp.add_argument("symbol", help="Symbol key (e.g. ES, NQ, CL) or full symbol")
    fp.add_argument("quantity", type=float)
    fp.add_argument("--last-trade-month", default=None,
                    help="YYYYMM expiry (otherwise uses continuous front-month resolver)")
    _add_common_order_flags(fp)

    # forex
    fxp = sub.add_parser("forex", help="Place an FX order")
    fxp.add_argument("symbol", help="6-letter pair, e.g. EURUSD")
    fxp.add_argument("quantity", type=float)
    _add_common_order_flags(fxp)

    # cancel
    canp = sub.add_parser("cancel", help="Cancel an open order by ID")
    canp.add_argument("order_id", type=int)

    # list-orders
    sub.add_parser("list-orders", help="List all open orders (JSON)")

    return p


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    env_enabled = _check_env_gate()
    # cancel and list-orders don't need gates (cancelling/reading is intrinsically safe)
    is_readonly_cmd = args.cmd in ("cancel", "list-orders")
    confirm_flag = getattr(args, "confirm_trade", False)

    if not is_readonly_cmd and not env_enabled and not confirm_flag:
        # Pure dry-run with no connection cost — still surface the result schema
        log(
            f"ℹ️  {ENV_ENABLED} is not set AND --confirm-trade is not passed. "
            "Running in dry-run mode (no IBKR connection).\n"
            "    See references/trading.md to enable trading."
        )

    try:
        with ib_connect(
            client_id_offset=CLIENT_ID_OFFSET,
            readonly=False,
            verbose=True,
        ) as ib:
            checks = Checks(
                trading_env_enabled=env_enabled,
                confirm_flag_passed=confirm_flag,
            )

            if args.cmd == "stock":
                result = cmd_stock(args, ib, checks)
            elif args.cmd == "option":
                result = cmd_option(args, ib, checks)
            elif args.cmd == "combo":
                result = cmd_combo(args, ib, checks)
            elif args.cmd == "future":
                result = cmd_future(args, ib, checks)
            elif args.cmd == "forex":
                result = cmd_forex(args, ib, checks)
            elif args.cmd == "cancel":
                result = cmd_cancel(args, ib)
            elif args.cmd == "list-orders":
                result = cmd_list_orders(args, ib)
            else:
                raise ValueError(f"Unknown command: {args.cmd}")
    except Exception as e:
        result = {
            "mode": "error",
            "error": f"{type(e).__name__}: {e}",
        }

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get("mode") != "error" else 1


if __name__ == "__main__":
    sys.exit(main())
