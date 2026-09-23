---
name: hot-theme-scanner
description: A股热点题材扫描器：基于akshare概念板块与资金流向接口，识别近N日最热题材、列出领涨股并输出结构化热度表 | A-share hot theme scanner: identifies the hottest themes over N days, lists leading stocks, and outputs a structured heat table based on akshare concept-board and capital-flow APIs | A株ホットテーマスキャナー：akshareのコンセプト板・資金フローAPIを使い、N日間の人気テーマを特定し、上昇先導株をリストアップして構造化ヒート表を出力
author: Serennity007
license: MIT
---

# 🔥 A股热点题材扫描器（hot-theme-scanner）

每天开盘先看这张表。基于 akshare 概念板块与资金流向接口，对 A 股市场做**热点题材机械化扫描**：内置当前10大热点词典，拉取概念板块涨幅榜与主力资金流向，识别当日及近 N 日持续活跃的题材，输出结构化热度表，一眼看清资金正在往哪跑。

## 扫描逻辑

| 步骤 | 说明 |
|---|---|
| 1. 拉取概念资金流向 | 使用 `akshare.stock_fund_flow_concept` 拉取 即时 / 3日 / 5日 / 10日 排行，获取题材涨幅、主力净流入、领涨股 |
| 2. 匹配内置热点词典 | 将 `references/theme_glossary.md` 中的题材名与 akshare 板块名做模糊匹配（支持别名） |
| 3. 计算连续热度 | 统计题材在 1/3/5/10 日排行中连续进入前 N 名的最长时间窗口 |
| 4. 输出热度表 | 题材、匹配板块名、阶段涨幅、主力净流入、领涨股、连续上榜天数 |

## 使用方法

```bash
pip install akshare pandas

# 默认：扫描近 5 日热点，输出前 20 名
python scripts/hot_themes.py --days 5 --top 20 --out hot_themes.csv

# 只看当日即时排行
python scripts/hot_themes.py --days 1 --top 15
```

参数说明：

- `--days`: 统计窗口，支持 1/3/5/10（默认 5），不足时取最接近的可用窗口
- `--top`: 进入排行前 N 名才视为热门（默认 20）
- `--out`: CSV 输出路径（默认 `hot_themes.csv`）
- `--no-proxy`: 禁用系统代理（脚本默认已自动绕过系统代理，保留此参数用于兼容旧调用）

## 数据来源

- 东方财富/同花顺公开接口（akshare 封装）。
- 默认自动绕过系统代理（禁用环境代理变量），避免本地代理（如 `127.0.0.1:7890`）阻断数据源。
- 优先尝试东方财富概念板块接口；若因网络/代理不可用，自动降级到同花顺概念资金流向接口。

## 配套文件

- `references/theme_glossary.md` — 当前热点题材词典（题材名、核心逻辑、催化事件、代表股），需定期更新。

## 免责声明

本技能仅供学习研究，不构成投资建议。题材热度基于历史资金与价格统计，不代表未来走势；任何扫描结果都必须结合基本面与风险偏好二次确认。
