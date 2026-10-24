# 验证范围与复现证据

验证日期：2026-10-24。不能把文件数量、测试数量、历史选股分数解释为投资表现。

## 本次执行

| 检查 | 结果 | 证明范围 |
|---|---|---|
| 原创 skill 与目录统计 | 30 个原创、16 个来源目录、225 份第三方 SKILL.md | 目录规模，不代表全部接口已跑通 |
| 原创 frontmatter、路由与文档链接 | `python scripts/validate_repository.py` | 结构、命名、描述、许可文件与本次文档本地链接；修复原有 29 份未正确引用的 YAML description，并将作者移入 metadata |
| 离线行为测试 | 13 个测试方法通过 | 共识排序、错误输入、追溯文件；巡检差异、许可、失败状态 |
| 合成数据端到端运行 | 000003 / 000001 / 000002，分数 83.3 / 66.7 / 50.0 | CSV → 合成 → CSV + JSON 计算链路 |
| 实际上游巡检 | 16 个来源中 15 个查询成功，1 个返回 HTTP 404；AKShare PyPI 版本 1.19.3 | 当次远程元数据查询，不代表镜像已更新或行情接口可用 |

本地离线验证环境为 Python 3.11.9 / pandas 3.0.2。[质量工作流模板](workflows/quality.yml)覆盖 Python 3.11 / 3.13；因当前凭据缺少 `workflow` 权限，新工作流未部署，不能把模板配置等同于远端通过。

原始上游巡检记录：[Markdown](../reports/upstreams/latest.md)、[JSON](../reports/upstreams/latest.json)。当次不可访问的来源为 `AlexLiu0130/ibkr-options-assistant`；404 本身无法确定其删除、迁移或权限变化原因。16 份旧来源均未记录精确提交号，因此标为 `snapshot-unpinned`。本次没有据此替换第三方代码。

## 复现离线检查

在仓库根目录执行：

```bash
python -m pip install pandas pyyaml
python scripts/validate_repository.py
python -m unittest discover -s tests -v
python my-skills/master-ensemble/scripts/ensemble.py --csvs examples/ensemble/quality.csv examples/ensemble/momentum.csv --out output/consensus.csv
```

查看输出 CSV 与 `.meta.json`。`as_of=null` 表示未提供数据日；即使使用 `--as-of`，它也只是用户声明，脚本不自动校验原始抓取日期。测试覆盖错误输入非零退出与防止覆盖输入，不能证明真实财务数据正确。

## 尚未证明的能力

- 本次未重跑 30 个原创与 225 个第三方 skill 的全部联网接口；依赖、密钥与数据权限各不相同。
- 本次未复测历史示例中的股价、财务数值、候选排名、估值或回测收益。[历史记录](historical-demos.md)保留原日期与出处，仅作既有样例。
- `framework-backtest` 的实际披露日、历史修订版本、历史成分、交易成本和可成交约束尚未完整建模；本次修正文档表述，没有把回测引擎升级成严格 point-in-time 系统。
- 共识框架共享因子与数据源，不具备已证明的统计独立性；共识分不是胜率、收益预测或投资大师本人认可。

## 维护验证与投资验证分开

离线测试回答“计算和报错行为是否符合约定”；实时取数回答“这一刻的接口与字段是否可用”；无偏历史回测与样本外研究才可能检验策略假设。发布 README 时应分别写清，不互相替代。
