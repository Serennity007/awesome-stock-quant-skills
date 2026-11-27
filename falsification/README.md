[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

# Trading-model falsification journal

This directory does one thing: it turns claims that are treated as correct trading models into testable propositions, then tries to refute them with reproducible computations. When a claim survives, the record says "insufficient evidence" instead of leaving unverified statements as default truth.

It covers two kinds of claims:

- models implicit in this repository's own tools and methods (pricing conventions, annualization conventions, backtest assumptions, consensus-voting assumptions, ...);
- widely repeated trading rules of thumb that were never tested ("high win rate means steady profit", "annualized roll yield is the return you can collect", "a near-zero put-call parity residual means no arbitrage", ...).

> Scope: this is a research record, not a trading signal, and not investment advice. Every conclusion holds only for the stated inputs, parameters and conventions.

## What is here (as of 2026-11-28)

Nine claims across five round files (rounds 1, 3, 4, 5, 6): **8 REFUTED, 1 AMBIGUOUS**, none OPEN or BLOCKED. The full definition, computation and boundary of each claim live in its round file; `claims.md` is only the index.

### Round index

| Round | File | Claim | Verdict |
|---|---|---|---|
| 1 | [2026-11-27.md](rounds/2026-11-27.md) | F-001 High-win-rate option selling ≠ positive expectancy | `REFUTED` |
| 2 (blocked for lack of data, no file) | — | F-002 Volatility risk premium | completed in round 6 |
| 3 | [2026-11-27-round3.md](rounds/2026-11-27-round3.md) | F-003 Annualized curve slope ≠ realisable roll return | `REFUTED` |
| 4 | [2026-11-27-round4.md](rounds/2026-11-27-round4.md) | F-008 RSI<30 and the 5-day positive-return probability | `AMBIGUOUS` |
| 5 | [2026-11-27-round5.md](rounds/2026-11-27-round5.md) | F-009 Arithmetic annualization ≠ compound annualization | `REFUTED` |
| 6 | [2026-11-27-round6.md](rounds/2026-11-27-round6.md) | F-002 Volatility risk premium (variance-swap proxy) | `REFUTED` |

When several rounds run on the same day, files are named `YYYY-MM-DD-roundN.md`; N follows execution order, not claim IDs. Round 2 was the first attempt at F-002; it was marked `BLOCKED` for missing IV/RV data and produced no file; round 6 completed it after the data was connected.

### Claims overview

| ID | Claim (short) | Status | Key result |
|---|---|---|---|
| F-001 | Selling deep OTM options is profitable because of the high win rate | `REFUTED` | Under fair Black-76 pricing, the six strikes with 21.6%–98.5% win rates all have zero discounted expectancy; with a 0.10-point cost all are −0.10 |
| F-002 | Selling options has positive expectancy when realised vol is below implied vol | `REFUTED` | 50ETF QVIX + 510050 (2015–2026), variance-swap proxy: ex-ante conditional mean −11.7 (95% CI [−85.7, +55.5]); −30.9 after a 0.5 vol-point cost. The ex-post version is an algebraic identity (100% positive) |
| F-003 | Curve slope = realisable annualized roll return | `REFUTED` | At the same 12.0614% snapshot, short roll gross returns on three slope paths are 6.46%/11.94%/17.46% (range 11.00 pp); costs take another 0.48–1.19 pp |
| F-004 | Consensus score = votes of independent frameworks | `REFUTED` | Documentation-level: frameworks share factors and data sources, so they are not statistically independent |
| F-005 | Current universe + 120-day lag backtest = point-in-time | `REFUTED` | Documentation-level: no real disclosure dates, restatements or delistings; survivorship/look-ahead bias remains |
| F-006 | A covered call's maximum loss is always finite | `REFUTED` | Documentation-level: with negative settlement prices (e.g. 2020 WTI) the left tail is unbounded |
| F-007 | Near-zero parity residual = no arbitrage | `REFUTED` | Documentation-level: it only says call/put quotes at the same expiry and strike are consistent; borrow, funding, fees and spreads are not modelled |
| F-008 | A 5-day positive return is significantly more likely than 50% after RSI<30 | `AMBIGUOUS` | 30 A-shares (2018–2026): 55.62% vs 49.80% base (+5.82 pp, block-bootstrap p=0.002); vs 50% p=0.0065, but 0.0585 after 9-way Holm, and the 95% lower bound is 0.4971 after 15 bp costs |
| F-009 | Arithmetic mean × 252 = realisable compound annual return | `REFUTED` | Counterexample +11%/−10%: arithmetic +126.0%, compound −11.84%; 30/30 A-shares overstated, median +4.08 pp |

## How each round is done

### Protocol

1. **Register first, compute second**: before running anything, write the claim, operational definition, decision rules, inputs and parameters at the top of `rounds/<date>.md`. Choosing the convention after seeing results is forbidden.
2. **Reproducible**: give the exact command, input files/parameters and Python version; use only standard-library code or tools already in the repository (round 6 uses pandas/AKShare from the repo `.venv`). Every number must be recomputable from the command.
3. **Cross-check**: verify key numbers with a second method (repository tool vs independent implementation, closed form vs numeric, two adjustment conventions, ...). Record any discrepancy.
4. **State the boundary**: describe the assumptions under which the claim holds or fails; label model-level and empirical results separately.
5. **One claim per round.**
6. **Update the registry**: after each round, update the status, round and evidence link in `claims.md`; if nothing changed, say so.
7. **Tool defects get an issue**: if refutation exposes a bug in a repository tool, do not fix it here; open an issue with a reproduction and file:line.

### How to read a round file

| Section | Content |
|---|---|
| Sections 1–3 | The pre-computation registration: operational definition, decision rules, inputs, full script |
| Section 4 | Full stdout of the script (sample sizes, cost columns, every parameter combination tried) |
| Section 5 | Cross-checks and implementation fixes (including wrong turns that were corrected) |
| Section 6 | Verdict + the pre-registered criteria checked one by one + an explicit "what this does not prove" |
| Section 7 | Boundaries and unproven parts |
| Section 8 | Follow-ups and the next candidate |

### Anti-cheating rules

- No future data; every lookback window has a stated start and cannot be adjusted afterwards.
- Any test involving costs must model them and report zero-cost and with-cost columns separately.
- When several parameters/windows/instruments were tried, report how many; never show only the best one.
- Record data sources and retrieval dates; label synthetic data explicitly.
- Never turn "test passed" into "strategy works"; `SUPPORTED` only means no counterexample was found.

## Data and reproduction

| Round | Data | Source / retrieval date | Dependencies |
|---|---|---|---|
| 1 | synthetic (Black-76 formula, no external data) | — | standard library |
| 3 | synthetic curve (12 contracts, deterministic) | — | standard library |
| 4 | 30 A-share back-adjusted daily bars, 2018–2026 | Eastmoney kline, 2026-11-27 | standard library |
| 5 | 30 A-share back-adjusted daily bars, 2018–2026 | Eastmoney kline, 2026-11-27 | standard library |
| 6 | 50ETF QVIX + 510050 back-adjusted daily bars, 2015–2026 | AKShare 1.18.94, 2026-11-27 | pandas + AKShare |

- Runtime: Python 3.11.9 (round 6 uses the repository `.venv`).
- **No raw market data is committed**: each round records source, retrieval date and convention; rounds 4/5 print the panel SHA-256, round 6 records the QVIX/ETF maturity and adjustment conventions.
- Reproduction commands are in section 3 of each round and can be pasted into a script; formula-only and synthetic parts need no network.
- Repository check: `python scripts/validate_repository.py`.

## Scope and boundaries

- **Model-level vs empirical**: F-001 (Black-76 counterexample), F-003 (synthetic curve) and F-009 (mathematical counterexample) are model-level refutations with a computation or formula; F-004–F-007 are documentation-level evidence (the repository docs already state the limits; they were not recomputed); F-002 (variance-swap proxy data) and F-008 (A-share sample) are empirical.
- **Costs**: every trading round reports zero-cost and with-cost results (F-001 0.10 point, F-002 0/0.5/1.0 vol-point, F-003 0/2/5 bp, F-008 0/15/30 bp).
- **Multiple comparisons**: F-008 tried 3 thresholds × 3 holding periods, reported all of them and applied a Holm correction; the best combination is never shown alone.
- **Proxy convention**: F-002 uses a variance swap to proxy "selling volatility"; it is not an option chain's realised expiry P&L, which would also bear hedging error, jumps and margin.
- **Synthetic data**: F-001/F-003 inputs are formulas or `synthetic` data, labelled as such; they are not market records.
- **No market conclusions**: `REFUTED` only means "the claim fails under the stated convention"; it does not mean the real market has no edge, and it is not trading advice.

## Status definitions

| Status | Meaning |
|---|---|
| `OPEN` | registered, not yet tested |
| `REFUTED` | refuted by a counterexample under the stated convention ("the claim does not hold") |
| `SUPPORTED` | passed the test under the stated convention ("no counterexample found", not universal truth) |
| `AMBIGUOUS` | the result depends on convention/data; no single conclusion, disagreements recorded |
| `BLOCKED` | missing data or permission; state what is missing and how to unblock |

## Directory layout

```
falsification/
├── README.md                    # this file: introduction, protocol, round index, data and scope
├── claims.md                    # claim registry (the only index)
└── rounds/
    ├── YYYY-MM-DD.md            # first round of the day
    └── YYYY-MM-DD-roundN.md     # Nth round of the same day (N follows execution order)
```

## Cadence

The DSH scheduled task "trading-model falsification round" runs every **Tuesday and Friday at 21:00 (Asia/Shanghai)**: each round registers and tests one `OPEN` claim, writes a round file and updates the registry. Manual runs are fine too. On 2026-11-27 rounds 1/3/4/5/6 were completed in one day (round 2 was F-002's blocked attempt, completed by round 6).

## Adding a claim

Append a row to `claims.md` with: ID, verbatim claim, source (which document or which popular saying), operational definition, test method and status. Do not rewrite earlier conclusions; to correct one, open a new round and label it "correction to round N". The operational definition must be expressible as reproducible code or a formula; otherwise leave the claim `OPEN`.

## Relation to the rest of the repository

- Tool behaviour contracts remain in each skill's `references/` and `tests/`; this directory only refutes claims.
- Division of labour with [docs/validation.md](../docs/validation.md): that file records "what was implemented and verified"; this directory records "which models/assumptions were refuted and which still do not hold".
- Entry points in the main READMEs: [English](../README.md) / [简体中文](../README.zh-CN.md) / [日本語](../README.ja.md).
