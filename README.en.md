[中文](README.md) · [English](README.en.md) · [日本語](README.ja.md)

![Stock Quant Skills](.github/quant-research.svg)

# AI Stock Screening & Quant Research Toolchain

`awesome-stock-quant-skills`

[![GitHub Stars](https://img.shields.io/github/stars/Serennity007/awesome-stock-quant-skills?style=flat-square&color=00d4ff)](https://github.com/Serennity007/awesome-stock-quant-skills/stargazers) [![GitHub Forks](https://img.shields.io/github/forks/Serennity007/awesome-stock-quant-skills?style=flat-square&color=8b5cf6)](https://github.com/Serennity007/awesome-stock-quant-skills/forks) [![Original code: MIT](https://img.shields.io/badge/original_code-MIT-22c55e?style=flat-square)](LICENSE)

Investment research implemented as Agent Skills and Python scripts: financial screening, factor ranking, multi-framework consensus and backtesting with transaction costs. Covers A-share research and US hot-stock tracking.

**30 original Skills · 23 investment-method reference frameworks · 32 Python scripts · 52 passing local tests.**

**41 Stars / 8 Forks** on GitHub as of 2026-10-24. Original implementations, third-party source snapshots and external links are maintained separately; 16 source directories contain 225 vendored `SKILL.md` files.

<!-- inventory: originals=30 mirrors=16 vendored=225 -->

**[One-command offline demo](docs/quickstart.md) · [Validation scope](docs/validation.md) · [Live-data record](examples/verification/2026-10-24/buffett-check.json)**

## First run: two offline examples

The default branch now contains all 30 original Skills and the data/backtest checks. After installing demo dependencies, one command runs two independent synthetic scenarios: consensus ranking and backtest arithmetic. It writes a readable report, CSVs, provenance and logs.

```bash
git clone https://github.com/Serennity007/awesome-stock-quant-skills.git
cd awesome-stock-quant-skills
python -m pip install -r requirements-demo.txt
python scripts/run_demo.py
```

Open the printed `output/demo/run-…/REPORT.md` path. Runs use fresh directories; missing dependencies produce an install hint, and failed calculations return a nonzero exit code with a failure record. **Inputs are synthetic and validate program behavior only.** [Full guide](docs/quickstart.md).

## Paper records and reviews

Freeze screening inputs with `scripts/paper_journal.py start`, then append dated buy-and-hold paper reviews with `review`. The saved [2026-10-25 market snapshot](reports/paper/2026-10-25/INITIAL_REVIEW.md) is pending execution: 14 complete and 6 partial records, with no invented prices or returns. The separately labeled [synthetic account](examples/paper/journal/reviews/2026-09-30.md) demonstrates round lots, costs, residual cash, benchmark comparisons and a loss. Historical fixture dates are not a live track record; these examples were created on 2026-10-25.

[Guide and commands](docs/paper-journal.md) · [Daily data-quality report](reports/latest.md). Existing daily automation saves independent pending snapshots; continuous reviews must keep using the same journal.

## Research tasks, concrete outputs

| Task | Implementation | Inspectable outputs |
|---|---|---|
| Financial quality and valuation | Buffett, Munger and Li Lu reference frameworks | Financial series, valuation percentiles and component deductions |
| Growth, momentum and themes | Lynch, Fisher, CANSLIM, theme scanning and concept mapping | Growth metrics, relative strength, sectors and candidates |
| Compare screening frameworks | Percentile normalization and consensus ranking | Consensus scores, coverage, input hashes and parameters |
| Examine historical behavior | Monthly rebalancing, drift-aware turnover and transaction costs | Gross/net returns, holdings, benchmark and data manifest |

## Engineering behind the research

Combine task routing, retrieval, scoring, consensus and historical checks around a research question. Run Python scripts directly or load individual Skills in an agent. CSV and JSON outputs preserve results for inspection and further analysis.

The tools check annual reporting periods, valuation dates, TTM fields, missing financials and consensus inputs, and record trading costs and holdings. The 23 methodology Skills are rule-based references to public investment methods.

## Hands-on validation

On 2026-10-24, **AKShare 1.19.3** retrieved real financial data and completed screening for **600519**, spanning **FY2021–2025**, with a **2026-10-23** valuation observation. **35 behavioral tests** cover missing financials, valuation dates, consensus validation, turnover and costs. Original JSON, CSV, scope and reproduction commands are public. This validates retrieval and calculation; investment performance requires separate evidence.

## What makes it useful

| Capability | Inspect the implementation |
|---|---|
| A research entry point that selects relevant skills and checks data dates | [quant-research-workflow](my-skills/quant-research-workflow/SKILL.md) |
| Financial screening with component-level reasoning | [Buffett rules](my-skills/buffett-value-investing/references/scoring_rules.md), [all originals](README.md#原创技能) |
| Percentile-based consensus with strict code, score, name and pool validation | [ensemble.py](my-skills/master-ensemble/scripts/ensemble.py) |
| Input SHA-256, parameters and timestamps alongside consensus results | [synthetic inputs](examples/ensemble), [behavior tests](tests/test_ensemble.py) |
| Exploratory monthly backtests with stated data limitations | [backtest methodology](my-skills/framework-backtest/references/backtest_methodology.md) |
| Ready-to-enable weekly upstream head/license/archive checks and AKShare version lookup | [maintenance](docs/maintenance.md), [workflow](docs/workflows/upstream-watch.yml) |

Counts describe files and source directories, not independently verified integrations. The [validation record](docs/validation.md) separates structural checks, offline behavior, historical examples and live-data verification.

## Core upgrades, backed by executable checks

The current pass strengthens Buffett screening, single-stock valuation, framework backtesting and their consensus handoff. Valuation uses an explicit five-year date window and exact TTM fields; price and PE come from the same observation. Partial financial scores carry data issues and cannot enter consensus as complete votes.

Backtests rank using information at rebalance time, then evaluate selected holdings. Missing exit prices and benchmark data stop the run. Trading dates stay aligned, first-month losses count toward drawdown, and drift-aware turnover produces separate gross returns, costs, net returns and holding-level audit records.

**35 behavior tests pass. A single-stock live screen also passed with AKShare 1.19.3 on 2026-10-24**, using 2021–2025 annual periods and a 2026-10-23 valuation observation. See the [record](examples/verification/2026-10-24/buffett-check.json) and [CSV](examples/verification/2026-10-24/buffett-screen.csv). This verifies that path, not strategy profitability or every integration.

## Quick start: no market API required

Run from the repository root. These are **synthetic data**, not current stock observations:

```bash
git clone https://github.com/Serennity007/awesome-stock-quant-skills.git
cd awesome-stock-quant-skills
python -m pip install pandas
python my-skills/master-ensemble/scripts/ensemble.py --csvs examples/ensemble/quality.csv examples/ensemble/momentum.csv --out output/consensus.csv
```

Expected order and consensus scores: `000003: 83.3`, `000001: 66.7`, `000002: 50.0`. A `consensus.csv.meta.json` sidecar records provenance. `as_of` is null because no market-data date was supplied; a supplied date is user-declared and remains unverified.

For live A-share screening:

```bash
python -m pip install akshare pandas numpy
python my-skills/buffett-value-investing/scripts/screen.py --codes 600519,000858,600036 --out output/buffett.csv
```

Live retrieval depends on network, provider availability and package/API versions. Record actual trading dates and financial reporting periods. Read `score_status` and `decision` before using a score: `partial` / `needs_data` requires more evidence. This maintenance pass did not rerun all live-market integrations.

## Reproduce the cost and holdings audit

```bash
python my-skills/framework-backtest/scripts/backtest.py --cache-dir examples/backtest/cache --results-dir output/backtest-demo --frameworks danbin --start 2026-07-31 --top 1 --min-stocks 2 --cost-bps 10
```

This uses synthetic prices `100 → 110 → 99`, a 10 bps initial entry cost and no forced final liquidation. Expected net ending wealth: **0.98901**; benchmark: **1.01**. Inspect monthly gross/net returns, turnover, holding details and the input-hash manifest. This is a calculation fixture, not historical performance. [Scenario](examples/backtest/SCENARIO.md).

## Use in an agent

Copy only the skill folders you need into your assistant's skill directory. For environments using the common agents directory:

```bash
mkdir -p ~/.agents/skills
cp -r my-skills/quant-research-workflow ~/.agents/skills/
cp -r my-skills/buffett-value-investing ~/.agents/skills/
cp -r my-skills/master-ensemble ~/.agents/skills/
```

Claude Code may use `~/.claude/skills/`. For a bundled third-party project, install its inner folder containing `SKILL.md`, not the outer collection. The workflow skill does not install dependencies or other skills automatically.

Example: “Use quant-research-workflow to screen these companies for financial quality. Report data dates, component deductions and moat questions that still need qualitative evidence.”

## Browse the collection

- [Full original-skill table](README.md#原创技能): value, growth, defensive, themes, allocation, consensus and backtesting.
- [Third-party sources](README.md#第三方收录), each with its own license and SOURCE.md.
- [External resource index](docs/resource-index.md): legacy star counts are explicitly dated, not live rankings.
- [Historical demo records](docs/historical-demos.md): prior maintainer observations, not revalidated market data or investment performance.

## Verify and keep current

```bash
python -m pip install pandas pyyaml
python scripts/validate_repository.py
python -m unittest discover -s tests -v
python scripts/check_upstreams.py
```

Only the final command needs network access. The [workflow templates](docs/workflows) cover Python 3.11 / 3.13 quality checks and weekly metadata reports. The current GitHub credential lacks `workflow` scope, so these new workflows are not deployed. With appropriate permission, copy them to `.github/workflows/` and push to the default branch to enable them. They publish reports without replacing third-party code. A missing mirror commit is marked `snapshot-unpinned`; fetch failures remain visible and produce a nonzero exit.

Maintenance baseline: **2026-10-24**. Third-party files remain historical snapshots. See [maintenance details](docs/maintenance.md) and [validation scope](docs/validation.md).

## Scope and license

For research and education; not investment advice. Named-investor frameworks are rule-based approximations of public ideas, without endorsement or claims to replicate their decisions. Consensus scores are not win probabilities. The current backtest uses a present-day pool and a fixed 120-day reporting-lag approximation; actual disclosure dates and historical revisions are unverified, so strict point-in-time correctness is not established. Relative strategy rankings may also be biased.

Original skills and curation use [MIT](LICENSE); vendored works retain their own licenses and authorship. See [NOTICE](docs/NOTICE.md). The collection policy copies MIT / Apache-2.0 / BSD / CC0 projects and links other projects without copying them.
