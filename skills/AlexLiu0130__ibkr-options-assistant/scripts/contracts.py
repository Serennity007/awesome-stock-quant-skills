"""
IBKR 合约映射表 —— 所有 OpenClaw 金融脚本共用的"单一数据源"。

用法：
    from contracts import resolve, INDICES, SECTOR_ETFS, FUTURES, US_TICKERS, HK_TICKERS

    contract = resolve("^GSPC")        # → Index("SPX", "CBOE", "USD")
    contract = resolve("AAPL")         # → Stock("AAPL", "SMART", "USD")
    contract = resolve("0700.HK")      # → Stock("700", "SEHK", "HKD")
    contract = resolve("EURUSD")       # → Forex("EURUSD")

命名规则：
  - Yahoo 风格的 ^XXX 指数、XXX.HK 港股、USD/ZAR 汇率都能 resolve
  - 板块 ETF、资金流 ETF、期货、外汇都有固定 key，见各 dict
"""

from typing import Optional

from ib_async import ContFuture, Forex, Index, Option, Stock


# ─────────────────────────────────────────────────────────────
# 美股指数（CBOE Indices 订阅必须开）
# ─────────────────────────────────────────────────────────────
# Yahoo key → (IBKR symbol, exchange, 中文名, 是否为收益率指数)
INDICES: dict[str, tuple[str, str, str, str, bool]] = {
    "^GSPC":  ("SPX",   "CBOE",   "USD", "标普 500",    False),
    "^DJI":   ("INDU",  "CME",    "USD", "道琼斯",      False),
    "^IXIC":  ("COMP",  "NASDAQ", "USD", "纳斯达克综合", False),
    "^HSI":   ("HSI",   "HKFE",   "HKD", "恒生指数",    False),
    "^VIX":   ("VIX",   "CBOE",   "USD", "VIX 波动率",  False),
    # 美债收益率指数（数值单位 = %，不是价格）
    "^TNX":   ("TNX",   "CBOE",   "USD", "10Y 美债收益率", True),
    "^TYX":   ("TYX",   "CBOE",   "USD", "30Y 美债收益率", True),
    "^FVX":   ("FVX",   "CBOE",   "USD", "5Y 美债收益率",  True),
    "^IRX":   ("IRX",   "CBOE",   "USD", "13W 美债收益率", True),
}

# ─────────────────────────────────────────────────────────────
# 板块 ETF（美股 SMART 路由，delayed 免费）
# ─────────────────────────────────────────────────────────────
SECTOR_ETFS: dict[str, str] = {
    "XLK":  "科技",
    "XLF":  "金融",
    "XLY":  "非必需消费",
    "XLV":  "医疗",
    "XLE":  "能源",
    "XLU":  "公用事业",
    "XLI":  "工业",
    "XLP":  "必需消费",
    "XLB":  "材料",
    "XLRE": "房地产",
}

# 细分行业 ETF（日报用，比宽板块更精准地反映资金流向）
INDUSTRY_ETFS: dict[str, str] = {
    "SMH":  "半导体",
    "IGV":  "软件/SaaS",
    "HACK": "网络安全",
    "XBI":  "生物科技",
    "KRE":  "区域银行",
    "XHB":  "房屋建筑",
    "XRT":  "零售",
    "JETS": "航空",
    "OIH":  "油服",
    "ITA":  "国防/航空",
    "TAN":  "太阳能",
    "GDX":  "黄金矿业",
    "ARKK": "创新科技",
    "KWEB": "中概互联",
    "XME":  "金属/矿业",
}

# ─────────────────────────────────────────────────────────────
# 资金流 / 避险 / 信用 ETF
# ─────────────────────────────────────────────────────────────
MARKET_ETFS: dict[str, str] = {
    "SPY": "标普 ETF",
    "QQQ": "纳指 ETF",
    "IWM": "小盘股 ETF",
}
SAFE_HAVEN_ETFS: dict[str, str] = {
    "TLT": "长债 ETF(20Y)",
    "GLD": "黄金 ETF",
}
CREDIT_ETFS: dict[str, str] = {
    "HYG": "高收益债 ETF",
    "LQD": "投资级债 ETF",
}

# ─────────────────────────────────────────────────────────────
# 国际股指 ETF（avoid 开多国交易所订阅）
# ─────────────────────────────────────────────────────────────
INTL_ETFS: dict[str, str] = {
    "EWJ":  "日本 iShares",
    "EWG":  "德国 iShares",
    "EWU":  "英国 iShares",
    "MCHI": "中国 iShares",
    "INDA": "印度 iShares",
    "EWZ":  "巴西 iShares",
}

