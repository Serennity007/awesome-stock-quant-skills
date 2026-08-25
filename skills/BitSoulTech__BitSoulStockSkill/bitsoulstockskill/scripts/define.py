import os
import json
from typing import Optional
import utils
import config

def _load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"base_url": "", "http_timeout": 30}

_config = _load_config()

# ============================================================
# 常量
# ============================================================

BASE_URL = _config.get("base_url", "")
HTTP_TIMEOUT = _config.get("http_timeout", 30)
DB_PATH = os.path.join(config.get_cache_dir(), "data.db")

def get_cache_dir() -> str:
    return config.get_cache_dir()

# ============================================================
# 数据模型
# ============================================================

class RealtimeStockQuote:
    """
    实时股票报价信息

    字段说明:
        ts_code       股票代码（如 000001.SZ）
        name          股票名称
        open          今日开盘价
        pre_close     昨日收盘价
        price         当前最新价
        high          今日最高价
        low           今日最低价
        bid           买一价
        ask           卖一价
        volume        成交量（股）
        amount        成交额（元）
        date          交易日期（YYYY-MM-DD）
        time          最新报价时间（HH:MM:SS）
        amplitude     振幅（%）
        turnover_rate 换手率（%），可能为空
        total_cap     总市值（元），可能为空
        circ_cap      流通市值（元），可能为空
        pb            市净率，可能为空
        pe_ttm        市盈率（TTM），可能为空
        total_shares  总股本（股），可能为空
        circ_shares   流通股本（股），可能为空
        status        请求状态（success / error）
    """

    __slots__ = ("ts_code", "name", "open", "pre_close", "price",
                 "high", "low", "bid", "ask", "volume", "amount",
                 "date", "time", "amplitude", "turnover_rate",
                 "total_cap", "circ_cap", "pb", "pe_ttm",
                 "total_shares", "circ_shares", "status")

    def __init__(self, ts_code: str, name: str, open: float, pre_close: float,
                 price: float, high: float, low: float, bid: float, ask: float,
                 volume: int, amount: float, date: str, time: str,
                 amplitude: float, turnover_rate: Optional[float],
                 total_cap: Optional[float], circ_cap: Optional[float],
                 pb: Optional[float], pe_ttm: Optional[float],
                 total_shares: Optional[float], circ_shares: Optional[float],
                 status: str):
        self.ts_code = ts_code
        self.name = name
        self.open = open
        self.pre_close = pre_close
        self.price = price
        self.high = high
        self.low = low
        self.bid = bid
        self.ask = ask
        self.volume = volume
        self.amount = amount
        self.date = date
        self.time = time
        self.amplitude = amplitude
        self.turnover_rate = turnover_rate
        self.total_cap = total_cap
        self.circ_cap = circ_cap
        self.pb = pb
        self.pe_ttm = pe_ttm
        self.total_shares = total_shares
        self.circ_shares = circ_shares
        self.status = status

    @classmethod
    def from_dict(cls, d: dict) -> "RealtimeStockQuote":
        def _f(v):
            try:
                return float(v) if v is not None and v != "" else None
            except (TypeError, ValueError):
                return None

        return cls(
            ts_code=d.get("ts_code") or "",
            name=d.get("name") or "",
            open=float(d.get("open") or 0.0),
            pre_close=float(d.get("pre_close") or 0.0),
            price=float(d.get("price") or 0.0),
            high=float(d.get("high") or 0.0),
            low=float(d.get("low") or 0.0),
            bid=float(d.get("bid") or 0.0),
            ask=float(d.get("ask") or 0.0),
            volume=int(d.get("volume") or 0),
            amount=float(d.get("amount") or 0.0),
            date=d.get("date") or "",
            time=d.get("time") or "",
            amplitude=float(d.get("amplitude") or 0.0),
            turnover_rate=_f(d.get("turnover_rate")),
            total_cap=_f(d.get("total_cap")),
            circ_cap=_f(d.get("circ_cap")),
            pb=_f(d.get("pb")),
            pe_ttm=_f(d.get("pe_ttm")),
            total_shares=_f(d.get("total_shares")),
            circ_shares=_f(d.get("circ_shares")),
            status=d.get("status") or "",
        )

    def __repr__(self) -> str:
        return (f"RealtimeStockQuote(ts_code={self.ts_code!r}, name={self.name!r}, "
                f"price={self.price}, date={self.date!r})")

class StockBasic:
    """
    股票基础信息，对应远程 stock_basic 表及本地同名表。

    字段说明:
        ts_code     股票代码，如 000001.SZ
        symbol      股票符号，如 000001
        name        股票名称，如 平安银行
        area        所在地区
        industry    所属行业
        fullname    股票全称
        enname      英文名称
        cnspell     拼音
        market      市场类型（主板/创业板/科创板等）
        exchange    交易所代码
        curr_type   交易货币
        list_date   上市日期，格式 YYYY-MM-DD
        list_status 上市状态 (L=上市, D=退市, G=过会未交易, P=暂停上市)
        delist_date 退市日期（未退市则为空），格式 YYYY-MM-DD
        is_hs       是否沪深港通标的（N=否, H=沪股通, S=深股通）
    """

    __slots__ = ("ts_code", "symbol", "name", "area", "industry",
                 "fullname", "enname", "cnspell", "market", "exchange",
                 "curr_type", "list_date", "list_status", "delist_date", "is_hs")

    def __init__(self, ts_code: str, symbol: str, name: str,
                 area: str, industry: str, fullname: str, enname: str,
                 cnspell: str, market: str, exchange: str, curr_type: str,
                 list_date: str, list_status:str, delist_date: str, is_hs: str):
        self.ts_code = ts_code
        self.symbol = symbol
        self.name = name
        self.area = area
        self.industry = industry
        self.fullname = fullname
        self.enname = enname
        self.cnspell = cnspell
        self.market = market
        self.exchange = exchange
        self.curr_type = curr_type
        self.list_date = list_date
        self.list_status = list_status
        self.delist_date = delist_date
        self.is_hs = is_hs

    @classmethod
    def from_dict(cls, d: dict) -> "StockBasic":
        """从字典（API 响应或数据库行）构造 StockBasic 对象。"""
        return cls(
            ts_code=d.get("ts_code") or "",
            symbol=d.get("symbol") or "",
            name=d.get("name") or "",
            area=d.get("area") or "",
            industry=d.get("industry") or "",
            fullname=d.get("fullname") or "",
            enname=d.get("enname") or "",
            cnspell=d.get("cnspell") or "",
            market=d.get("market") or "",
            exchange=d.get("exchange") or "",
            curr_type=d.get("curr_type") or "",
            list_date=d.get("list_date") or "",
            list_status=d.get("list_status") or "",
            delist_date=d.get("delist_date") or "",
            is_hs=d.get("is_hs") or "",
        )

    def __repr__(self) -> str:
        return f"StockBasic(ts_code={self.ts_code!r}, name={self.name!r}, market={self.market!r})"


