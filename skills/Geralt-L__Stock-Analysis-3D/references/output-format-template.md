# 3D Decision Dashboard Output Format

## Format Specification

Use exactly this Markdown structure for the 3D scoring output dashboard.

### Header

```
## {DATE} 股票决策看板（3D 评分）

{N} 只股票分析完成 | 强买/买: {n} | 持有: {n} | 观望/卖: {n}
```

### Per-Stock Card

For each stock, output one card separated by `---`:

```
### {NAME}({CODE}) — {SIGNAL_EMOJI} {SIGNAL_CN}（{TOTAL}/100）

| 指标 | 数值 |
|------|------|
| 现价 | {price} ({change_pct:+.2f}%) |
| **总分** | **{total}/100** |
| 信号 | {signal_cn} |
| 市场 | {market} |

**🎯 三维评分拆解**

| 维度 | 得分 | 满分 | 关键观察 |
|------|------|------|---------|
| 技术面 | {technical_50} | 50 | {tech_oneline} |
| 基本面 | {fundamental_30} | 30 | {fund_oneline} |
| 消息面 | {news_20} | 20 | {news_oneline} |
| **总计** | **{total}** | **100** | **{signal_cn}** |

**📊 技术面拆解（50 分）**

| 子项 | 得分(满分) | 解读 |
|------|----------|------|
| 趋势/均线 | {trend}/15 | MA5={ma5} MA10={ma10} MA20={ma20} | {alignment_cn} |
| 乖离率 | {bias}/10 | MA5乖离 {bias_ma5:+.2f}% |
| 量能 | {vol}/8 | 量比 {vol_ratio} | {vol_trend_cn} |
| MACD | {macd}/8 | DIF={dif} DEA={dea} 柱={hist} |
| RSI | {rsi}/5 | RSI6={rsi6} RSI12={rsi12} |
| 支撑 | {sup}/4 | MA5支撑={support_ma5}, MA10支撑={support_ma10} |

**💰 基本面拆解（30 分）**

| 子项 | 得分(满分) | 数值 | 评级 |
|------|----------|------|------|
| PE 估值 | {pe_score}/5 | {pe_ttm} | {pe_note} |
| PB 估值 | {pb_score}/5 | {pb} | {pb_note} |
| ROE | {roe_score}/5 | {roe}% | {roe_note} |
| 营收增速 | {rev_score}/5 | {rev_yoy}% | {rev_note} |
| 毛利率 | {gm_score}/5 | {gm}% | {gm_note} |
| 资产负债率 | {debt_score}/5 | {da}% | {debt_note} |

基本面总评: **{fundamental_rating}**（{fundamental_30}/30）

**📰 消息面拆解（20 分，AI 评分）**

| 子项 | 得分(满分) | 评分理由 |
|------|----------|---------|
| 新闻情绪 | {news_sentiment}/10 | {news_sentiment_reason} |
| 机构动作 | {institutional}/5 | {institutional_reason} |
| 资金流向 | {capital_flow}/5 | {capital_flow_reason} |

近期关键新闻：
- {news1}
- {news2}
- {news3}

**🧠 AI 综合判断**

{2-3 段综合分析。必须明确说明：
 ① 三维哪个维度是支撑/拖累；
 ② 矛盾点在哪（如基本面好但技术差）；
 ③ 给出明确的"现在该做什么"动作}

**✅ 看多因素 / ❌ 看空因素**

看多：
- {bull1}
- {bull2}

看空：
- {bear1}
- {bear2}

**🎯 价格目标**

| 入场区间 | 目标价 | 止损价 |
|---------|--------|--------|
| {entry_low} ~ {entry_high} | {target} (+{target_pct}%) | {stop_loss} (-{stop_pct}%) |

如适用，附"分批建仓表"：

| 价位 | 仓位 | 触发条件 |
|------|------|----------|
| {p1} | 20% | 第一击球点 |
| {p2} | 50% | 第二支撑确认 |
| {p3} | 80% | 极端低估区 |

---
```

### Signal Emoji Mapping (新)

| Signal | Emoji | Chinese | 总分区间 |
|--------|-------|---------|---------|
| strong_buy | 🟢 | 强烈买入 | 80-100 |
| buy | 🔵 | 买入 | 65-79 |
| hold | 🟡 | 持有 | 50-64 |
| wait | ⚪ | 观望 | 35-49 |
| sell | 🟠 | 卖出 | 20-34 |
| strong_sell | 🔴 | 强烈卖出 | <20 |

### Alignment Chinese Mapping

| English | Chinese |
|---------|---------|
| strong_bullish | 强势多头排列 |
| bullish | 多头排列 |
| weak_bullish | 弱多排列 |
| consolidation | 盘整 |
| weak_bearish | 弱空排列 |
| bearish | 空头排列 |
| strong_bearish | 强势空头排列 |

### MACD Signal Chinese Mapping

| English | Chinese |
|---------|---------|
| golden_cross_above_zero | 零轴上金叉 |
| golden_cross | 金叉 |
| crossing_above_zero | 上穿零轴 |
| bullish | 多头运行 |
| neutral | 中性 |
| bearish | 空头运行 |
| death_cross | 死叉 |
| crossing_below_zero | 下穿零轴 |

### Volume Trend Chinese Mapping

| English | Chinese |
|---------|---------|
| heavy_volume_up | 放量上涨 |
| heavy_volume_down | 放量下跌 |
| shrink_pullback | 缩量回调 |
| shrink_up | 缩量上涨 |
| normal | 正常 |

### RSI Zone Chinese Mapping

| English | Chinese |
|---------|---------|
| overbought | 超买 |
| strong | 强势 |
| neutral | 中性 |
| weak | 弱势 |
| oversold | 超卖 |

### Fundamental Rating Mapping

| Total | Rating |
|-------|--------|
| 24-30 | 优秀 |
| 18-23 | 良好 |
| 12-17 | 中等 |
| 6-11 | 偏弱 |
| 0-5 | 差 |

### Footer

```
> 免责声明: 以上分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。
> 数据来源: {data_source} (行情/基本面) / WebSearch (消息面) | 分析时间: {timestamp}
> 评分版本: 3D v2.0 (technical 50 + fundamental 30 + news 20)
```