# ─────────────────────────────────────────────────────────────
# 期货连续合约（各交易所订阅必须开）
# ─────────────────────────────────────────────────────────────
# key → (IBKR symbol, exchange, 中文名)
FUTURES: dict[str, tuple[str, str, str]] = {
    "VX": ("VIX", "CFE",   "VIX 波动率期货"),
    "ES": ("ES",  "CME",   "标普期货"),
    "NQ": ("NQ",  "CME",   "纳指期货"),
    "ZN": ("ZN",  "CBOT",  "10Y 美债期货"),
    "CL": ("CL",  "NYMEX", "WTI 原油"),
    "GC": ("GC",  "COMEX", "黄金"),
    "SI": ("SI",  "COMEX", "白银"),
}

# ─────────────────────────────────────────────────────────────
# 外汇（IDEALPRO 免费）
# ─────────────────────────────────────────────────────────────
FX_PAIRS: list[str] = [
    "EURUSD",
    "USDJPY",
    "GBPUSD",
    "USDCNH",
    "AUDUSD",
]

# ─────────────────────────────────────────────────────────────
# 股票清单（从旧 fetch_top_movers.py 迁移）
# ─────────────────────────────────────────────────────────────
US_TICKERS: list[str] = [
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "BRK B",
    "UNH", "XOM", "JNJ", "JPM", "V", "PG", "MA", "AVGO", "HD", "CVX",
    "MRK", "ABBV", "LLY", "COST", "PEP", "KO", "WMT", "BAC", "MCD",
    "TMO", "CSCO", "CRM", "ACN", "ABT", "DHR", "ADBE", "TXN", "NFLX",
    "CMCSA", "AMD", "PM", "NEE", "WFC", "INTC", "UNP", "RTX", "ORCL",
    "IBM", "QCOM", "LOW", "INTU", "SPGI", "GE", "AMAT", "ISRG", "CAT",
    "BLK", "AXP", "BKNG", "SYK", "MDLZ", "ADI", "GILD", "VRTX",
    "MMC", "LRCX", "DE", "ADP", "AMT", "REGN", "GS", "CB", "SCHW",
    "PANW", "MU", "KLAC", "SHW", "FI", "SNPS", "CDNS", "ICE", "BSX",
    "SO", "DUK", "CME", "CL", "MCO", "PGR", "APD", "EQIX", "TJX",
    "NOC", "EMR", "USB", "PNC", "ABNB", "MELI", "FTNT", "CRWD",
    "PYPL", "UBER", "COIN", "RIVN", "PLTR", "SNOW", "DDOG", "ZS",
    "NET", "ARM", "SMCI", "MRVL", "ON", "ENPH", "FSLR", "SEDG",
    "NKE", "DIS", "SBUX", "F", "GM", "UAL", "DAL", "LUV",
    "PFE", "BMY", "MRNA", "BIIB",
]
# BRK-B 在 IBKR 用空格（BRK B）

# 港股（旧脚本 .HK 格式 → IBKR 去掉前导 0 的 local symbol）
# IBKR 港股接受的 symbol 是去前导 0 的数字，如 "700"、"9988"
HK_TICKERS_YAHOO: list[str] = [
    "0700.HK", "9988.HK", "9618.HK", "3690.HK", "9999.HK",
    "1810.HK", "2382.HK", "0992.HK", "6690.HK", "0268.HK",
    "1211.HK", "0175.HK", "2015.HK", "0968.HK",
    "0005.HK", "0388.HK", "2318.HK", "2628.HK", "1299.HK", "3988.HK",
    "2020.HK", "9961.HK", "6862.HK", "0291.HK",
    "0883.HK", "0857.HK", "1088.HK",
    "0016.HK", "0001.HK", "0003.HK",
    "1177.HK", "6160.HK",
    "0027.HK", "1928.HK",
    "0941.HK", "0762.HK",
]