class DailyKline:
    """
    日线行情数据，对应远程 daily_kline 表及本地同名表。

    字段说明:
        date        交易日期，格式 YYYY-MM-DD
        code        股票代码，如 sz.000001
        open        开盘价
        high        最高价
        low         最低价
        close       收盘价
        volume      成交量（股）
        amount      成交额（元）
        adjustflag  复权状态
        turn        换手率
        pctChg      涨跌幅（%）
        pre_close   前收盘价
        change      涨跌额
    """

    __slots__ = ("date", "code", "open", "high", "low", "close",
                 "volume", "amount", "adjustflag", "turn", "pctChg",
                 "pre_close", "change")

    def __init__(self, date: str, code: str, open: float, high: float,
                 low: float, close: float, volume: float, amount: float,
                 adjustflag: str, turn: float, pctChg: float,
                 pre_close: float, change: float):
        self.date = date
        self.code = code
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.amount = amount
        self.adjustflag = adjustflag
        self.turn = turn
        self.pctChg = pctChg
        self.pre_close = pre_close
        self.change = change

    @classmethod
    def from_dict(cls, d: dict) -> "DailyKline":
        """从字典（API 响应或数据库行）构造 DailyKline 对象。"""
        def _f(v):
            """将值安全转换为 float，None/空字符串返回 0.0。"""
            try:
                return float(v) if v is not None and v != "" else 0.0
            except (TypeError, ValueError):
                return 0.0

        return cls(
            date=d.get("date") or "",
            code=d.get("code") or "",
            open=_f(d.get("open")),
            high=_f(d.get("high")),
            low=_f(d.get("low")),
            close=_f(d.get("close")),
            volume=_f(d.get("volume")),
            amount=_f(d.get("amount")),
            adjustflag=d.get("adjustflag") or "",
            turn=_f(d.get("turn")),
            pctChg=_f(d.get("pctChg")),
            pre_close=_f(d.get("pre_close")),
            change=_f(d.get("change")),
        )

    def __repr__(self) -> str:
        return (f"DailyKline(date={self.date!r}, code={self.code!r}, "
                f"close={self.close}, pctChg={self.pctChg})")


class HourKline:
    """
    小时级别 K 线行情数据，对应本地 hour_kline 表。

    字段说明:
        date    交易日期,格式 "YYYY-MM-DD"
        time    交易时间
        open    开盘价
        high    最高价
        low     最低价
        close   收盘价
        volume  成交量
        amount  成交额
        code    股票代码
    """

    __slots__ = ("date", "time", "open", "high", "low", "close",
                 "volume", "amount", "code")

    def __init__(self, date: str, time: str, open: float, high: float,
                 low: float, close: float, volume: float, amount: float,
                 code: str):
        self.date = date
        self.time = time
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.amount = amount
        self.code = code

    @classmethod
    def from_dict(cls, d: dict) -> "HourKline":
        def _f(v):
            try:
                return float(v) if v is not None and v != "" else 0.0
            except (TypeError, ValueError):
                return 0.0

        return cls(
            date=d.get("date") or "",
            time=d.get("time") or "",
            open=_f(d.get("open")),
            high=_f(d.get("high")),
            low=_f(d.get("low")),
            close=_f(d.get("close")),
            volume=_f(d.get("volume")),
            amount=_f(d.get("amount")),
            code=d.get("code") or "",
        )

    def __repr__(self) -> str:
        return (f"HourKline(date={self.date!r}, time={self.time!r}, "
                f"code={self.code!r}, close={self.close})")


class WeeklyKline:
    """
    周线行情数据，对应本地 weekly_kline 表。

    字段说明:
        date    交易日期（周五日期），格式 YYYY-MM-DD
        code    股票代码
        open    开盘价
        high    最高价
        low     最低价
        close   收盘价
        volume  成交量
        amount  成交额
        pctChg  涨跌幅（%）
    """

    __slots__ = ("date", "code", "open", "high", "low", "close",
                 "volume", "amount", "pctChg")

    def __init__(self, date: str, code: str, open: float, high: float,
                 low: float, close: float, volume: float, amount: float,
                 pctChg: float):
        self.date = date
        self.code = code
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.amount = amount
        self.pctChg = pctChg

    @classmethod
    def from_dict(cls, d: dict) -> "WeeklyKline":
        def _f(v):
            try:
                return float(v) if v is not None and v != "" else 0.0
            except (TypeError, ValueError):
                return 0.0

        return cls(
            date=d.get("date") or "",
            code=d.get("code") or "",
            open=_f(d.get("open")),
            high=_f(d.get("high")),
            low=_f(d.get("low")),
            close=_f(d.get("close")),
            volume=_f(d.get("volume")),
            amount=_f(d.get("amount")),
            pctChg=_f(d.get("pctChg")),
        )

    def __repr__(self) -> str:
        return (f"WeeklyKline(date={self.date!r}, code={self.code!r}, "
                f"close={self.close}, pctChg={self.pctChg})")


