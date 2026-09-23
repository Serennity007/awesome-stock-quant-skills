# 🦎 宏观变色龙｜德鲁肯米勒式灵活仪表盘

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | License：MIT | 数据：akshare（中行/新浪/东财/同花顺公开接口）

每天开盘前先看一眼全球资金的"风向"。本技能以斯坦利·德鲁肯米勒（Stanley Druckenmiller）的宏观交易哲学为框架，用 akshare 把 **7 大类资产** 的趋势与动量压缩成一张表：美元/人民币汇率、中美 10 年期国债收益率、黄金、原油、铜、A 股主要指数，以及可选个股。输出不是交易信号，而是一张**趋势跟随视角的多空倾向快照**。

## 快速开始

```bash
pip install akshare pandas

# 默认 20 日窗口，输出 macro_dashboard.csv
python scripts/macro_dashboard.py

# 自定义窗口 + 输出
python scripts/macro_dashboard.py --days 20 --out macro_dashboard.csv

# 加入自选个股同步扫描
python scripts/macro_dashboard.py --days 20 --codes 600519,000858,600036 --out my_dashboard.csv
```

## 参数说明

- `--days`: 趋势/动量计算窗口（默认 20）
- `--codes`: 逗号分隔的 A 股个股代码（可选）
- `--out`: CSV 输出路径（默认 `macro_dashboard.csv`）
- `--no-proxy`: 禁用系统代理（脚本已默认禁用，保留兼容参数）

> 代理说明：脚本启动时自动清除 `HTTP_PROXY` / `HTTPS_PROXY` 等环境变量，避免本地代理（如 `127.0.0.1:7890`）阻断数据源。优先尝试东方财富/首选接口，失败自动降级到新浪/中行/同花顺。

## 输出字段

| 字段 | 说明 |
|---|---|
| `asset` | 资产名称 |
| `category` | 资产类别（fx/bond_cn/bond_us/commodity/equity/stock） |
| `current` | 最新收盘价/收益率/汇率 |
| `ma_n` | N 日移动平均 |
| `roc_n` | N 日涨跌幅% |
| `roc_5` | 近 5 日涨跌幅% |
| `trend` | 趋势描述（上升/下降/震荡/拐点） |
| `signal` | 趋势信号（BULLISH/BEARISH/NEUTRAL） |
| `bias` | 多空倾向描述（如"美元偏空"、"中债偏多"） |
| `source` | 实际使用的数据来源 |

## 判定逻辑

```
BULLISH = 收盘价 > N 日均线 且 N 日涨跌幅 > 0
BEARISH = 收盘价 < N 日均线 且 N 日涨跌幅 < 0
NEUTRAL = 其他情况
```

国债收益率的趋势方向与债券价格相反：收益率上行 = 债券偏空。脚本最后会汇总综合宏观得分与整体立场提示。

## 配套文件

- `SKILL.md` — 技能定义与完整说明
- `scripts/macro_dashboard.py` — 宏观仪表盘脚本
- `references/druckenmiller_style.md` — 德鲁肯米勒投资思想要点整理

## 免责声明

仅供学习研究，不构成投资建议。宏观趋势与动量均由历史价格统计而来，不代表未来走势；任何输出都必须经过自己对宏观环境、流动性与风险偏好的理解二次确认。
