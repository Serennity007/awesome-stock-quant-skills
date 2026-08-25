# Troubleshooting

A reference for every error this toolkit can throw at you. Issues are grouped by category. If you hit something not listed here, please open an issue with the full stderr log.

## Table of Contents

- [Connection errors](#connection-errors)
- [Contract / market-data errors](#contract--market-data-errors)
- [Greeks and IV problems](#greeks-and-iv-problems)
- [Read-only mode (intentional)](#read-only-mode-intentional)
- [Performance & pacing](#performance--pacing)
- [Getting Gateway logs](#getting-gateway-logs)
- [IBKR-side configuration checklist](#ibkr-side-configuration-checklist)

---

## Connection errors

### `ConnectionRefusedError` / "Connection refused"

The script can't reach IB Gateway at all.

**Diagnostic order:**

1. **Is Gateway running?** Check the dock / system tray. A logged-out Gateway is **not** accepting connections — re-login.
2. **Is the port right?**
   - Gateway live: `4001`
   - Gateway paper: `4002`
   - TWS live: `7496`
   - TWS paper: `7497`
3. **Is the API enabled?** `Configure → Settings → API → Settings → Enable ActiveX and Socket Clients` must be checked.
4. **Is `127.0.0.1` in Trusted IPs?** Same panel. Add it explicitly.
5. **Did you restart Gateway after enabling the API?** API settings do not apply live — Gateway must be restarted.

Quick sanity check (Mac / Linux):

```bash
nc -zv 127.0.0.1 4001
```

If `nc` fails: the problem is Gateway, not this toolkit.

### `TimeoutError` after a long pause

Gateway is alive but not responding within `CONNECT_TIMEOUT` (10s). Causes:

- Gateway is mid-restart or mid-login (banner showing 2FA challenge).
- A previous client with the same clientId is hanging — wait 30 seconds for the server to time it out, or restart Gateway.
- Firewall (Little Snitch on Mac, Windows Defender) is blocking the socket.

### `clientId X already in use`

Two connections collided on the same clientId. Possible causes:

- You re-ran a script faster than the previous run could disconnect.
- Two scripts somehow ended up with the same offset (shouldn't happen — check that no one edited `CLIENT_ID_OFFSET` constants).
- Another application (your TWS workstation, a third-party bot) is using that clientId.

**Fix:** raise `IBKR_CLIENT_ID_BASE` in `.env` to a value that doesn't collide:

```ini
IBKR_CLIENT_ID_BASE=51
```

This shifts all script clientIds (51+7 through 51+16). Confirm no other app uses anything in that range.

---

## Contract / market-data errors

### `Error 200: No security definition has been found for the request`

The contract didn't resolve. The error from IBKR's API is unhelpful — here's how to debug.

**Causes ranked by frequency:**

1. **Typo in the symbol.** `BRK.B` should be `BRK B` (space, not dot) in some routes.
2. **Wrong asset class.** Trying to fetch an option on a ticker that doesn't have listed options.
3. **Expired option.** The expiration date is in the past.
4. **Non-standard strike.** The strike doesn't exist on that expiration — chains sometimes have $0.50 strikes near ATM but $1.00 strikes farther out.
5. **Wrong exchange.** Some tickers must be routed to a specific exchange instead of `SMART`:
   - European stocks → `--exchange LSEETF` (London) or similar
   - Some Chinese ADRs at certain times
   - Cash-settled indexes → `--exchange CBOE`
6. **Future / option on future** missing `multiplier`. CME futures options need `multiplier=50` etc.

**Debug command:**

```bash
python scripts/market_quote.py SYM       # if even the underlying fails, problem is symbol/exchange
python scripts/options_chain.py SYM      # if underlying works but chain fails, problem is expiration/strike
```

### `Error 10091: Requested market data requires additional subscription`

Self-explanatory: your IBKR account doesn't have a subscription for the exchange / data type you're requesting.

**Two fixes:**

1. **Switch to delayed data** (free, ~15 min lag). Edit `.env`:

   ```ini
   IBKR_MARKET_DATA_TYPE=3
   ```

   Restart the script. Quotes will be delayed but free.

2. **Subscribe.** Account Management → Settings → User Settings → Market Data Subscriptions. Common subscriptions:
   - **US Securities Snapshot and Futures Value Bundle** — $10/mo, real-time US stocks/ETFs.
   - **OPRA (US Option Exchanges)** — $1.50/mo (no professional), needed for option Greeks live.
   - **NASDAQ Last Sale (NLS)** — covers many Nasdaq tickers.

### `Error 354: Requested market data is not subscribed`

Variant of 10091 — same fix.

### `Error 162: Historical market data Service error message`

`reqHistoricalData` failed. Causes:

- **Pacing violation:** "more than 6 same-contract historical requests in 2 seconds". The toolkit's `req_historical_safe()` enforces a 0.35s minimum interval — but if you've also got TWS running and pulling the same data, you can exceed the cap. Wait a minute and retry.
- **Outside data range:** asking for 5-year history on a ticker that IPO'd 6 months ago.
- **Wrong `whatToShow`:** `MIDPOINT` works for FX, `TRADES` for stocks; mismatching gets you 162.

---

## Greeks and IV problems

### `modelGreeks is None`

The `options_chain.py` or `portfolio_positions.py` output shows `delta: null, iv: null, ...`.

**Why it happens:**

- The market is **closed** *and* you're using `IBKR_MARKET_DATA_TYPE=1` (realtime). Without a live tick, the server has no current Greeks to deliver. The same call during market hours returns Greeks correctly.
- Far-OTM strike with no trading activity — sometimes the server simply hasn't computed Greeks for an option no one's quoting.
- Wrong feed: deep OTM weeklies on illiquid names can lack Greeks even live.

**Fixes:**

1. Wait for the market to open (best signal quality).
2. Use **delayed-frozen** to serve the last cached delayed Greeks from the previous session:

   ```ini
   IBKR_MARKET_DATA_TYPE=4
   ```

3. Move to a more liquid strike or a more liquid expiry.

### IV looks wrong (zero, NaN, or jumping)

Stock and option ticks arrive asynchronously. Right when you connect, the chain returns an IV computed against a stale stock price. If you re-run the script 5 seconds later, IV will be sane.

`options_analyzer.py` waits ~3 seconds for ticks to settle before computing IV context. If you're calling `options_chain.py` directly, give it a moment.

---

## Read-only mode (intentional)

If you see in the stderr log:

```
🔄 Connecting to IB Gateway 127.0.0.1:4001 (clientId=18, readonly=True) ...
```

…**this is by design.** The toolkit always connects with `readonly=True` so it cannot place, modify, or cancel orders even if some downstream library tried. We additionally recommend enabling the Gateway-side **Read-Only API** setting for double safety:

- `Configure → Settings → API → Settings → Read-Only API` — **enable**.

This way, even if your `.env` got tampered with, Gateway would still refuse any order attempt.

> If you ever want to write a tool in this repo that places orders, you would need to (a) set `readonly=False` in `ib_connect()` and (b) disable Read-Only API in Gateway. The toolkit deliberately makes that hard.

---

## Performance & pacing

### Scripts feel slow

Typical baseline:

| Operation | Expected wall time |
|---|---|
| `market_quote.py SPY` | 2–4 sec (cold connect + 1 tick) |
| `options_chain.py SPY` (3 expirations) | 8–20 sec |
| `portfolio_positions.py` (20 positions) | 6–12 sec |
| `options_analyzer.py SPY --iv-context` | 10–25 sec |

If you see > 60 sec, suspect:

- Pacing throttle (too many historical requests recently).
- A laggy connection (geographic distance from IBKR data center).
- Subscription mismatch causing fallbacks.

### `Pacing violation` warnings

The toolkit enforces a 0.35s minimum interval between historical-data calls (see `req_historical_safe` in `ib_client.py`). If you still hit pacing limits, you're likely running another tool concurrently. Stop everything, wait 60 seconds, retry.

---

## Getting Gateway logs

When opening a bug report or a support ticket, Gateway logs make all the difference.

**Location:**

- macOS: `~/Jts/<gateway-version>/`, files named `api.<date>.log` and `ibgateway.<date>.log`
- Linux: `~/Jts/<gateway-version>/`
- Windows: `C:\Jts\<gateway-version>\`

**What to grep for:**

```bash
grep -E "ERROR|WARN|10091|^Error 200" ~/Jts/*/api.*.log | tail -50
```

The interesting errors are usually the last 50 lines.

**Enable verbose API logging** (helpful when contracts fail to resolve):

`Configure → Settings → API → Settings → Logging Level → Detail`. Restart Gateway.

---

## IBKR-side configuration checklist

If something feels broken in a way none of the above explains, walk this list:

- [ ] Gateway is logged in (not paused at a 2FA / "agreement updated" screen).
- [ ] `Configure → Settings → API → Settings → Enable ActiveX and Socket Clients` ✅
- [ ] `Configure → Settings → API → Settings → Read-Only API` ✅ (matches our convention)
- [ ] `Configure → Settings → API → Settings → Socket port` = value in your `.env`
- [ ] `Configure → Settings → API → Settings → Trusted IPs` includes `127.0.0.1`
- [ ] **Restart Gateway** after changing any API setting (settings are not live-applied).
- [ ] Account Management → Market Data Subscriptions includes the exchanges you query.
- [ ] No other client (a second Python script, an old TWS instance, another bot) is using a clientId in the toolkit's range (`base+7` … `base+16`).

If everything on this list is green and the toolkit still fails: open an issue with the failing command, the stderr output, and a redacted Gateway log line. Most repeat issues come back to one of the items above.