class MonthlyKline:
    """
    月线行情数据，对应本地 monthly_kline 表。

    字段说明:
        date    交易日期（月末日期），格式 YYYY-MM-DD
        code    股票代码
        open    开盘价
        high    最高价
        low     最低价
        close   收盘价
        volume  成交量
        amount  成交额
        pctChg  涨跌幅（%）
    """

    __slots__ = ("date", "code", "open", "high", "low", "close",
                 "volume", "amount", "pctChg")

    def __init__(self, date: str, code: str, open: float, high: float,
                 low: float, close: float, volume: float, amount: float,
                 pctChg: float):
        self.date = date
        self.code = code
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.amount = amount
        self.pctChg = pctChg

    @classmethod
    def from_dict(cls, d: dict) -> "MonthlyKline":
        def _f(v):
            try:
                return float(v) if v is not None and v != "" else 0.0
            except (TypeError, ValueError):
                return 0.0

        return cls(
            date=d.get("date") or "",
            code=d.get("code") or "",
            open=_f(d.get("open")),
            high=_f(d.get("high")),
            low=_f(d.get("low")),
            close=_f(d.get("close")),
            volume=_f(d.get("volume")),
            amount=_f(d.get("amount")),
            pctChg=_f(d.get("pctChg")),
        )

    def __repr__(self) -> str:
        return (f"MonthlyKline(date={self.date!r}, code={self.code!r}, "
                f"close={self.close}, pctChg={self.pctChg})")


class DailyBasic:
    """
    每日基本面指标数据，对应本地 daily_basic 表。

    字段说明:
        trade_date      交易日期（PK），格式 YYYY-MM-DD
        ts_code         股票代码（PK）
        close           当日收盘价
        turnover_rate   换手率（%）
        turnover_rate_f 换手率（自由流通股）
        volume_ratio    量比
        pe              市盈率（总市值/净利润）
        pe_ttm          市盈率（TTM）
        pb              市净率（总市值/净资产）
        ps              市销率
        ps_ttm          市销率（TTM）
        dv_ratio        股息率（%）
        dv_ttm          股息率（TTM）（%）
        total_share     总股本（万股）
        float_share     流通股本（万股）
        free_share      自由流通股本（万）
        total_mv        总市值（万元）
        circ_mv         流通市值（万元）
        adj_factor      复权因子
    """

    __slots__ = ("trade_date", "ts_code", "close", "turnover_rate",
                 "turnover_rate_f", "volume_ratio", "pe", "pe_ttm",
                 "pb", "ps", "ps_ttm", "dv_ratio", "dv_ttm",
                 "total_share", "float_share", "free_share",
                 "total_mv", "circ_mv", "adj_factor")

    def __init__(self, trade_date: str, ts_code: str, close: float,
                 turnover_rate: float, turnover_rate_f: float, volume_ratio: float,
                 pe: float, pe_ttm: float, pb: float, ps: float, ps_ttm: float,
                 dv_ratio: float, dv_ttm: float, total_share: float,
                 float_share: float, free_share: float, total_mv: float,
                 circ_mv: float, adj_factor: float):
        self.trade_date = trade_date
        self.ts_code = ts_code
        self.close = close
        self.turnover_rate = turnover_rate
        self.turnover_rate_f = turnover_rate_f
        self.volume_ratio = volume_ratio
        self.pe = pe
        self.pe_ttm = pe_ttm
        self.pb = pb
        self.ps = ps
        self.ps_ttm = ps_ttm
        self.dv_ratio = dv_ratio
        self.dv_ttm = dv_ttm
        self.total_share = total_share
        self.float_share = float_share
        self.free_share = free_share
        self.total_mv = total_mv
        self.circ_mv = circ_mv
        self.adj_factor = adj_factor

    @classmethod
    def from_dict(cls, d: dict) -> "DailyBasic":
        def _f(v):
            try:
                return float(v) if v is not None and v != "" else 0.0
            except (TypeError, ValueError):
                return 0.0

        return cls(
            trade_date=d.get("trade_date") or "",
            ts_code=d.get("ts_code") or "",
            close=_f(d.get("close")),
            turnover_rate=_f(d.get("turnover_rate")),
            turnover_rate_f=_f(d.get("turnover_rate_f")),
            volume_ratio=_f(d.get("volume_ratio")),
            pe=_f(d.get("pe")),
            pe_ttm=_f(d.get("pe_ttm")),
            pb=_f(d.get("pb")),
            ps=_f(d.get("ps")),
            ps_ttm=_f(d.get("ps_ttm")),
            dv_ratio=_f(d.get("dv_ratio")),
            dv_ttm=_f(d.get("dv_ttm")),
            total_share=_f(d.get("total_share")),
            float_share=_f(d.get("float_share")),
            free_share=_f(d.get("free_share")),
            total_mv=_f(d.get("total_mv")),
            circ_mv=_f(d.get("circ_mv")),
            adj_factor=_f(d.get("adj_factor")),
        )

    def __repr__(self) -> str:
        return (f"DailyBasic(trade_date={self.trade_date!r}, ts_code={self.ts_code!r}, "
                f"close={self.close}, pe={self.pe}, pb={self.pb})")


