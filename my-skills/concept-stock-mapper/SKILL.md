---
name: concept-stock-mapper
description: A股题材关键词→概念股映射器：用akshare概念板块接口模糊匹配板块，取成分股并按涨幅/换手/主力资金排序，支持多关键词题材强度对比 | A-share theme keyword → concept stock mapper: fuzzy-match concept boards via akshare, extract constituents and sort by gain/turnover/main-force capital, supports multi-keyword theme strength comparison | A株テーマキーワード→概念股マッパー：akshareの概念セクターインターフェースであいまい一致し、構成銘柄を取得して騰落率/回転率/主力資金で並べ替え、複数キーワードの題材強度比較に対応
author: Serennity007
license: MIT
---

# 🎯 题材关键词→概念股映射器（A股）

输入一个或多个题材关键词，秒速生成概念股清单。脚本自动模糊匹配同花顺/东方财富概念板块，拉取板块成分股并按当日涨幅、换手率、主力资金活跃度排序；一次传入多个关键词时，还会输出题材强度对比表，帮助判断当前市场哪个题材更热。

数据来自 akshare 公开接口与同花顺行情中心页面（当 akshare 东方财富成分股接口不可达时的降级来源）。

## 核心能力

| 能力 | 说明 |
|---|---|
| 模糊匹配板块 | 对关键词做子串匹配，返回最相关的 1 个或多个概念板块 |
| 成分股清单 | 提取板块成分股，保留代码、名称、现价、涨跌幅、换手率、成交额、主力净流入 |
| 多维度排序 | 支持按 `change_pct`（涨跌幅）、`turnover`（换手率）、`main_force`（主力资金净流入）排序 |
| 多题材对比 | 同时输出各题材的板块涨幅、资金净流入、成交额、涨跌家数、成分股数量 |

## 使用方法

```bash
pip install akshare pandas

# 单关键词（默认按涨跌幅排序，取前 15）
python scripts/concept_mapper.py --keywords 商业航天

# 多关键词 + 自定义排序与输出
python scripts/concept_mapper.py --keywords 商业航天,核聚变,固态电池 --top 15 --sort main_force --out concept_result.csv
```

参数说明：

- `--keywords`：逗号分隔的题材关键词，支持模糊匹配。
- `--top`：每个题材输出前 N 只成分股，默认 15。
- `--sort`：排序维度，`change_pct`（涨跌幅，默认）、`turnover`（换手率）、`main_force`（主力资金净流入）。
- `--out`：CSV 输出路径，默认 `concept_stocks.csv`。

## 输出解读

CSV 包含两部分信息：

1. **题材强度对比表**：每个关键词命中的板块名称、板块涨幅、资金净流入、成交额、涨跌家数、成分股数量。
2. **成分股明细表**：每只股票所属题材、代码、名称、现价、涨跌幅、换手率、成交额、主力净流入、在所属题材内的排序。

配合 AI 使用时，可快速回答：

- 某个热点涉及哪些概念股？
- 同一产业链下，哪个细分题材更强？
- 龙头股（前排涨停）与中军（换手适中、成交额大）分别是哪些？

## 免责声明

本技能仅供学习研究，不构成投资建议。题材炒作波动剧烈，跟风风险极高，任何输出都必须结合市场环境与自身判断二次确认。
