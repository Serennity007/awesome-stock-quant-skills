# 第一次使用 / First run

默认分支包含 30 个原创 Skill。先运行两个内置合成场景，检查安装和计算链路，再按目标安装 Skill 或接入市场数据。

The default branch includes all 30 original Skills. Start with the bundled synthetic examples, then select the Skills and market-data dependencies needed for your own research.

## 1. 准备环境 / Setup

使用 Python 3.11 或更新版本。演示只需 NumPy 和 pandas；这份依赖文件不负责安装整个第三方合集。

```bash
git clone https://github.com/Serennity007/awesome-stock-quant-skills.git
cd awesome-stock-quant-skills
python -m pip install -r requirements-demo.txt
```

已有本地副本时，可在确认本地改动已保存后更新默认分支。此后的演示只读取仓库中的合成 CSV；安装依赖需要包源访问。

## 2. 一条命令运行 / Run

```bash
python scripts/run_demo.py
```

运行两个独立场景：多框架共识排序，以及含交易成本的月度回测核算。它们分别使用自己的合成输入。

成功后，终端会打印 `PASS` 和报告路径：`output/demo/run-…/REPORT.md`。每次创建新子目录，保留此前的结果。

Run two independent synthetic scenarios: consensus ranking and backtest arithmetic with transaction costs. The terminal prints the report path after validation passes; repeated runs preserve previous output.

## 3. 查看结果 / Inspect

`REPORT.md` 是阅读入口，也可以打开原始文件：

| 文件 | 用途 |
|---|---|
| `consensus.csv` | 共识分、排序、框架覆盖数与分项原始分 |
| `consensus.csv.meta.json` | 输入文件哈希、参数和运行时间 |
| `backtest/bt_result_danbin.csv` | 两期毛净收益、换手、成本和基准 |
| `backtest/bt_holdings_danbin.csv` | 逐期持仓与进出价格 |
| `backtest/bt_manifest.json` | 缓存哈希与回测参数 |
| `consensus.log` / `backtest.log` | 两个原有 CLI 的输出 |
| `status.json` | `passed` 或 `failed`，明确标记 `synthetic` |

共识排序应为：

| 合成代码 | 共识分 |
|---|---:|
| 000003 | 83.3 |
| 000001 | 66.7 |
| 000002 | 50.0 |

回测输入价格人为设为 `100 → 110 → 99`；净期末资产应为 `0.999 × 1.1 × 0.9 = 0.98901`，基准为 `1.01`。细节见 [场景说明](../examples/backtest/SCENARIO.md)。这些数值检查计算行为，不代表真实证券表现。

The examples are synthetic. Their scores and ending wealth are calculation fixtures, not trading performance.

## 指定输出位置 / Output location

```bash
python scripts/run_demo.py --output-dir "output/my demo"
```

这个路径是输出父目录；脚本仍会创建独立的 `run-…` 子目录。

## 常见问题 / Troubleshooting

- **缺依赖**：运行终端给出的 `pip install -r requirements-demo.txt` 命令，使用同一个 Python 解释器。
- **运行失败**：脚本非零退出；查看本次目录下的 `status.json` 和日志。失败不会生成成功报告。
- **准备使用真实数据**：阅读目标 Skill 的 `SKILL.md`、依赖和数据口径。演示不会安装 Skill、拉取实时行情或发送交易指令。
- **希望复核源码**：运行目录校验与完整测试；PyYAML 仅用于仓库校验，不是演示运行依赖。

```bash
python -m pip install pyyaml
python scripts/validate_repository.py
python -m unittest discover -s tests -v
```

2026-10-25 本地验证为 40 项测试通过，环境与范围见 [验证记录](validation.md)。