class Income:
    """
    利润表数据，对应本地 income 表。

    字段说明:
        ts_code           股票代码（PK）
        end_date          报告期结束日期（PK），格式 YYYY-MM-DD
        ann_date          公告日期，格式 YYYY-MM-DD
        report_type       报告类型（PK，1=合并报表）
        comp_type         公司类型
        basic_eps         基本每股收益
        diluted_eps       稀释每股收益
        total_revenue     营业总收入
        revenue           营业收入
        total_cogs        营业总成本
        oper_cost         营业成本
        sell_exp          销售费用
        admin_exp         管理费用
        fin_exp           财务费用
        total_profit      利润总额
        income_tax        所得税费用
        n_income          净利润
        n_income_attr_p   归属于母公司所有者的净利润
        minority_gain     少数股东损益
        oth_compr_income  其他综合收益
        t_compr_income    综合收益总额
        compr_inc_attr_p  归属于母公司所有者的综合收益总额
        ebit              息税前利润
        ebitda            息税折旧摊销前利润
        roe               净资产收益率（%）
        roa               总资产收益率（%）
        gross_margin      毛利率（%）
        net_profit_margin 净利率（%）
        net_profit_yoy    净利润增长率（%）
        revenue_yoy       营业收入增长率（%）
        equity_yoy        净资产增长率（%）
        pcf               市现率
        free_circ_mv      自由流通市值
    """

    __slots__ = (
        "ts_code", "end_date", "ann_date", "report_type", "comp_type",
        "basic_eps", "diluted_eps", "total_revenue", "revenue",
        "total_cogs", "oper_cost", "sell_exp", "admin_exp", "fin_exp",
        "total_profit", "income_tax", "n_income", "n_income_attr_p",
        "minority_gain", "oth_compr_income", "t_compr_income", "compr_inc_attr_p",
        "ebit", "ebitda", "roe", "roa", "gross_margin", "net_profit_margin",
        "net_profit_yoy", "revenue_yoy", "equity_yoy", "pcf", "free_circ_mv",
    )

    def __init__(
        self,
        ts_code: str, end_date: str, report_type: str, ann_date: str, comp_type: str,
        basic_eps: float, diluted_eps: float, total_revenue: float, revenue: float,
        total_cogs: float, oper_cost: float, sell_exp: float, admin_exp: float, fin_exp: float,
        total_profit: float, income_tax: float, n_income: float, n_income_attr_p: float,
        minority_gain: float, oth_compr_income: float, t_compr_income: float, compr_inc_attr_p: float,
        ebit: float, ebitda: float, roe: float, roa: float, gross_margin: float,
        net_profit_margin: float, net_profit_yoy: float, revenue_yoy: float,
        equity_yoy: float, pcf: float, free_circ_mv: float,
    ):
        self.ts_code = ts_code
        self.end_date = end_date
        self.report_type = report_type
        self.ann_date = ann_date
        self.comp_type = comp_type
        self.basic_eps = basic_eps
        self.diluted_eps = diluted_eps
        self.total_revenue = total_revenue
        self.revenue = revenue
        self.total_cogs = total_cogs
        self.oper_cost = oper_cost
        self.sell_exp = sell_exp
        self.admin_exp = admin_exp
        self.fin_exp = fin_exp
        self.total_profit = total_profit
        self.income_tax = income_tax
        self.n_income = n_income
        self.n_income_attr_p = n_income_attr_p
        self.minority_gain = minority_gain
        self.oth_compr_income = oth_compr_income
        self.t_compr_income = t_compr_income
        self.compr_inc_attr_p = compr_inc_attr_p
        self.ebit = ebit
        self.ebitda = ebitda
        self.roe = roe
        self.roa = roa
        self.gross_margin = gross_margin
        self.net_profit_margin = net_profit_margin
        self.net_profit_yoy = net_profit_yoy
        self.revenue_yoy = revenue_yoy
        self.equity_yoy = equity_yoy
        self.pcf = pcf
        self.free_circ_mv = free_circ_mv

    @classmethod
    def from_dict(cls, d: dict) -> "Income":
        """从字典（数据库行）构造 Income 对象。"""
        def _f(v):
            try:
                return float(v) if v is not None and v != "" else 0.0
            except (TypeError, ValueError):
                return 0.0

        return cls(
            ts_code=d.get("ts_code") or "",
            end_date=d.get("end_date") or "",
            report_type=d.get("report_type") or "",
            ann_date=d.get("ann_date") or "",
            comp_type=d.get("comp_type") or "",
            basic_eps=_f(d.get("basic_eps")),
            diluted_eps=_f(d.get("diluted_eps")),
            total_revenue=_f(d.get("total_revenue")),
            revenue=_f(d.get("revenue")),
            total_cogs=_f(d.get("total_cogs")),
            oper_cost=_f(d.get("oper_cost")),
            sell_exp=_f(d.get("sell_exp")),
            admin_exp=_f(d.get("admin_exp")),
            fin_exp=_f(d.get("fin_exp")),
            total_profit=_f(d.get("total_profit")),
            income_tax=_f(d.get("income_tax")),
            n_income=_f(d.get("n_income")),
            n_income_attr_p=_f(d.get("n_income_attr_p")),
            minority_gain=_f(d.get("minority_gain")),
            oth_compr_income=_f(d.get("oth_compr_income")),
            t_compr_income=_f(d.get("t_compr_income")),
            compr_inc_attr_p=_f(d.get("compr_inc_attr_p")),
            ebit=_f(d.get("ebit")),
            ebitda=_f(d.get("ebitda")),
            roe=_f(d.get("roe")),
            roa=_f(d.get("roa")),
            gross_margin=_f(d.get("gross_margin")),
            net_profit_margin=_f(d.get("net_profit_margin")),
            net_profit_yoy=_f(d.get("net_profit_yoy")),
            revenue_yoy=_f(d.get("revenue_yoy")),
            equity_yoy=_f(d.get("equity_yoy")),
            pcf=_f(d.get("pcf")),
            free_circ_mv=_f(d.get("free_circ_mv")),
        )

    def __repr__(self) -> str:
        return (f"Income(ts_code={self.ts_code!r}, end_date={self.end_date!r}, "
                f"report_type={self.report_type!r}, n_income={self.n_income})")


class StockLimit:
    """
    每日涨跌停价格数据，对应本地 stock_limit 表。

    字段说明:
        trade_date  交易日期（PK），格式 YYYY-MM-DD
        ts_code     股票代码（PK）
        pre_close   昨日收盘价
        up_limit    涨停价
        down_limit  跌停价
    """

    __slots__ = ("trade_date", "ts_code", "pre_close", "up_limit", "down_limit")

    def __init__(self, trade_date: str, ts_code: str,
                 pre_close: float, up_limit: float, down_limit: float):
        self.trade_date = trade_date
        self.ts_code = ts_code
        self.pre_close = pre_close
        self.up_limit = up_limit
        self.down_limit = down_limit

    @classmethod
    def from_dict(cls, d: dict) -> "StockLimit":
        def _f(v):
            try:
                return float(v) if v is not None and v != "" else 0.0
            except (TypeError, ValueError):
                return 0.0

        return cls(
            trade_date=d.get("trade_date") or "",
            ts_code=d.get("ts_code") or "",
            pre_close=_f(d.get("pre_close")),
            up_limit=_f(d.get("up_limit")),
            down_limit=_f(d.get("down_limit")),
        )

    def __repr__(self) -> str:
        return (f"StockLimit(trade_date={self.trade_date!r}, ts_code={self.ts_code!r}, "
                f"up_limit={self.up_limit}, down_limit={self.down_limit})")


