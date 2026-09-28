# 🤝 大师共识筛选器｜跨框架交集合成器

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | 许可证：MIT | 依赖：仅 pandas（纯本地 CSV 合成，无网络调用）

> **"多条互相独立的思路同时指向同一标的，才是给概率加权。"**

本技能把仓库内任意多个大师 skill 的打分结果 CSV（各 `screen.py` 输出，含 `code`/`total` 列）合成为跨框架共识名单：框架内百分位归一 → 共识分（各框架百分位均值）+ 顶级命中数 + 覆盖框架数，输出交集标的。

## 目录结构

- `SKILL.md` — 技能定义、共识逻辑与使用方法
- `scripts/ensemble.py` — 共识合成器（秒级完成，无网络调用）
- `references/ensemble_methodology.md` — 方法论：百分位归一的理由、框架冲突的解读、共识的局限
- `consensus_hs300_demo.csv` — 但斌+李录+欧奈尔三框架全量沪深300共识 demo

## 快速开始

```bash
pip install pandas

# 第一步：各大师框架全量跑测（同一股票池，如 --pool hs300）
python ../dan-bin-rose-of-time/scripts/screen.py --pool hs300 --out danbin_hs300_result.csv
python ../li-lu-value-compounding/scripts/screen.py --pool hs300 --out lilu_hs300_result.csv
python ../oneil-canslim/scripts/screen.py --pool hs300 --out canslim_hs300_result.csv

# 第二步：合成共识
python scripts/ensemble.py \
    --csvs ../dan-bin-rose-of-time/danbin_hs300_result.csv \
           ../li-lu-value-compounding/lilu_hs300_result.csv \
           ../oneil-canslim/canslim_hs300_result.csv \
    --min-frameworks 2 --out consensus.csv
```

## 参数说明

- `--csvs`: 至少 2 个大师结果 CSV，文件名去掉 `_result` 等后缀即框架名。
- `--top-pct`: 单框架"顶级命中"分位线（默认前 10%）。
- `--min-frameworks`: 至少被几个框架覆盖才输出（默认 2）。
- `--out`: 共识 CSV 输出路径（默认 `consensus.csv`）。

## 输出字段

- `code` / `name` / `industry`：代码 / 简称 / 行业（元信息取自首个含该列的框架）
- `consensus_score`：共识分（各框架百分位均值，0-100）
- `top_hits`：处于各框架前 10% 分位的框架数
- `frameworks`：覆盖框架数
- `<框架>_pct` / `<框架>_raw`：各框架内百分位与原始分

## 免责声明

仅供学习研究，不构成投资建议。共识分不校验"共同的数据错误"，框架间也非完全独立，历史一致不代表未来一致。
