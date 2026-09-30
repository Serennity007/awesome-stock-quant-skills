# 📊 大师框架回测验证器｜月度调仓检验框架真金白银的表现

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | 许可证：MIT | 数据源：akshare（东财/新浪公开接口）+ 本地缓存

> **"回测是策略的照妖镜——所有讲不出来的收益都是故事。"**

本技能把仓库里的大师框架变成**可证伪的策略**：每月末全池打分 → 等权买入前 N 名 → 持有到下月末 → 累计净值对照沪深300。打分严格 point-in-time（只用已发布 ≥120 天的年报 + 当期估值），无未来函数。v1 支持 danbin（但斌六维）/ lilu（李录六维）/ mom12_1（12-1 月动量基准）。

## 目录结构

- `SKILL.md` — 技能定义、回测口径与使用方法
- `scripts/fetch_history.py` — 个股历史数据缓存器（估值/年度指标/利润表，可断点续传、分块）
- `scripts/backtest.py` — 月度调仓回测引擎
- `references/backtest_methodology.md` — 方法论：point-in-time 原则、幸存者偏差、相对比较的正确用法
- `results/` — 回测输出（汇总/月度净值/逐年表）
- `cache/` — 数据缓存（.gitignore 排除）

## 快速开始

```bash
pip install akshare pandas numpy

# 第一步：拉取全池历史数据（约 25 分钟，断点续传）
python scripts/fetch_history.py --pool hs300

# 第二步：回测三框架
python scripts/backtest.py
```

## 已知局限（读结果前必读）

1. **幸存者偏差**：股票池固定为当前沪深300，绝对收益被系统性高估——**只做框架间相对比较**。
2. 无交易成本（月度换手 10 只约 1-2pp/年）。
3. PE/PB 历史约自 2018 年起。
4. 年报滞后按 120 天近似。

## 免责声明

仅供学习研究，不构成投资建议。回测收益不代表未来。
