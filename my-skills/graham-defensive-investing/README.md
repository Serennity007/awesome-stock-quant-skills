# 🛡️ A股格雷厄姆防御型七准则筛股器｜7道铁门护本金

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | License：MIT | 数据：akshare（东方财富 / 新浪财经公开接口）

把本杰明·格雷厄姆的防御型选股框架搬到 A 股：用 7 道量化铁门（规模、流动比率、连续盈利、连续分红、盈利增长、PE<15、PB<1.5 或 PE×PB<22.5）批量初筛股票，自动标注数据窗口是 10 年还是降级为 5 年，一眼看清哪些标的符合"先求不亏"的保守标准。

## 快速开始

```bash
pip install akshare pandas

# 沪深300成分股中筛选
python scripts/screen.py --pool hs300 --top 20 --out graham_result.csv

# 小样本实测
python scripts/screen.py --codes 600519,000858,600036 --out graham_result.csv
```

## 参数说明

- `--pool`: 股票池，目前支持 `hs300`
- `--codes`: 逗号分隔的自定义股票代码，优先于 `--pool`
- `--top`: 终端展示前 N 名（默认 20）
- `--out`: CSV 输出路径（默认 `graham_result.csv`）
- `--min-cap`: 最小总市值门槛，单位亿元（默认 200）
- `--sleep`: 每只股票间隔秒数（默认 0.5，防限流）

## 7 道关卡

| 关卡 | 标准 |
|---|---|
| 规模足够 | 总市值 ≥ 200 亿元（可调） |
| 流动比率 | 最新年度 > 2 |
| 连续盈利 | 窗口期内每年扣非每股收益 > 0 |
| 连续分红 | 窗口期内每年都有现金分红 |
| 盈利增长 | 窗口期末 EPS / 期初 EPS > 4/3 |
| 低 PE | PE(静) < 15 |
| 低 PB | PB < 1.5 或 PE × PB < 22.5 |

> 数据不足 10 年时自动降级为 5 年窗口并标注；不足 5 年则标记 `NA`。

## 文件说明

- `SKILL.md` — 技能定义与详细使用说明
- `scripts/screen.py` — 防御型七准则筛股脚本
- `references/graham_principles.md` — 格雷厄姆核心原则：安全边际、市场先生、防御型 vs 进取型、烟蒂股风险

## 免责声明

仅供学习研究，不构成投资建议。历史财务指标不代表未来表现，任何筛选结果都必须经过自己对生意与估值的理解二次确认。
