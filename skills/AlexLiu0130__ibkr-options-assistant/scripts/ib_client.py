"""
IB Gateway shared connection manager.

All scripts use `ib_connect(client_id_offset)` instead of `IB().connect()` to ensure:
  1. Read-only double safety (readonly=True + Gateway "Read-Only API")
  2. Unique clientId per script (avoid Gateway conflicts)
  3. Configurable host/port/market data type via environment variables
  4. Auto-disconnect on exception

Environment variables (all optional, see .env.example):
  IBKR_HOST              default 127.0.0.1
  IBKR_PORT              default 4001 (IB Gateway live; 7497 for TWS paper)
  IBKR_CLIENT_ID_BASE    default 11; each script adds an offset
  IBKR_MARKET_DATA_TYPE  default 1 (realtime); 3 = delayed (free)

ClientId offsets (script-to-offset mapping):
  market_quote.py        offset 7   → client_id = base + 7
  options_chain.py       offset 8
  portfolio_positions.py offset 9
  options_analyzer.py    offset 10
  options_daily.py       offset 11
  pnl_analytics.py       offset 12
  risk_simulator.py      offset 13
  technical_indicators   offset 14
  wheel_tracker.py       offset 15
  alerts_monitor.py      offset 16
  cost_basis.py          offset 17
  concentration.py       offset 18
  trade.py               offset 19
  status_dashboard.py    offset 20
  (flex_import.py has no IBKR connection)
"""

import os
import sys
import time
from contextlib import contextmanager

from ib_async import IB

HOST = os.getenv("IBKR_HOST", "127.0.0.1")
PORT = int(os.getenv("IBKR_PORT", "4001"))
DEFAULT_MARKET_DATA_TYPE = int(os.getenv("IBKR_MARKET_DATA_TYPE", "3"))
CLIENT_ID_BASE = int(os.getenv("IBKR_CLIENT_ID_BASE", "11"))
CONNECT_TIMEOUT = 10

# Pacing: same contract + same tick type, ≤6 requests per 2s → min interval 0.35s
HIST_MIN_INTERVAL_SEC = 0.35


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


@contextmanager
def ib_connect(
    client_id_offset: int,
    *,
    market_data_type: int = None,
    readonly: bool = True,
    verbose: bool = True,
):
    """Connect to IB Gateway with configurable client_id offset.

    Usage:
        with ib_connect(client_id_offset=7) as ib:
            bars = ib.reqHistoricalData(...)

    Client ID = CLIENT_ID_BASE + client_id_offset (configurable via env var).
    """
    if market_data_type is None:
        market_data_type = DEFAULT_MARKET_DATA_TYPE
    client_id = CLIENT_ID_BASE + client_id_offset

    ib = IB()
    try:
        if verbose:
            log(f"🔄 Connecting to IB Gateway {HOST}:{PORT} "
                f"(clientId={client_id}, readonly={readonly}) ...")
        ib.connect(HOST, PORT, clientId=client_id,
                   readonly=readonly, timeout=CONNECT_TIMEOUT)
        if verbose:
            log(f"✅ Connected (server v{ib.client.serverVersion()})")
        if market_data_type:
            ib.reqMarketDataType(market_data_type)
            if verbose:
                log(f"   marketDataType={market_data_type} "
                    f"(1=realtime, 3=delayed, 4=delayed-frozen)")
        yield ib
    finally:
        if ib.isConnected():
            ib.disconnect()
            if verbose:
                log("👋 Disconnected")


_last_hist_call_ts: float = 0.0


def req_historical_safe(ib: IB, contract, **kwargs):
    """Pacing-aware wrapper around ib.reqHistoricalData.

    kwargs are passed through to ib.reqHistoricalData (endDateTime, durationStr,
    barSizeSetting, whatToShow, useRTH, formatDate, etc.).
    """
    global _last_hist_call_ts
    elapsed = time.monotonic() - _last_hist_call_ts
    if elapsed < HIST_MIN_INTERVAL_SEC:
        time.sleep(HIST_MIN_INTERVAL_SEC - elapsed)
    _last_hist_call_ts = time.monotonic()
    return ib.reqHistoricalData(contract, **kwargs)


def qualify(ib: IB, contract):
    """Thin wrapper around qualifyContracts with a clear error on failure."""
    qualified = ib.qualifyContracts(contract)
    if not qualified:
        raise RuntimeError(
            f"qualifyContracts failed: {getattr(contract, 'symbol', contract)} "
            f"(secType={getattr(contract, 'secType', '?')}, "
            f"exchange={getattr(contract, 'exchange', '?')})"
        )
    return qualified[0]