class DailyLimitList:
    """
    每日涨跌停榜单数据，对应本地 daily_limit_list 表。

    字段说明:
        trade_date   交易日期（PK），格式 YYYY-MM-DD
        ts_code      股票代码（PK）
        name         股票名称
        limit_type   榜单类型（U=涨停, D=跌停）
        limit_price  涨跌停价格
        pct_chg      涨跌幅（%）
        volume       成交量
        amount       成交额
        limit_streak 连板数（涨停板）
        sector       所属板块
    """

    __slots__ = ("trade_date", "ts_code", "name", "limit_type", "limit_price",
                 "pct_chg", "volume", "amount", "limit_streak", "sector")

    def __init__(self, trade_date: str, ts_code: str, name: str, limit_type: str,
                 limit_price: float, pct_chg: float, volume: float, amount: float,
                 limit_streak: int, sector: str):
        self.trade_date = trade_date
        self.ts_code = ts_code
        self.name = name
        self.limit_type = limit_type
        self.limit_price = limit_price
        self.pct_chg = pct_chg
        self.volume = volume
        self.amount = amount
        self.limit_streak = limit_streak
        self.sector = sector

    @classmethod
    def from_dict(cls, d: dict) -> "DailyLimitList":
        def _f(v):
            try:
                return float(v) if v is not None and v != "" else 0.0
            except (TypeError, ValueError):
                return 0.0

        def _i(v):
            try:
                return int(v) if v is not None and v != "" else 0
            except (TypeError, ValueError):
                return 0

        return cls(
            trade_date=d.get("trade_date") or "",
            ts_code=d.get("ts_code") or "",
            name=d.get("name") or "",
            limit_type=d.get("limit_type") or "",
            limit_price=_f(d.get("limit_price")),
            pct_chg=_f(d.get("pct_chg")),
            volume=_f(d.get("volume")),
            amount=_f(d.get("amount")),
            limit_streak=_i(d.get("limit_streak")),
            sector=d.get("sector") or "",
        )

    def __repr__(self) -> str:
        return (f"DailyLimitList(trade_date={self.trade_date!r}, ts_code={self.ts_code!r}, "
                f"name={self.name!r}, limit_type={self.limit_type!r}, limit_streak={self.limit_streak})")


class SectorStockMap:
    """
    板块成分股映射表，对应本地 sector_stock_map 表。

    字段说明:
        sector_code  板块代码（PK）
        stock_code   股票代码（PK）
        sector_name  板块名称（冗余字段）
        source       数据来源
    """

    __slots__ = ("sector_code", "stock_code", "sector_name", "source")

    def __init__(self, sector_code: str, stock_code: str, sector_name: str, source: str):
        self.sector_code = sector_code
        self.stock_code = stock_code
        self.sector_name = sector_name
        self.source = source

    @classmethod
    def from_dict(cls, d: dict) -> "SectorStockMap":
        return cls(
            sector_code=d.get("sector_code") or "",
            stock_code=d.get("stock_code") or "",
            sector_name=d.get("sector_name") or "",
            source=d.get("source") or "",
        )

    def __repr__(self) -> str:
        return (f"SectorStockMap(sector_code={self.sector_code!r}, "
                f"stock_code={self.stock_code!r}, sector_name={self.sector_name!r})")


class TopList:
    """
    龙虎榜每日明细数据，对应本地 top_list 表。

    字段说明:
        id            自增ID（PK）
        trade_date    交易日期，格式 YYYY-MM-DD
        ts_code       股票代码
        name          股票名称
        close         收盘价
        pct_change    涨跌幅（%）
        turnover_rate 换手率（%）
        amount        总成交额
        l_sell        龙虎榜卖出额
        l_buy         龙虎榜买入额
        l_amount      龙虎榜成交额
        net_amount    龙虎榜净买入额
        net_rate      龙虎榜净买额占比（%）
        amount_rate   龙虎榜成交额占比（%）
        float_values  当日流通市值
        reason        上榜理由
    """

    __slots__ = ("id", "trade_date", "ts_code", "name", "close", "pct_change",
                 "turnover_rate", "amount", "l_sell", "l_buy", "l_amount",
                 "net_amount", "net_rate", "amount_rate", "float_values", "reason")

    def __init__(self, id: int, trade_date: str, ts_code: str, name: str,
                 close: float, pct_change: float, turnover_rate: float, amount: float,
                 l_sell: float, l_buy: float, l_amount: float, net_amount: float,
                 net_rate: float, amount_rate: float, float_values: float, reason: str):
        self.id = id
        self.trade_date = trade_date
        self.ts_code = ts_code
        self.name = name
        self.close = close
        self.pct_change = pct_change
        self.turnover_rate = turnover_rate
        self.amount = amount
        self.l_sell = l_sell
        self.l_buy = l_buy
        self.l_amount = l_amount
        self.net_amount = net_amount
        self.net_rate = net_rate
        self.amount_rate = amount_rate
        self.float_values = float_values
        self.reason = reason

    @classmethod
    def from_dict(cls, d: dict) -> "TopList":
        def _f(v):
            try:
                return float(v) if v is not None and v != "" else 0.0
            except (TypeError, ValueError):
                return 0.0

        def _i(v):
            try:
                return int(v) if v is not None and v != "" else 0
            except (TypeError, ValueError):
                return 0

        return cls(
            id=_i(d.get("id")),
            trade_date=d.get("trade_date") or "",
            ts_code=d.get("ts_code") or "",
            name=d.get("name") or "",
            close=_f(d.get("close")),
            pct_change=_f(d.get("pct_change")),
            turnover_rate=_f(d.get("turnover_rate")),
            amount=_f(d.get("amount")),
            l_sell=_f(d.get("l_sell")),
            l_buy=_f(d.get("l_buy")),
            l_amount=_f(d.get("l_amount")),
            net_amount=_f(d.get("net_amount")),
            net_rate=_f(d.get("net_rate")),
            amount_rate=_f(d.get("amount_rate")),
            float_values=_f(d.get("float_values")),
            reason=d.get("reason") or "",
        )

    def __repr__(self) -> str:
        return (f"TopList(trade_date={self.trade_date!r}, ts_code={self.ts_code!r}, "
                f"name={self.name!r}, pct_change={self.pct_change})")