# 中文公司名（从旧 fetch_top_movers.py 迁）
COMPANY_NAMES: dict[str, str] = {
    # 美股
    "AAPL": "苹果", "MSFT": "微软", "AMZN": "亚马逊", "NVDA": "英伟达",
    "GOOGL": "谷歌", "META": "Meta", "TSLA": "特斯拉", "BRK B": "伯克希尔",
    "UNH": "联合健康", "XOM": "埃克森美孚", "JNJ": "强生", "JPM": "摩根大通",
    "V": "Visa", "PG": "宝洁", "MA": "万事达", "AVGO": "博通",
    "HD": "家得宝", "CVX": "雪佛龙", "MRK": "默沙东", "ABBV": "艾伯维",
    "LLY": "礼来", "COST": "Costco", "PEP": "百事", "KO": "可口可乐",
    "WMT": "沃尔玛", "BAC": "美国银行", "MCD": "麦当劳", "NFLX": "Netflix",
    "AMD": "AMD", "INTC": "英特尔", "QCOM": "高通", "ORCL": "甲骨文",
    "CRM": "Salesforce", "ADBE": "Adobe", "INTU": "Intuit",
    "GS": "高盛", "SCHW": "嘉信理财",
    "NKE": "耐克", "DIS": "迪士尼", "SBUX": "星巴克",
    "PFE": "辉瑞", "BMY": "百时美施贵宝", "MRNA": "Moderna",
    "F": "福特", "GM": "通用汽车", "UBER": "Uber",
    "COIN": "Coinbase", "PLTR": "Palantir", "SNOW": "Snowflake",
    "CRWD": "CrowdStrike", "PANW": "Palo Alto", "ARM": "Arm",
    "SMCI": "超微电脑", "MRVL": "Marvell", "MU": "美光",
    "PYPL": "PayPal", "ABNB": "Airbnb", "MELI": "MercadoLibre",
    "RIVN": "Rivian", "ENPH": "Enphase", "FSLR": "First Solar",
    "NET": "Cloudflare", "DDOG": "Datadog", "ZS": "Zscaler",
    # 港股（用 Yahoo key 查询更稳，resolve 时会转换）
    "9988.HK": "阿里巴巴", "0700.HK": "腾讯", "3690.HK": "美团",
    "9618.HK": "京东", "1211.HK": "比亚迪", "2020.HK": "安踏",
    "9999.HK": "网易", "0941.HK": "中国移动", "1810.HK": "小米",
    "2318.HK": "中国平安", "0005.HK": "汇丰", "0388.HK": "港交所",
    "2628.HK": "中国人寿", "0003.HK": "中华煤气", "1299.HK": "友邦保险",
    "0883.HK": "中海油", "0016.HK": "新鸿基", "0027.HK": "银河娱乐",
    "2382.HK": "舜宇光学", "0968.HK": "信义光能", "0992.HK": "联想",
    "6690.HK": "海尔智家", "0268.HK": "金蝶国际", "0175.HK": "吉利汽车",
    "2015.HK": "理想汽车", "3988.HK": "中国银行", "9961.HK": "携程",
    "6862.HK": "海底捞", "0291.HK": "华润啤酒", "0857.HK": "中石油",
    "1088.HK": "中国神华", "0001.HK": "长和", "1177.HK": "中国生物制药",
    "6160.HK": "百济神州", "1928.HK": "金沙中国", "0762.HK": "中国联通",
}


# ─────────────────────────────────────────────────────────────
# 解析函数
# ─────────────────────────────────────────────────────────────

def _hk_yahoo_to_ibkr(yahoo_code: str) -> str:
    """'0700.HK' → '700'（IBKR 港股 symbol 去前导 0）"""
    return yahoo_code.split(".")[0].lstrip("0") or "0"


# 个别美股在 IBKR 里 ticker/primaryExchange 与 Yahoo 不一致（歧义/老代码）
# Yahoo ticker → (IBKR symbol, primaryExchange)
US_TICKER_ALIASES: dict[str, tuple[str, str]] = {
    "MMC": ("MRSH", "NYSE"),   # Marsh & McLennan：IBKR 仍挂老 ticker MRSH (conId 9705)
    "FI":  ("FISV", "NASDAQ"), # Fiserv：Yahoo 改名 FI，IBKR 仍是 FISV (conId 269315)
}


def us_stock(ticker: str):
    """构造美股 Stock，处理 IBKR 老 ticker / 模糊歧义。"""
    t = ticker.strip().upper()
    if t in US_TICKER_ALIASES:
        sym, primary = US_TICKER_ALIASES[t]
        return Stock(sym, "SMART", "USD", primaryExchange=primary)
    return Stock(t, "SMART", "USD")


def resolve(symbol: str):
    """把任意代码映射成 ib_async Contract。

    支持：
      - Yahoo 指数  ^GSPC / ^TNX / ^VIX
      - Yahoo 港股  0700.HK
      - 外汇       EURUSD / USD/ZAR / GBP-JPY（统一成 6 字符无分隔）
      - 期货 key   ES / NQ / VX (从 FUTURES dict)
      - 其他       视为美股 SMART 路由
    """
    sym = symbol.strip().upper()

    # 1. 指数
    if sym in INDICES:
        ibkr_sym, exchange, currency, _, _ = INDICES[sym]
        return Index(ibkr_sym, exchange, currency)

    # 2. 港股
    if sym.endswith(".HK"):
        return Stock(_hk_yahoo_to_ibkr(sym), "SEHK", "HKD")

    # 3. 期货连续合约
    if sym in FUTURES:
        ibkr_sym, exchange, _ = FUTURES[sym]
        return ContFuture(ibkr_sym, exchange)

    # 4. 外汇（USDJPY / USD/JPY / USD-JPY 都接受）
    fx_norm = sym.replace("/", "").replace("-", "")
    if len(fx_norm) == 6 and fx_norm.isalpha():
        return Forex(fx_norm)

    # 5. 美元指数（Yahoo: DX-Y.NYB）
    if sym in ("DX-Y.NYB", "DXY", "DX"):
        # NYBOT 的美元指数期货连续合约（现货 IND 未在 IBKR 免费列表）
        return ContFuture("DX", "NYBOT")

    # 6. 默认当美股
    return Stock(sym, "SMART", "USD")


def company_name(symbol: str) -> str:
    """返回中文公司名，没有则返回原 symbol。"""
    return COMPANY_NAMES.get(symbol.upper(), symbol)
