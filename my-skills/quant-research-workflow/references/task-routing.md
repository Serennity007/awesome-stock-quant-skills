# 按研究任务选 skill

以下均为本仓库 `my-skills/` 下的目录名。安装导航器不会自动安装这些 skill；只安装当前任务需要的目录。

| 任务 | 首选 | 继续深入 | 交付证据 |
|---|---|---|---|
| 判断公司质量与估值 | buffett-value-investing | munger-quality-investing、li-lu-value-compounding | 财务序列、分项分数、估值假设、人工护城河判断 |
| 找成长与动量候选 | lynch-garp-investing | oneil-canslim、fisher-growth-15 | 增长期间、PEG 口径、相对强度与基准日期 |
| 查低估与防御 | graham-defensive-investing | klarman-margin-safety、neff-low-pe-total-return | 估值分位窗口、分红期间、盈利与负债底线 |
| 找题材和概念关联 | hot-theme-scanner | concept-stock-mapper | 板块列表、成分与抓取日期；题材归属不等于收入暴露 |
| 看美股热门股 | us-hot-stocks-tracker | 需要深度财报时选择第三方美股分析 skill | 主题清单是静态配置，须核对最新业务与价格日期 |
| 看指数估值和配置 | bogle-index-investing | dalio-all-weather、howard-marks-cycle | 估值窗口、资产代理、相关性期间与配置假设 |
| 分析黄金与金银油运 | gold-cross-asset-research | 按具体市场补充官方事件、合约与 OHLC 数据 | 高低周期分工、结构触发/失效、跨资产反证；个人回顾不当作已验证战绩 |
| 对比多个框架 | master-ensemble | 回到入选框架定性复核 | 同池同日输入、百分位、覆盖数、输入哈希 |
| 检验历史表现 | framework-backtest | 样本外与成本敏感性需单独实施 | 明确固定池、120 天滞后近似和未建模的交易约束 |
| 识别技术形态 | technical-pattern-recognition | livermore-trend-trading | 复权方式、信号日、指标参数；信号不等于成交 |

## 三个常见请求

- “用巴菲特和芒格的方法看这几家公司”：选两个质量框架，对齐股票池，列出共同因子和不同扣分项；需要排序时再用 `master-ensemble`。
- “今天 AI 算力有什么热点”：先核对“今天”是否交易日，再跑热点与概念映射；新闻关联必须另查原始公告，不能从涨幅推断事件原因。
- “这个框架过去三年赚多少”：先读回测局限，再跑已有缓存或取数。固定当前股票池的结果只能作为探索，不能标为无偏历史业绩。