class TopInst:
    """
    龙虎榜机构交易明细数据，对应本地 top_inst 表。

    字段说明:
        id          自增ID（PK）
        trade_date  交易日期，格式 YYYY-MM-DD
        ts_code     股票代码
        exalter     营业部名称/机构名称
        side        买卖类型（0:买入最大的前5名, 1:卖出最大的前5名）
        buy         买入额（元）
        buy_rate    买入占总成交比例（%）
        sell        卖出额（元）
        sell_rate   卖出占总成交比例（%）
        net_buy     净成交额（元）
        reason      上榜理由
    """

    __slots__ = ("id", "trade_date", "ts_code", "exalter", "side",
                 "buy", "buy_rate", "sell", "sell_rate", "net_buy", "reason")

    def __init__(self, id: int, trade_date: str, ts_code: str, exalter: str,
                 side: str, buy: float, buy_rate: float, sell: float,
                 sell_rate: float, net_buy: float, reason: str):
        self.id = id
        self.trade_date = trade_date
        self.ts_code = ts_code
        self.exalter = exalter
        self.side = side
        self.buy = buy
        self.buy_rate = buy_rate
        self.sell = sell
        self.sell_rate = sell_rate
        self.net_buy = net_buy
        self.reason = reason

    @classmethod
    def from_dict(cls, d: dict) -> "TopInst":
        def _f(v):
            try:
                return float(v) if v is not None and v != "" else 0.0
            except (TypeError, ValueError):
                return 0.0

        def _i(v):
            try:
                return int(v) if v is not None and v != "" else 0
            except (TypeError, ValueError):
                return 0

        return cls(
            id=_i(d.get("id")),
            trade_date=d.get("trade_date") or "",
            ts_code=d.get("ts_code") or "",
            exalter=d.get("exalter") or "",
            side=d.get("side") or "",
            buy=_f(d.get("buy")),
            buy_rate=_f(d.get("buy_rate")),
            sell=_f(d.get("sell")),
            sell_rate=_f(d.get("sell_rate")),
            net_buy=_f(d.get("net_buy")),
            reason=d.get("reason") or "",
        )

    def __repr__(self) -> str:
        return (f"TopInst(trade_date={self.trade_date!r}, ts_code={self.ts_code!r}, "
                f"exalter={self.exalter!r}, side={self.side!r}, net_buy={self.net_buy})")


class SectorFlowDaily:
    """
    板块资金流向数据，对应本地 sector_flow_daily 表。

    字段说明:
        trade_date              交易日期（PK），格式 YYYY-MM-DD
        content_type            板块类型（行业/概念/地域）
        ts_code                 板块代码（PK）
        name                    板块名称
        pct_change              涨跌幅（%）
        close                   收盘价
        net_amount              净流入金额（元）
        net_amount_rate         净流入占比（%）
        buy_elg_amount          超大单净流入（元）
        buy_elg_amount_rate     超大单净流入占比（%）
        buy_lg_amount           大单净流入（元）
        buy_lg_amount_rate      大单净流入占比（%）
        buy_md_amount           中单净流入（元）
        buy_md_amount_rate      中单净流入占比（%）
        buy_sm_amount           小单净流入（元）
        buy_sm_amount_rate      小单净流入占比（%）
        buy_sm_amount_stock     小单净流入最大股
        rank                    排名
    """

    __slots__ = ("trade_date", "ts_code", "name", "content_type",
                 "pct_change", "close", "net_amount", "net_amount_rate",
                 "buy_elg_amount", "buy_elg_amount_rate",
                 "buy_lg_amount", "buy_lg_amount_rate",
                 "buy_md_amount", "buy_md_amount_rate",
                 "buy_sm_amount", "buy_sm_amount_rate",
                 "buy_sm_amount_stock", "rank")

    def __init__(self, trade_date: str, ts_code: str, name: str, content_type: str,
                 pct_change: float, close: float,
                 net_amount: float, net_amount_rate: float,
                 buy_elg_amount: float, buy_elg_amount_rate: float,
                 buy_lg_amount: float, buy_lg_amount_rate: float,
                 buy_md_amount: float, buy_md_amount_rate: float,
                 buy_sm_amount: float, buy_sm_amount_rate: float,
                 buy_sm_amount_stock: str, rank: int):
        self.trade_date = trade_date
        self.ts_code = ts_code
        self.name = name
        self.content_type = content_type
        self.pct_change = pct_change
        self.close = close
        self.net_amount = net_amount
        self.net_amount_rate = net_amount_rate
        self.buy_elg_amount = buy_elg_amount
        self.buy_elg_amount_rate = buy_elg_amount_rate
        self.buy_lg_amount = buy_lg_amount
        self.buy_lg_amount_rate = buy_lg_amount_rate
        self.buy_md_amount = buy_md_amount
        self.buy_md_amount_rate = buy_md_amount_rate
        self.buy_sm_amount = buy_sm_amount
        self.buy_sm_amount_rate = buy_sm_amount_rate
        self.buy_sm_amount_stock = buy_sm_amount_stock
        self.rank = rank

    @classmethod
    def from_dict(cls, d: dict) -> "SectorFlowDaily":
        def _f(v):
            try:
                return float(v) if v is not None and v != "" else 0.0
            except (TypeError, ValueError):
                return 0.0

        def _i(v):
            try:
                return int(v) if v is not None and v != "" else 0
            except (TypeError, ValueError):
                return 0

        return cls(
            trade_date=d.get("trade_date") or "",
            ts_code=d.get("ts_code") or "",
            name=d.get("name") or "",
            content_type=d.get("content_type") or "",
            pct_change=_f(d.get("pct_change")),
            close=_f(d.get("close")),
            net_amount=_f(d.get("net_amount")),
            net_amount_rate=_f(d.get("net_amount_rate")),
            buy_elg_amount=_f(d.get("buy_elg_amount")),
            buy_elg_amount_rate=_f(d.get("buy_elg_amount_rate")),
            buy_lg_amount=_f(d.get("buy_lg_amount")),
            buy_lg_amount_rate=_f(d.get("buy_lg_amount_rate")),
            buy_md_amount=_f(d.get("buy_md_amount")),
            buy_md_amount_rate=_f(d.get("buy_md_amount_rate")),
            buy_sm_amount=_f(d.get("buy_sm_amount")),
            buy_sm_amount_rate=_f(d.get("buy_sm_amount_rate")),
            buy_sm_amount_stock=d.get("buy_sm_amount_stock") or "",
            rank=_i(d.get("rank")),
        )

    def __repr__(self) -> str:
        return (f"SectorFlowDaily(trade_date={self.trade_date!r}, "
                f"ts_code={self.ts_code!r}, name={self.name!r}, "
                f"net_amount={self.net_amount})")


