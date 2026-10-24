# 验证范围与复现证据

验证日期：2026-10-24。不能把文件数量、测试数量、历史选股分数解释为投资表现。

## 本次执行

| 检查 | 结果 | 证明范围 |
|---|---|---|
| 原创 skill 与目录统计 | 30 个原创、16 个来源目录、225 份第三方 SKILL.md | 目录规模，不代表全部接口已跑通 |
| 原创 frontmatter、路由与文档链接 | `python scripts/validate_repository.py` | 结构、命名、描述、许可文件与本次文档本地链接；修复原有 29 份未正确引用的 YAML description，并将作者移入 metadata |
| 离线行为测试 | 35 个测试方法通过 | 估值窗口、TTM、缺失财务、日期对齐、退出缺价、首月回撤、漂移换手、成本与 CLI 持仓审计；共识与巡检行为 |
| 合成数据端到端运行 | 000003 / 000001 / 000002，分数 83.3 / 66.7 / 50.0 | CSV → 合成 → CSV + JSON 计算链路 |
| 合成回测端到端运行 | 两期净期末资产 0.98901，基准 1.01 | 价格 → 打分 → 持仓 → 毛净收益 → 输入哈希；不是历史业绩 |
| AKShare 1.19.3 实时小样 | 单股筛选成功，2021–2025 年报期，估值交易日 2026-10-23 | 当次真实取数与规则计算链路，非投资收益证明 |
| 实际上游巡检 | 16 个来源中 15 个查询成功，1 个返回 HTTP 404；AKShare PyPI 版本 1.19.3 | 当次远程元数据查询，不代表镜像已更新或行情接口可用 |

本地离线验证环境为 Python 3.11.9 / pandas 3.0.2。35 项测试也在禁止导入 AKShare 和 requests 的环境下通过，缓存回测可离线执行。AKShare 1.19.3 通过隔离目录安装做实时小样，未替换本机原有 1.18.96。[质量工作流模板](workflows/quality.yml)覆盖 Python 3.11 / 3.13；因当前凭据缺少 `workflow` 权限，新工作流未部署，不能把模板配置等同于远端通过。

原始上游巡检记录：[Markdown](../reports/upstreams/latest.md)、[JSON](../reports/upstreams/latest.json)。当次不可访问的来源为 `AlexLiu0130/ibkr-options-assistant`；404 本身无法确定其删除、迁移或权限变化原因。16 份旧来源均未记录精确提交号，因此标为 `snapshot-unpinned`。本次没有据此替换第三方代码。

实时原始产物：[查询记录](../examples/verification/2026-10-24/buffett-check.json)、[筛选 CSV](../examples/verification/2026-10-24/buffett-screen.csv)。单股评分只是规则计算结果，不是胜率或买入结论。

## 复现离线检查

在仓库根目录执行：

```bash
python -m pip install pandas pyyaml
python scripts/validate_repository.py
python -m unittest discover -s tests -v
python my-skills/master-ensemble/scripts/ensemble.py --csvs examples/ensemble/quality.csv examples/ensemble/momentum.csv --out output/consensus.csv
python my-skills/framework-backtest/scripts/backtest.py --cache-dir examples/backtest/cache --results-dir output/backtest-demo --frameworks danbin --start 2026-07-31 --top 1 --min-stocks 2 --cost-bps 10
```

查看输出 CSV 与 `.meta.json`。`as_of=null` 表示未提供数据日；即使使用 `--as-of`，它也只是用户声明，脚本不自动校验原始抓取日期。测试覆盖错误输入非零退出与防止覆盖输入，不能证明真实财务数据正确。

## 尚未证明的能力

- 本次未重跑 30 个原创与 225 个第三方 skill 的全部联网接口；依赖、密钥与数据权限各不相同。
- 本次未复测历史示例中的股价、财务数值、候选排名、估值或回测收益。[历史记录](historical-demos.md)保留原日期与出处，仅作既有样例。
- `framework-backtest` 已修复使用未来退出价格可得性提前选股、基准交易日改标及首月回撤问题，并加入成本、持仓与哈希产物。但实际披露日、历史修订版本、历史成分、复权分红和可成交约束尚未完整建模，仍非严格 point-in-time 或真实可成交总回报系统。
- 共识框架共享因子与数据源，不具备已证明的统计独立性；共识分不是胜率、收益预测或投资大师本人认可。

## 维护验证与投资验证分开

离线测试回答“计算和报错行为是否符合约定”；实时取数回答“这一刻的接口与字段是否可用”；无偏历史回测与样本外研究才可能检验策略假设。发布 README 时应分别写清，不互相替代。

## 先验证能力，再调整叙述

本轮先用回归测试复现原实现错误，再修改筛选与回测脚本。单股实时接口、离线 CLI 与行为测试通过后，才更新 README。修复前五项估值/数据测试均失败；回测可复现未来缺价筛选、首月回撤遗漏和投资期间缺月等问题。测试使用原始行为构造反例，不以 README 措辞或测试数量作为能力证明。
