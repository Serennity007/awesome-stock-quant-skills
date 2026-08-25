# 📊 Stock-Analysis-3D

> Claude Code 股票智能分析技能 — **3D 评分系统**：技术面 50 + 基本面 30 + 消息面 20。
> 支持 A 股 / 港股 / 美股，输入股票代码即出决策看板。

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python&logoColor=white)
![Claude Code](https://img.shields.io/badge/Claude_Code-Skill_v2.0-blueviolet?logo=anthropic&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Markets](https://img.shields.io/badge/Markets-A股_|_港股_|_美股-orange)
![Scoring](https://img.shields.io/badge/Scoring-3D_Composite-red)

---

## 🙏 致谢与说明

**本项目基于 [@liusai0820](https://github.com/liusai0820) 的 [Stock-Analysis-Skill](https://github.com/liusai0820/Stock-Analysis-Skill) 改造**，遵循 MIT 协议。

原项目提供了：
- 完整的 Claude Code Skill 封装架构
- 技术指标计算（MA / MACD / RSI / 量能 / 乖离 / 支撑）
- 行情数据分级降级策略（Tushare → efinance → akshare → yfinance）
- 100 分技术评分体系（本项目的"技术 50 分"模块即来自这里，缩放后保留全部原始逻辑）

**本 fork 的核心改造**：从"纯技术面"升级为"**技术 + 基本面 + 消息面**"三维评分。

> 详细的差异说明、上游同步指引见 [NOTICE.md](./NOTICE.md)。

---

## ✨ 3D 评分系统

```
总分 100 = 技术面 50 + 基本面 30 + 消息面 20
```

| 维度 | 满分 | 子项 | 来源 |
|------|------|------|------|
| **技术面** | 50 | 趋势 15 + 乖离 10 + 量能 8 + MACD 8 + RSI 5 + 支撑 4 | Python 计算 |
| **基本面** | 30 | PE 5 + PB 5 + ROE 5 + 营收增速 5 + 毛利率 5 + 资产负债率 5 | Python 计算 |
| **消息面** | 20 | 新闻情绪 10 + 机构动作 5 + 资金流向 5 | **Claude AI 评分** |

### 信号档位

| 总分 | 信号 | 含义 |
|------|------|------|
| 80+ | 🟢 强烈买入 | 三面共振利好 |
| 65-79 | 🔵 买入 | 两面以上利好 |
| 50-64 | 🟡 持有 | 互相对冲 |
| 35-49 | ⚪ 观望 | 一面利好压不住其他 |
| 20-34 | 🟠 卖出 | 多面利空 |
| <20 | 🔴 强烈卖出 | 三面共振利空 |

---

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/Geralt-L/Stock-Analysis-3D.git ~/.claude/skills/stock-analysis
```

Windows 用户：

```powershell
git clone https://github.com/Geralt-L/Stock-Analysis-3D.git "$env:USERPROFILE\.claude\skills\stock-analysis"
```

Python 依赖（首次运行会自动安装）：

```bash
pip3 install akshare yfinance efinance
```

### 使用

在 Claude Code 中直接输入：

```
分析下 TSLA
帮我看看沃尔核材 002130
HK09981 怎么样
对比下 京东健康 阿里健康
```

或者明确触发：

```
/stock-analysis 002130,HK09981,TSLA
```

---

## 🎯 输出示例（3D 决策看板）

```
### 沃尔核材(HK09981) — ⚪ 观望（37/100）

| 指标 | 数值 |
|------|------|
| 现价 | 13.78 HKD (-4.64%) |
| 总分 | 37/100 |
| 信号 | 观望 |

🎯 三维评分拆解

| 维度 | 得分 | 满分 | 关键观察 |
|------|------|------|---------|
| 技术面 | 11.0 | 50 | 强势空头排列，RSI6 极端超卖 9.47 |
| 基本面 | 26.0 | 30 | 优秀（PE 13.5 + ROE 15% + 低负债率） |
| 消息面 | 0/20 | — | (Claude 待填) |

💰 基本面拆解
| 子项 | 得分 | 数值 | 评级 |
|------|------|------|------|
| PE | 5/5 | 13.51 | 便宜 |
| PB | 5/5 | 1.76 | 便宜 |
| ROE | 4/5 | 15.06% | 优秀 |
| 营收YoY | 3/5 | 15.5% | 稳健 |
| 毛利率 | 4/5 | 30.66% | 健康 |
| 负债率 | 5/5 | 17.93% | 非常健康 |

📰 消息面拆解（AI 评分）
| 子项 | 得分 | 评分理由 |
|------|------|---------|
| 新闻情绪 | 6/10 | Q1 增收不增利触发回调，但 224G 已通过英伟达认证 |
| 机构动作 | 2/5 | 主力资金净流出，机构调研频次下降 |
| 资金流向 | 2/5 | 5/8 净卖出 1.22 亿 + 5/14 净卖出 2.27 亿 |
```

> 同时输出：技术面拆解、AI 综合判断、看多/看空因素、入场/目标/止损价位

---

## 🧠 工作原理

```
用户输入股票代码
      │
      ▼
[STEP 1] 解析市场（A股/港股/美股），标准化代码
      │
      ▼
[STEP 2] Python 取数据 + 算技术 + 算基本面
      │   → technical_50 (0-50) + fundamental_30 (0-30)
      ▼
[STEP 3] WebSearch 搜索近 30 天新闻
      │
      ▼
[STEP 4] ★ Claude 给消息面打分 (0-20)
      │   按"情绪 10 + 机构 5 + 资金 5"
      ▼
[STEP 5] 合并 total_100 = technical + fundamental + news
      │
      ▼
[STEP 6] 输出 3D 决策看板（含三维拆解 + 信号 + 目标价）
```

---

## 📊 基本面打分细则

### PE 估值（5 分）

| PE | 得分 |
|----|------|
| < 15 | 5 便宜 |
| 15-25 | 4 合理 |
| 25-40 | 3 偏贵 |
| 40-60 | 1 高估 |
| > 60 或 < 0 | 0 极度高估/亏损 |

### ROE（5 分）

| ROE % | 得分 |
|-------|------|
| ≥ 20% | 5 高质量 |
| 15-20% | 4 优秀 |
| 10-15% | 3 一般 |
| 5-10% | 2 偏弱 |
| 0-5% | 1 很弱 |
| < 0 | 0 亏损 |

### 营收增速（5 分）

| YoY | 得分 |
|-----|------|
| ≥ 50% | 5 高速 |
| 20-50% | 4 强劲 |
| 10-20% | 3 稳健 |
| 0-10% | 2 缓慢 |
| -10~0% | 1 下滑 |
| < -10% | 0 大幅下滑 |

> 其余 PB / 毛利率 / 资产负债率打分逻辑见 [`references/stock_data_fetcher.py`](references/stock_data_fetcher.py)。

---

## 📰 消息面打分细则（Claude 评分）

### 新闻情绪（10 分）

| 分数 | 情绪 | 典型场景 |
|------|------|---------|
| 9-10 | 强利好 | 业绩超预期 +30%、重大客户签约、政策强力扶持 |
| 7-8 | 利好 | 业绩超预期、新品获认证 |
| 5-6 | 中性偏多 | 业绩符合预期、有正面进展 |
| 4 | 中性 | 无重大新闻 |
| 2-3 | 利空 | 业绩不及预期、客户流失、监管处罚 |
| 0-1 | 强利空 | 财务造假、董事会动荡、退市风险 |

### 机构动作（5 分）

| 分数 | 情况 |
|------|------|
| 5 | 多家券商上调评级 / 知名投资者增持 |
| 4 | 北向资金净流入 / 个别上调 |
| 3 | 中性 |
| 2 | 个别下调评级 / 北向净流出 |
| 0-1 | 多家下调 / 重要股东减持 |

### 资金流向（5 分）

| 分数 | 情况 |
|------|------|
| 5 | 主力多日净流入 / 北水大幅买入 |
| 4 | 主力短期净流入 |
| 3 | 中性 |
| 2 | 主力短期净流出 |
| 0-1 | 主力大额净卖出 / 大单砸盘 |

---

## ⚙️ 数据源配置（可选）

零配置可用。配置以下环境变量后数据更精准：

| 环境变量 | 用途 | 获取 | 免费额度 |
|----------|------|------|---------|
| `TUSHARE_TOKEN` | A 股专业数据 | [tushare.pro](https://tushare.pro) | 基础接口免费 |
| `TAVILY_API_KEY` | 新闻搜索 | [tavily.com](https://tavily.com) | 1000 次/月 |
| `SERPAPI_KEY` | 新闻搜索备选 | [serpapi.com](https://serpapi.com) | 100 次/月 |

### 行情数据降级链

```
A 股: Tushare Pro → efinance → akshare → yfinance
港股: efinance → akshare → yfinance
美股: yfinance（主力）
```

### 基本面数据降级链（本项目新增）

```
A 股:  akshare 同花顺 → akshare 个股信息 → efinance base_info → yfinance
港股:  akshare HK 财务指标 → yfinance
美股:  yfinance（trailingPE / priceToBook / returnOnEquity 等）
```

---

## 🛡️ 硬性规则（继承自原项目）

1. **RSI > 80** → 绝不给买入信号（超买风险）
2. **乖离率 MA5 > 5%** → 绝不给买入信号（不追高）
3. **三维都 ≤ 满分 50%** → 绝不给买入信号
4. **必须给精确止损价**
5. **偏好缩量回调买点**

---

## 📁 项目结构

```
Stock-Analysis-3D/
├── SKILL.md                           # Skill 定义（Claude Code 入口）
├── README.md                          # 本文件
├── NOTICE.md                          # 致谢 + 改造说明
├── LICENSE                            # MIT（双版权：原作者 + 本 fork）
└── references/
    ├── stock_data_fetcher.py          # 取数据 + 算指标 + 评分（~1170 行）
    ├── analysis-prompt-template.md    # AI 分析框架（保留原版）
    └── output-format-template.md      # 3D 决策看板模板（v2.0 重写）
```

---

## 🔄 与上游同步

```bash
git remote add upstream https://github.com/liusai0820/Stock-Analysis-Skill.git
git fetch upstream
git merge upstream/main
```

本项目保留了 `pre-3d-refactor` tag 作为上游原始代码的快照，方便三方合并。

---

## 📜 License

MIT — 同时保留原作者 [@liusai0820](https://github.com/liusai0820) (Yzz) 与本 fork 作者 [@Geralt-L](https://github.com/Geralt-L) 的版权声明，详见 [LICENSE](./LICENSE)。

---

## 👤 Authors & Credits

- **3D Scoring Extension**: [@Geralt-L](https://github.com/Geralt-L)
- **Original Stock-Analysis-Skill**: [@liusai0820](https://github.com/liusai0820) (Yzz)
- **Further Upstream Inspiration**: [@ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis)
- **Built on**: [Claude Code](https://claude.com/claude-code) by Anthropic

---

> Built with Claude Code ⚡ — Forked, extended, and shared with gratitude.