class IndexBasic:
    """
    指数基础信息，对应本地 index_basic 表。

    字段说明:
        ts_code     指数代码（PK）
        name        指数名称
        fullname    指数全称
        market      市场
        publisher   发布方
        index_type  指数类型
        category    分类
        base_date   基准日期，格式 YYYY-MM-DD
        base_point  基点
        list_date   发布日期，格式 YYYY-MM-DD
        weight_rule 加权方式
        desc        描述
        exp_date    终止日期，格式 YYYY-MM-DD
    """

    __slots__ = ("ts_code", "name", "fullname", "market", "publisher",
                 "index_type", "category", "base_date", "base_point",
                 "list_date", "weight_rule", "desc", "exp_date")

    def __init__(self, ts_code: str, name: str, fullname: str, market: str,
                 publisher: str, index_type: str, category: str, base_date: str,
                 base_point: float, list_date: str, weight_rule: str,
                 desc: str, exp_date: str):
        self.ts_code = ts_code
        self.name = name
        self.fullname = fullname
        self.market = market
        self.publisher = publisher
        self.index_type = index_type
        self.category = category
        self.base_date = base_date
        self.base_point = base_point
        self.list_date = list_date
        self.weight_rule = weight_rule
        self.desc = desc
        self.exp_date = exp_date

    @classmethod
    def from_dict(cls, d: dict) -> "IndexBasic":
        def _f(v):
            try:
                return float(v) if v is not None and v != "" else 0.0
            except (TypeError, ValueError):
                return 0.0

        return cls(
            ts_code=d.get("ts_code") or "",
            name=d.get("name") or "",
            fullname=d.get("fullname") or "",
            market=d.get("market") or "",
            publisher=d.get("publisher") or "",
            index_type=d.get("index_type") or "",
            category=d.get("category") or "",
            base_date=d.get("base_date") or "",
            base_point=_f(d.get("base_point")),
            list_date=d.get("list_date") or "",
            weight_rule=d.get("weight_rule") or "",
            desc=d.get("desc") or "",
            exp_date=d.get("exp_date") or "",
        )

    def __repr__(self) -> str:
        return (f"IndexBasic(ts_code={self.ts_code!r}, name={self.name!r}, "
                f"market={self.market!r})")


class IndexDaily:
    """
    指数日线行情数据，对应本地 index_daily 表。

    字段说明:
        trade_date  交易日期（PK），格式 YYYY-MM-DD
        ts_code     指数代码（PK）
        close       收盘指数
        open        开盘指数
        high        最高指数
        low         最低指数
        pre_close   前收盘指数
        change      涨跌点数
        pct_chg     涨跌幅（%）
        vol         成交量
        amount      成交额
    """

    __slots__ = ("trade_date", "ts_code", "open", "high", "low", "close",
                 "pre_close", "change", "pct_chg", "vol", "amount")

    def __init__(self, trade_date: str, ts_code: str, open: float, high: float,
                 low: float, close: float, pre_close: float, change: float,
                 pct_chg: float, vol: float, amount: float):
        self.trade_date = trade_date
        self.ts_code = ts_code
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.pre_close = pre_close
        self.change = change
        self.pct_chg = pct_chg
        self.vol = vol
        self.amount = amount

    @classmethod
    def from_dict(cls, d: dict) -> "IndexDaily":
        def _f(v):
            try:
                return float(v) if v is not None and v != "" else 0.0
            except (TypeError, ValueError):
                return 0.0

        return cls(
            trade_date=d.get("trade_date") or "",
            ts_code=d.get("ts_code") or "",
            open=_f(d.get("open")),
            high=_f(d.get("high")),
            low=_f(d.get("low")),
            close=_f(d.get("close")),
            pre_close=_f(d.get("pre_close")),
            change=_f(d.get("change")),
            pct_chg=_f(d.get("pct_chg")),
            vol=_f(d.get("vol")),
            amount=_f(d.get("amount")),
        )

    def __repr__(self) -> str:
        return (f"IndexDaily(trade_date={self.trade_date!r}, ts_code={self.ts_code!r}, "
                f"close={self.close}, pct_chg={self.pct_chg})")


class IndexWeekly:
    """
    指数周线行情数据，对应本地 index_weekly 表。

    字段说明:
        trade_date  交易日期（PK），格式 YYYY-MM-DD
        ts_code     指数代码（PK）
        close       收盘指数
        open        开盘指数
        high        最高指数
        low         最低指数
        pre_close   前收盘指数
        change      涨跌点数
        pct_chg     涨跌幅（%）
        vol         成交量
        amount      成交额
    """

    __slots__ = ("trade_date", "ts_code", "open", "high", "low", "close",
                 "pre_close", "change", "pct_chg", "vol", "amount")

    def __init__(self, trade_date: str, ts_code: str, open: float, high: float,
                 low: float, close: float, pre_close: float, change: float,
                 pct_chg: float, vol: float, amount: float):
        self.trade_date = trade_date
        self.ts_code = ts_code
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.pre_close = pre_close
        self.change = change
        self.pct_chg = pct_chg
        self.vol = vol
        self.amount = amount

    @classmethod
    def from_dict(cls, d: dict) -> "IndexWeekly":
        def _f(v):
            try:
                return float(v) if v is not None and v != "" else 0.0
            except (TypeError, ValueError):
                return 0.0

        return cls(
            trade_date=d.get("trade_date") or "",
            ts_code=d.get("ts_code") or "",
            open=_f(d.get("open")),
            high=_f(d.get("high")),
            low=_f(d.get("low")),
            close=_f(d.get("close")),
            pre_close=_f(d.get("pre_close")),
            change=_f(d.get("change")),
            pct_chg=_f(d.get("pct_chg")),
            vol=_f(d.get("vol")),
            amount=_f(d.get("amount")),
        )

    def __repr__(self) -> str:
        return (f"IndexWeekly(trade_date={self.trade_date!r}, ts_code={self.ts_code!r}, "
                f"close={self.close}, pct_chg={self.pct_chg})")


