# Awesome Stock Quant Skills

**Turn a stock research question into a runnable, reviewable workflow.**

[中文](README.md) · [English](README.en.md) · [日本語](README.ja.md)


<!-- inventory: originals=30 mirrors=16 vendored=225 -->

**30 original skills · 16 third-party source snapshots · 225 vendored SKILL.md files · Chinese / English / Japanese docs**

An Agent Skills toolbox for stock analysis and quantitative research: A-share quality, value, growth, momentum, themes and index allocation, plus US hot-stock tracking. Run the Python scripts directly, or let an Agent Skills-compatible assistant choose a workflow.

The useful chain is **choose a framework → fetch data → inspect component scores → compare frameworks → examine historical performance**. Scores remain linked to rules, inputs and limitations.

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

Live retrieval depends on network, provider availability and package/API versions. Record actual trading dates and financial reporting periods. This maintenance pass did not rerun all live-market integrations.

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