class IndexMonthly:
    """
    指数月线行情数据，对应本地 index_monthly 表。

    字段说明:
        trade_date  交易日期（PK），格式 YYYY-MM-DD
        ts_code     指数代码（PK）
        close       收盘指数
        open        开盘指数
        high        最高指数
        low         最低指数
        pre_close   前收盘指数
        change      涨跌点数
        pct_chg     涨跌幅（%）
        vol         成交量
        amount      成交额
    """

    __slots__ = ("trade_date", "ts_code", "open", "high", "low", "close",
                 "pre_close", "change", "pct_chg", "vol", "amount")

    def __init__(self, trade_date: str, ts_code: str, open: float, high: float,
                 low: float, close: float, pre_close: float, change: float,
                 pct_chg: float, vol: float, amount: float):
        self.trade_date = trade_date
        self.ts_code = ts_code
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.pre_close = pre_close
        self.change = change
        self.pct_chg = pct_chg
        self.vol = vol
        self.amount = amount

    @classmethod
    def from_dict(cls, d: dict) -> "IndexMonthly":
        def _f(v):
            try:
                return float(v) if v is not None and v != "" else 0.0
            except (TypeError, ValueError):
                return 0.0

        return cls(
            trade_date=d.get("trade_date") or "",
            ts_code=d.get("ts_code") or "",
            open=_f(d.get("open")),
            high=_f(d.get("high")),
            low=_f(d.get("low")),
            close=_f(d.get("close")),
            pre_close=_f(d.get("pre_close")),
            change=_f(d.get("change")),
            pct_chg=_f(d.get("pct_chg")),
            vol=_f(d.get("vol")),
            amount=_f(d.get("amount")),
        )

    def __repr__(self) -> str:
        return (f"IndexMonthly(trade_date={self.trade_date!r}, ts_code={self.ts_code!r}, "
                f"close={self.close}, pct_chg={self.pct_chg})")


class DailyBombList:
    """
    每日炸板榜单数据，对应本地 daily_bomb_list 表。

    字段说明:
        trade_date  交易日期（PK），格式 YYYY-MM-DD
        ts_code     股票代码（PK）
        name        股票名称
        bomb_type   炸板类型（U=曾涨停, D=曾跌停/撬板）
        limit_price 触及的涨跌停价格
        pct_chg     涨跌幅（%）
        volume      成交量
        amount      成交额
        sector      所属板块
    """

    __slots__ = ("trade_date", "ts_code", "name", "bomb_type", "limit_price",
                 "pct_chg", "volume", "amount", "sector")

    def __init__(self, trade_date: str, ts_code: str, name: str, bomb_type: str,
                 limit_price: float, pct_chg: float, volume: float, amount: float,
                 sector: str):
        self.trade_date = trade_date
        self.ts_code = ts_code
        self.name = name
        self.bomb_type = bomb_type
        self.limit_price = limit_price
        self.pct_chg = pct_chg
        self.volume = volume
        self.amount = amount
        self.sector = sector

    @classmethod
    def from_dict(cls, d: dict) -> "DailyBombList":
        def _f(v):
            try:
                return float(v) if v is not None and v != "" else 0.0
            except (TypeError, ValueError):
                return 0.0

        return cls(
            trade_date=d.get("trade_date") or "",
            ts_code=d.get("ts_code") or "",
            name=d.get("name") or "",
            bomb_type=d.get("bomb_type") or "",
            limit_price=_f(d.get("limit_price")),
            pct_chg=_f(d.get("pct_chg")),
            volume=_f(d.get("volume")),
            amount=_f(d.get("amount")),
            sector=d.get("sector") or "",
        )

    def __repr__(self) -> str:
        return (f"DailyBombList(trade_date={self.trade_date!r}, ts_code={self.ts_code!r}, "
                f"name={self.name!r}, bomb_type={self.bomb_type!r})")


class AppVersion:
    """
    应用版本信息。

    字段说明:
        version       版本号（如 1.0、1.1）
        release_date  发布日期，格式 YYYY-MM-DD
        file_name     安装包文件名
        download_url  安装包下载地址
    """

    __slots__ = ("version", "release_date", "file_name", "download_url")

    def __init__(self, version: str, release_date: str, file_name: str, download_url: str):
        self.version = version
        self.release_date = release_date
        self.file_name = file_name
        self.download_url = download_url

    @classmethod
    def from_dict(cls, d: dict) -> "AppVersion":
        return cls(
            version=d["version"],
            release_date=d["release_date"],
            file_name=d["file_name"],
            download_url=d["download_url"],
        )

    def __repr__(self) -> str:
        return (f"AppVersion(version={self.version!r}, release_date={self.release_date!r}, "
                f"file_name={self.file_name!r}, download_url={self.download_url!r})")


class TokenCheckResult:
    """
    Token 校验结果。

    字段说明:
        status   校验状态（success=通过, failure=失败）
        message  状态描述信息
    """

    __slots__ = ("status", "message")

    def __init__(self, status: str, message: str):
        self.status = status
        self.message = message

    @classmethod
    def from_dict(cls, d: dict) -> "TokenCheckResult":
        return cls(
            status=d.get("status") or "",
            message=d.get("message") or "",
        )

    def is_success(self) -> bool:
        return self.status == "success"

    def __repr__(self) -> str:
        return f"TokenCheckResult(status={self.status!r}, message={self.message!r})"
