"""
data_fetcher.py
===============
封装 HTTP 数据获取接口，将远程数据拉取并持久化到本地 SQLite 数据库，
同时提供本地数据库的查询接口。

接口规范参考: API_REFERENCE.md § "通用数据查询接口"
表结构参考:  DATABASE_DOCUMENTATION.md

不依赖任何第三方库，仅使用 Python 3 标准库。
"""

import json
import datetime
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
import shutil
import pandas as pd
import requests
import os
import decrypt_patch
from sqlalchemy import create_engine, text, Engine

from typing import List, Optional
from define import BASE_URL, HTTP_TIMEOUT, DB_PATH, StockBasic, DailyKline, HourKline, WeeklyKline, MonthlyKline, DailyBasic, Income, StockLimit, DailyLimitList, DailyBombList, SectorStockMap, TopList, TopInst, SectorFlowDaily, IndexBasic, IndexDaily, IndexWeekly, IndexMonthly
import utils
from logger import log
import config
import remote_api
from remote_api import PatchItem
from urllib.parse import urlparse
_g_engine: Engine = None
g_table_name_to_pk = {
    "stock_basic" : ["ts_code"],
    "hour_kline" : ["code","date", "time"],
    "daily_kline" : ["code","date"],
    "weekly_kline" : ["code","date"],
    "monthly_kline" : ["code","date"],
    "daily_basic": ["ts_code", "trade_date"],
    "income": ["ts_code", "report_type", "end_date"],
    "stock_limit": ["trade_date", "ts_code"],
    "daily_limit_list": ["trade_date", "ts_code"],
    "daily_bomb_list": ["trade_date", "ts_code"],
    "sector_stock_map": ["sector_code", "stock_code"],
    "top_list": ["id"],
    "top_inst": ["id"],
    "sector_flow_daily": ["trade_date", "ts_code"],
    "index_basic": ["ts_code"],
    "index_daily": ["trade_date", "ts_code"],
    "index_weekly": ["trade_date", "ts_code"],
    "index_monthly": ["trade_date", "ts_code"],
}


def getEngine() -> Engine:
    global _g_engine
    if not _g_engine:
        _g_engine = create_engine(f"sqlite:///{DB_PATH}")
    return _g_engine

class TablePatch:
    """
    各个表目前应用的是哪个补丁的数据
    字段说明:
        patch 当前表数据是用的哪个patch，patch格式patch0、patch1等
    """
    __slots__ = ("patch")

    def __init__(self, patch: str):
        self.patch = patch

    @classmethod
    def from_dict(cls, d: dict) -> "TablePatch":
        """从字典（API 响应或数据库行）构造 TablePatch 对象。"""
        return cls(
            patch=d.get("patch") or "",
        )

    def __repr__(self) -> str:
        return f"TablePatch(patch={self.patch!r})"

# ============================================================
# 本地 SQLite 数据库管理
# ============================================================

def init_db() -> None:
    """
    初始化本地 SQLite 数据库，创建 stock_basic 和 daily_kline 表（若不存在）。
    若检测到旧版本表结构（字段不匹配），自动删除旧库重建。
    """
    assets_dir = utils.get_skill_assets_dir()
    base_data_file = os.path.join(assets_dir, "data_1.0.bin")
    if not os.path.exists(base_data_file):
        log(f"本地基础数据包 data_1.0.bin 不存在，正在从服务器下载...")
        if not download_data_file("data_1.0.bin", base_data_file, max_retries=3):
            log("错误:基础数据包下载失败，数据库初始化中止")
            return

    with getEngine().connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS stock_basic (
                ts_code     TEXT NOT NULL,
                symbol      TEXT,
                name        TEXT,
                area        TEXT,
                industry    TEXT,
                fullname    TEXT,
                enname      TEXT,
                cnspell     TEXT,
                market      TEXT,
                exchange    TEXT,
                curr_type   TEXT,
                list_status TEXT,
                list_date   TEXT,
                delist_date TEXT,
                is_hs       TEXT,
                PRIMARY KEY (ts_code)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS hour_kline (
                date        TEXT NOT NULL,
                time        TEXT NOT NULL,
                open        REAL,
                high        REAL,
                low         REAL,
                close       REAL,
                volume      REAL,
                amount      REAL,
                code        TEXT NOT NULL,
                PRIMARY KEY (code,date,time)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS daily_kline (
                date        TEXT NOT NULL,
                code        TEXT NOT NULL,
                open        REAL,
                high        REAL,
                low         REAL,
                close       REAL,
                volume      REAL,
                amount      REAL,
                adjustflag  TEXT,
                turn        REAL,
                pctChg      REAL,
                pre_close   REAL,
                change      REAL,
                PRIMARY KEY (code,date)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS weekly_kline (
                date        TEXT NOT NULL,
                code        TEXT NOT NULL,
                open        REAL,
                high        REAL,
                low         REAL,
                close       REAL,
                volume      REAL,
                amount      REAL,
                pctChg      REAL,
                PRIMARY KEY (code,date)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS monthly_kline (
                date        TEXT NOT NULL,
                code        TEXT NOT NULL,
                open        REAL,
                high        REAL,
                low         REAL,
                close       REAL,
                volume      REAL,
                amount      REAL,
                pctChg      REAL,
                PRIMARY KEY (code,date)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS daily_basic (
                trade_date       TEXT NOT NULL,
                ts_code          TEXT NOT NULL,
                close            REAL,
                turnover_rate    REAL,
                turnover_rate_f  REAL,
                volume_ratio     REAL,
                pe               REAL,
                pe_ttm           REAL,
                pb               REAL,
                ps               REAL,
                ps_ttm           REAL,
                dv_ratio         REAL,
                dv_ttm           REAL,
                total_share      REAL,
                float_share      REAL,
                free_share       REAL,
                total_mv         REAL,
                circ_mv          REAL,
                adj_factor       REAL,
                PRIMARY KEY (trade_date, ts_code)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS income (
                ts_code           TEXT NOT NULL,
                end_date          TEXT NOT NULL,
                ann_date          TEXT,
                report_type       TEXT NOT NULL,
                comp_type         TEXT,
                basic_eps         REAL,
                diluted_eps       REAL,
                total_revenue     REAL,
                revenue           REAL,
                total_cogs        REAL,
                oper_cost         REAL,
                sell_exp          REAL,
                admin_exp         REAL,
                fin_exp           REAL,
                total_profit      REAL,
                income_tax        REAL,
                n_income          REAL,
                n_income_attr_p   REAL,
                minority_gain     REAL,
                oth_compr_income  REAL,
                t_compr_income    REAL,
                compr_inc_attr_p  REAL,
                ebit              REAL,
                ebitda            REAL,
                roe               REAL,
                roa               REAL,
                gross_margin      REAL,
                net_profit_margin REAL,
                net_profit_yoy    REAL,
                revenue_yoy       REAL,
                equity_yoy        REAL,
                pcf               REAL,
                free_circ_mv      REAL,
                PRIMARY KEY (ts_code, report_type, end_date)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS stock_limit (
                trade_date  TEXT NOT NULL,
                ts_code     TEXT NOT NULL,
                pre_close   REAL,
                up_limit    REAL,
                down_limit  REAL,
                PRIMARY KEY (trade_date, ts_code)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS daily_limit_list (
                trade_date   TEXT NOT NULL,
                ts_code      TEXT NOT NULL,
                name         TEXT,
                limit_type   TEXT,
                limit_price  REAL,
                pct_chg      REAL,
                volume       REAL,
                amount       REAL,
                limit_streak INTEGER,
                sector       TEXT,
                PRIMARY KEY (trade_date, ts_code)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS daily_bomb_list (
                trade_date  TEXT NOT NULL,
                ts_code     TEXT NOT NULL,
                name        TEXT,
                bomb_type   TEXT,
                limit_price REAL,
                pct_chg     REAL,
                volume      REAL,
                amount      REAL,
                sector      TEXT,
                PRIMARY KEY (trade_date, ts_code)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sector_stock_map (
                sector_code  TEXT NOT NULL,
                stock_code   TEXT NOT NULL,
                sector_name  TEXT,
                source       TEXT,
                PRIMARY KEY (sector_code, stock_code)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS top_list (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date    TEXT,
                ts_code       TEXT,
                name          TEXT,
                close         REAL,
                pct_change    REAL,
                turnover_rate REAL,
                amount        REAL,
                l_sell        REAL,
                l_buy         REAL,
                l_amount      REAL,
                net_amount    REAL,
                net_rate      REAL,
                amount_rate   REAL,
                float_values  REAL,
                reason        TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS top_inst (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date  TEXT,
                ts_code     TEXT,
                exalter     TEXT,
                side        TEXT,
                buy         REAL,
                buy_rate    REAL,
                sell        REAL,
                sell_rate   REAL,
                net_buy     REAL,
                reason      TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sector_flow_daily (
                trade_date              TEXT NOT NULL,
                content_type            TEXT,
                ts_code                 TEXT NOT NULL,
                name                    TEXT,
                pct_change              REAL,
                close                   REAL,
                net_amount              REAL,
                net_amount_rate         REAL,
                buy_elg_amount          REAL,
                buy_elg_amount_rate     REAL,
                buy_lg_amount           REAL,
                buy_lg_amount_rate      REAL,
                buy_md_amount           REAL,
                buy_md_amount_rate      REAL,
                buy_sm_amount           REAL,
                buy_sm_amount_rate      REAL,
                buy_sm_amount_stock     TEXT,
                rank                    INTEGER,
                PRIMARY KEY (trade_date, ts_code)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS index_basic (
                ts_code     TEXT NOT NULL,
                name        TEXT,
                fullname    TEXT,
                market      TEXT,
                publisher   TEXT,
                index_type  TEXT,
                category    TEXT,
                base_date   TEXT,
                base_point  REAL,
                list_date   TEXT,
                weight_rule TEXT,
                desc        TEXT,
                exp_date    TEXT,
                PRIMARY KEY (ts_code)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS index_daily (
                trade_date  TEXT NOT NULL,
                ts_code     TEXT NOT NULL,
                close       REAL,
                open        REAL,
                high        REAL,
                low         REAL,
                pre_close   REAL,
                change      REAL,
                pct_chg     REAL,
                vol         REAL,
                amount      REAL,
                PRIMARY KEY (trade_date, ts_code)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS index_weekly (
                trade_date  TEXT NOT NULL,
                ts_code     TEXT NOT NULL,
                close       REAL,
                open        REAL,
                high        REAL,
                low         REAL,
                pre_close   REAL,
                change      REAL,
                pct_chg     REAL,
                vol         REAL,
                amount      REAL,
                PRIMARY KEY (trade_date, ts_code)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS index_monthly (
                trade_date  TEXT NOT NULL,
                ts_code     TEXT NOT NULL,
                close       REAL,
                open        REAL,
                high        REAL,
                low         REAL,
                pre_close   REAL,
                change      REAL,
                pct_chg     REAL,
                vol         REAL,
                amount      REAL,
                PRIMARY KEY (trade_date, ts_code)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS table_patch (
                patch        TEXT NOT NULL
            )
        """))
        conn.commit()
  
# ============================================================
# 本地 SQLite 查询接口
# ============================================================

def query_stock_basic(
    ts_code: Optional[str] = None,
    industry: Optional[str] = None,
    industry_keyword: Optional[str] = None,
    area: Optional[str] = None,
    market: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[StockBasic]:
    """
    从本地 SQLite 数据库查询 stock_basic 表，返回 StockBasic 对象列表。

    参数:
        ts_code          按股票代码精确过滤
        industry         按行业名称精确过滤
        industry_keyword 按行业名称关键词模糊过滤（LIKE %keyword%），与 industry 互斥，
                         优先使用 industry_keyword
        area             按地区精确过滤
        market           按市场精确过滤
        limit            返回最大记录数；为 None 表示不限
        offset           分页偏移量，默认 0

    返回:
        List[StockBasic]  符合条件的股票基础信息对象列表

    示例:
        all_stocks   = query_stock_basic()
        bank_stocks  = query_stock_basic(industry="银行")
        chip_stocks  = query_stock_basic(industry_keyword="半导体")
        single_stock = query_stock_basic(ts_code="000001.SZ")
    """

    conditions = []
    params: dict = {}

    if ts_code is not None:
        conditions.append("ts_code = :ts_code")
        params["ts_code"] = ts_code
    if industry_keyword is not None:
        conditions.append("industry LIKE :industry_keyword")
        params["industry_keyword"] = f"%{industry_keyword}%"
    elif industry is not None:
        conditions.append("industry = :industry")
        params["industry"] = industry
    if area is not None:
        conditions.append("area = :area")
        params["area"] = area
    if market is not None:
        conditions.append("market = :market")
        params["market"] = market

    sql = "SELECT * FROM stock_basic"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [StockBasic.from_dict(dict(row._mapping)) for row in rows]

def query_daily_kline(
    codes: List[str] = [],
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: str = "date ASC",
) -> List[DailyKline]:
    """
    从本地 SQLite 数据库查询 daily_kline 表，返回 DailyKline 对象列表。

    参数:
        code        按股票代码精确过滤
        date        按具体交易日期精确过滤，格式 "YYYY-MM-DD"
        start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
        end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
        limit       返回最大记录数；为 None 表示不限
        offset      分页偏移量，默认 0
        order_by    排序表达式，默认 "date ASC"

    返回:
        List[DailyKline]  符合条件的日线行情对象列表

    示例:
        # 查询某只股票全部历史行情（按日期升序）
        klines = query_daily_kline(code=["sz.000001"])

        # 查询某只股票某段时间行情，最新的 30 条
        klines = query_daily_kline(code=["sz.000001"],
                                   start_date="2024-01-01", end_date="2024-12-31",
                                   limit=30, order_by="date DESC")

        # 查询某天全市场行情
        klines = query_daily_kline(date="2024-06-03")
    """
    conditions = []
    params: dict = {}

    if len(codes) != 0:
        keys = [f"code_{i}" for i in range(len(codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"code IN ({placeholders})")
        for k, v in zip(keys, codes):
            params[k] = v
    if date is not None:
        conditions.append("DATE(date) = :date")
        params["date"] = date
    else:
        if start_date is not None:
            conditions.append("DATE(date) >= DATE('{0}')".format(start_date))

        if end_date is not None:
            conditions.append("DATE(date) <= DATE('{0}')".format(end_date))


    sql = "SELECT * FROM daily_kline"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    # SQLite IN 子句上限 999，codes 过多时分批查询后合并
    if len(codes) > 900:
        result = []
        for i in range(0, len(codes), 900):
            result.extend(
                query_daily_kline(
                    codes=codes[i: i + 900],
                    date=date,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                    offset=offset,
                    order_by=order_by,
                )
            )
        return result

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [DailyKline.from_dict(dict(row._mapping)) for row in rows]


def query_hour_kline(
    codes: List[str] = [],
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: str = "date ASC, time ASC",
) -> List[HourKline]:
    """
    从本地 SQLite 数据库查询 hour_kline 表，返回 HourKline 对象列表。

    参数:
        codes       按股票代码列表过滤
        date        按具体交易日期精确过滤，格式 "YYYY-MM-DD"
        start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
        end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
        limit       返回最大记录数；为 None 表示不限
        offset      分页偏移量，默认 0
        order_by    排序表达式，默认 "date ASC, time ASC"

    返回:
        List[HourKline]  符合条件的小时级别 K 线对象列表
    """
    conditions = []
    params: dict = {}

    if len(codes) != 0:
        keys = [f"code_{i}" for i in range(len(codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"code IN ({placeholders})")
        for k, v in zip(keys, codes):
            params[k] = v
    if date is not None:
        conditions.append("DATE(date) = :date")
        params["date"] = date
    else:
        if start_date is not None:
            conditions.append("DATE(date) >= DATE('{0}')".format(start_date))
        if end_date is not None:
            conditions.append("DATE(date) <= DATE('{0}')".format(end_date))

    sql = "SELECT * FROM hour_kline"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [HourKline.from_dict(dict(row._mapping)) for row in rows]


def query_weekly_kline(
    codes: List[str] = [],
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: str = "date ASC",
) -> List[WeeklyKline]:
    """
    从本地 SQLite 数据库查询 weekly_kline 表，返回 WeeklyKline 对象列表。

    参数:
        codes       按股票代码列表过滤
        date        按具体日期精确过滤，格式 "YYYY-MM-DD"
        start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
        end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
        limit       返回最大记录数；为 None 表示不限
        offset      分页偏移量，默认 0
        order_by    排序表达式，默认 "date ASC"

    返回:
        List[WeeklyKline]  符合条件的周线 K 线对象列表
    """
    conditions = []
    params: dict = {}

    if len(codes) != 0:
        keys = [f"code_{i}" for i in range(len(codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"code IN ({placeholders})")
        for k, v in zip(keys, codes):
            params[k] = v
    if date is not None:
        conditions.append("DATE(date) = :date")
        params["date"] = date
    else:
        if start_date is not None:
            conditions.append("DATE(date) >= DATE('{0}')".format(start_date))
        if end_date is not None:
            conditions.append("DATE(date) <= DATE('{0}')".format(end_date))

    sql = "SELECT * FROM weekly_kline"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [WeeklyKline.from_dict(dict(row._mapping)) for row in rows]


def query_monthly_kline(
    codes: List[str] = [],
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: str = "date ASC",
) -> List[MonthlyKline]:
    """
    从本地 SQLite 数据库查询 monthly_kline 表，返回 MonthlyKline 对象列表。

    参数:
        codes       按股票代码列表过滤
        date        按具体日期精确过滤，格式 "YYYY-MM-DD"
        start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
        end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
        limit       返回最大记录数；为 None 表示不限
        offset      分页偏移量，默认 0
        order_by    排序表达式，默认 "date ASC"

    返回:
        List[MonthlyKline]  符合条件的月线 K 线对象列表
    """
    conditions = []
    params: dict = {}

    if len(codes) != 0:
        keys = [f"code_{i}" for i in range(len(codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"code IN ({placeholders})")
        for k, v in zip(keys, codes):
            params[k] = v
    if date is not None:
        conditions.append("DATE(date) = :date")
        params["date"] = date
    else:
        if start_date is not None:
            conditions.append("DATE(date) >= DATE('{0}')".format(start_date))
        if end_date is not None:
            conditions.append("DATE(date) <= DATE('{0}')".format(end_date))

    sql = "SELECT * FROM monthly_kline"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [MonthlyKline.from_dict(dict(row._mapping)) for row in rows]


def query_daily_basic(
    ts_codes: List[str] = [],
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: str = "trade_date ASC",
) -> List[DailyBasic]:
    """
    从本地 SQLite 数据库查询 daily_basic 表，返回 DailyBasic 对象列表。

    参数:
        ts_codes    按股票代码列表过滤
        trade_date  按具体交易日期精确过滤，格式 "YYYY-MM-DD"
        start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
        end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
        limit       返回最大记录数；为 None 表示不限
        offset      分页偏移量，默认 0
        order_by    排序表达式，默认 "trade_date ASC"

    返回:
        List[DailyBasic]  符合条件的每日基本面指标对象列表

    示例:
        # 查询某只股票全部历史基本面数据
        basics = query_daily_basic(ts_codes=["000001.SZ"])

        # 查询某天全市场基本面数据
        basics = query_daily_basic(trade_date="2024-06-03")
    """
    conditions = []
    params: dict = {}

    if len(ts_codes) != 0:
        keys = [f"ts_code_{i}" for i in range(len(ts_codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"ts_code IN ({placeholders})")
        for k, v in zip(keys, ts_codes):
            params[k] = v
    if trade_date is not None:
        conditions.append("DATE(trade_date) = :trade_date")
        params["trade_date"] = trade_date
    else:
        if start_date is not None:
            conditions.append("DATE(trade_date) >= DATE('{0}')".format(start_date))
        if end_date is not None:
            conditions.append("DATE(trade_date) <= DATE('{0}')".format(end_date))

    sql = "SELECT * FROM daily_basic"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [DailyBasic.from_dict(dict(row._mapping)) for row in rows]


def query_income(
    ts_codes: List[str] = [],
    report_type: Optional[str] = None,
    end_date: Optional[str] = None,
    start_end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: str = "end_date ASC",
) -> List[Income]:
    """
    从本地 SQLite 数据库查询 income 表，返回 Income 对象列表。

    参数:
        ts_codes        按股票代码列表过滤
        report_type     按报告类型精确过滤（如 "1" 表示合并报表）
        end_date        按报告期结束日期精确过滤，格式 "YYYY-MM-DD"
        start_end_date  按报告期结束日期范围过滤下限（含），格式 "YYYY-MM-DD"
        limit           返回最大记录数；为 None 表示不限
        offset          分页偏移量，默认 0
        order_by        排序表达式，默认 "end_date ASC"

    返回:
        List[Income]  符合条件的利润表对象列表

    示例:
        # 查询某只股票全部利润表（合并报表）
        records = query_income(ts_codes=["000001.SZ"], report_type="1")

        # 查询某报告期全市场数据
        records = query_income(end_date="20231231")

        # 查询最新一期
        records = query_income(ts_codes=["000001.SZ"], order_by="end_date DESC", limit=1)
    """
    conditions = []
    params: dict = {}

    if len(ts_codes) != 0:
        keys = [f"ts_code_{i}" for i in range(len(ts_codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"ts_code IN ({placeholders})")
        for k, v in zip(keys, ts_codes):
            params[k] = v
    if report_type is not None:
        conditions.append("report_type = :report_type")
        params["report_type"] = report_type
    if end_date is not None:
        conditions.append("end_date = :end_date")
        params["end_date"] = end_date
    elif start_end_date is not None:
        conditions.append("end_date >= :start_end_date")
        params["start_end_date"] = start_end_date

    sql = "SELECT * FROM income"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [Income.from_dict(dict(row._mapping)) for row in rows]


def query_stock_limit(
    ts_codes: List[str] = [],
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: str = "trade_date ASC",
) -> List[StockLimit]:
    """
    从本地 SQLite 数据库查询 stock_limit 表，返回 StockLimit 对象列表。

    参数:
        ts_codes    按股票代码列表过滤
        trade_date  按具体交易日期精确过滤，格式 "YYYY-MM-DD"
        start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
        end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
        limit       返回最大记录数；为 None 表示不限
        offset      分页偏移量，默认 0
        order_by    排序表达式，默认 "trade_date ASC"

    返回:
        List[StockLimit]  符合条件的每日涨跌停价格对象列表

    示例:
        # 查询某只股票的涨跌停价格历史
        limits = query_stock_limit(ts_codes=["000001.SZ"])

        # 查询某天全市场涨跌停价格
        limits = query_stock_limit(trade_date="2024-06-03")
    """
    conditions = []
    params: dict = {}

    if len(ts_codes) != 0:
        keys = [f"ts_code_{i}" for i in range(len(ts_codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"ts_code IN ({placeholders})")
        for k, v in zip(keys, ts_codes):
            params[k] = v
    if trade_date is not None:
        conditions.append("DATE(trade_date) = :trade_date")
        params["trade_date"] = trade_date
    else:
        if start_date is not None:
            conditions.append("DATE(trade_date) >= DATE('{0}')".format(start_date))
        if end_date is not None:
            conditions.append("DATE(trade_date) <= DATE('{0}')".format(end_date))

    sql = "SELECT * FROM stock_limit"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [StockLimit.from_dict(dict(row._mapping)) for row in rows]


def query_daily_limit_list(
    ts_codes: List[str] = [],
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit_type: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: str = "trade_date ASC",
) -> List[DailyLimitList]:
    """
    从本地 SQLite 数据库查询 daily_limit_list 表，返回 DailyLimitList 对象列表。

    参数:
        ts_codes    按股票代码列表过滤
        trade_date  按具体交易日期精确过滤，格式 "YYYY-MM-DD"
        start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
        end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
        limit_type  按榜单类型过滤（U=涨停, D=跌停）
        limit       返回最大记录数；为 None 表示不限
        offset      分页偏移量，默认 0
        order_by    排序表达式，默认 "trade_date ASC"

    返回:
        List[DailyLimitList]  符合条件的每日涨跌停榜单对象列表

    示例:
        # 查询某天所有涨停股
        records = query_daily_limit_list(trade_date="2024-06-03", limit_type="U")

        # 查询某只股票历史上榜记录
        records = query_daily_limit_list(ts_codes=["000001.SZ"])
    """
    conditions = []
    params: dict = {}

    if len(ts_codes) != 0:
        keys = [f"ts_code_{i}" for i in range(len(ts_codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"ts_code IN ({placeholders})")
        for k, v in zip(keys, ts_codes):
            params[k] = v
    if trade_date is not None:
        conditions.append("DATE(trade_date) = :trade_date")
        params["trade_date"] = trade_date
    else:
        if start_date is not None:
            conditions.append("DATE(trade_date) >= DATE('{0}')".format(start_date))
        if end_date is not None:
            conditions.append("DATE(trade_date) <= DATE('{0}')".format(end_date))
    if limit_type is not None:
        conditions.append("limit_type = :limit_type")
        params["limit_type"] = limit_type

    sql = "SELECT * FROM daily_limit_list"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [DailyLimitList.from_dict(dict(row._mapping)) for row in rows]


def query_daily_bomb_list(
    ts_codes: List[str] = [],
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    bomb_type: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: str = "trade_date ASC",
) -> List[DailyBombList]:
    """
    从本地 SQLite 数据库查询 daily_bomb_list 表，返回 DailyBombList 对象列表。

    参数:
        ts_codes    按股票代码列表过滤
        trade_date  按具体交易日期精确过滤，格式 "YYYY-MM-DD"
        start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
        end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
        bomb_type   按炸板类型过滤（U=曾涨停, D=曾跌停/撬板）
        limit       返回最大记录数；为 None 表示不限
        offset      分页偏移量，默认 0
        order_by    排序表达式，默认 "trade_date ASC"

    返回:
        List[DailyBombList]  符合条件的每日炸板榜单对象列表

    示例:
        # 查询某天所有炸板（曾涨停）股票
        records = query_daily_bomb_list(trade_date="2024-06-03", bomb_type="U")

        # 查询某只股票历史炸板记录
        records = query_daily_bomb_list(ts_codes=["000001.SZ"])
    """
    conditions = []
    params: dict = {}

    if len(ts_codes) != 0:
        keys = [f"ts_code_{i}" for i in range(len(ts_codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"ts_code IN ({placeholders})")
        for k, v in zip(keys, ts_codes):
            params[k] = v
    if trade_date is not None:
        conditions.append("DATE(trade_date) = :trade_date")
        params["trade_date"] = trade_date
    else:
        if start_date is not None:
            conditions.append("DATE(trade_date) >= DATE('{0}')".format(start_date))
        if end_date is not None:
            conditions.append("DATE(trade_date) <= DATE('{0}')".format(end_date))
    if bomb_type is not None:
        conditions.append("bomb_type = :bomb_type")
        params["bomb_type"] = bomb_type

    sql = "SELECT * FROM daily_bomb_list"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [DailyBombList.from_dict(dict(row._mapping)) for row in rows]


def query_sector_stock_map(
    sector_codes: List[str] = [],
    stock_codes: List[str] = [],
    source: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[SectorStockMap]:
    """
    从本地 SQLite 数据库查询 sector_stock_map 表，返回 SectorStockMap 对象列表。

    参数:
        sector_codes 按板块代码列表过滤
        stock_codes  按股票代码列表过滤
        source       按数据来源精确过滤
        limit        返回最大记录数；为 None 表示不限
        offset       分页偏移量，默认 0

    示例:
        # 查询某个板块下的所有股票
        records = query_sector_stock_map(sector_codes=["BK0475"])

        # 查询某只股票归属的所有板块
        records = query_sector_stock_map(stock_codes=["000001.SZ"])
    """
    conditions = []
    params: dict = {}

    if len(sector_codes) != 0:
        keys = [f"sector_code_{i}" for i in range(len(sector_codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"sector_code IN ({placeholders})")
        for k, v in zip(keys, sector_codes):
            params[k] = v
    if len(stock_codes) != 0:
        keys = [f"stock_code_{i}" for i in range(len(stock_codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"stock_code IN ({placeholders})")
        for k, v in zip(keys, stock_codes):
            params[k] = v
    if source is not None:
        conditions.append("source = :source")
        params["source"] = source

    sql = "SELECT * FROM sector_stock_map"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [SectorStockMap.from_dict(dict(row._mapping)) for row in rows]


def query_top_list(
    ts_codes: List[str] = [],
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: str = "trade_date ASC",
) -> List[TopList]:
    """
    从本地 SQLite 数据库查询 top_list 表，返回 TopList 对象列表。

    参数:
        ts_codes    按股票代码列表过滤
        trade_date  按具体交易日期精确过滤，格式 "YYYY-MM-DD"
        start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
        end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
        limit       返回最大记录数；为 None 表示不限
        offset      分页偏移量，默认 0
        order_by    排序表达式，默认 "trade_date ASC"

    示例:
        # 查询某天龙虎榜数据
        records = query_top_list(trade_date="2024-06-03")

        # 查询某只股票历史上榜记录
        records = query_top_list(ts_codes=["000001.SZ"])
    """
    conditions = []
    params: dict = {}

    if len(ts_codes) != 0:
        keys = [f"ts_code_{i}" for i in range(len(ts_codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"ts_code IN ({placeholders})")
        for k, v in zip(keys, ts_codes):
            params[k] = v
    if trade_date is not None:
        conditions.append("DATE(trade_date) = :trade_date")
        params["trade_date"] = trade_date
    else:
        if start_date is not None:
            conditions.append("DATE(trade_date) >= DATE('{0}')".format(start_date))
        if end_date is not None:
            conditions.append("DATE(trade_date) <= DATE('{0}')".format(end_date))

    sql = "SELECT * FROM top_list"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [TopList.from_dict(dict(row._mapping)) for row in rows]


def query_top_inst(
    ts_codes: List[str] = [],
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    side: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: str = "trade_date ASC",
) -> List[TopInst]:
    """
    从本地 SQLite 数据库查询 top_inst 表，返回 TopInst 对象列表。

    参数:
        ts_codes    按股票代码列表过滤
        trade_date  按具体交易日期精确过滤，格式 "YYYY-MM-DD"
        start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
        end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
        side        按买卖类型过滤（"0"=买入, "1"=卖出）
        limit       返回最大记录数；为 None 表示不限
        offset      分页偏移量，默认 0
        order_by    排序表达式，默认 "trade_date ASC"

    示例:
        # 查询某天机构交易明细
        records = query_top_inst(trade_date="2024-06-03")

        # 查询某只股票历史机构上榜记录
        records = query_top_inst(ts_codes=["000001.SZ"])
    """
    conditions = []
    params: dict = {}

    if len(ts_codes) != 0:
        keys = [f"ts_code_{i}" for i in range(len(ts_codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"ts_code IN ({placeholders})")
        for k, v in zip(keys, ts_codes):
            params[k] = v
    if trade_date is not None:
        conditions.append("DATE(trade_date) = :trade_date")
        params["trade_date"] = trade_date
    else:
        if start_date is not None:
            conditions.append("DATE(trade_date) >= DATE('{0}')".format(start_date))
        if end_date is not None:
            conditions.append("DATE(trade_date) <= DATE('{0}')".format(end_date))
    if side is not None:
        conditions.append("side = :side")
        params["side"] = side

    sql = "SELECT * FROM top_inst"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [TopInst.from_dict(dict(row._mapping)) for row in rows]


def query_sector_flow_daily(
    ts_codes: List[str] = [],
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: str = "trade_date ASC",
) -> List[SectorFlowDaily]:
    """
    从本地 SQLite 数据库查询 sector_flow_daily 表，返回 SectorFlowDaily 对象列表。

    参数:
        ts_codes     按板块代码列表过滤
        trade_date   按具体交易日期精确过滤，格式 "YYYY-MM-DD"
        start_date   按日期范围过滤下限（含），格式 "YYYY-MM-DD"
        end_date     按日期范围过滤上限（含），格式 "YYYY-MM-DD"
        limit        返回最大记录数；为 None 表示不限
        offset       分页偏移量，默认 0
        order_by     排序表达式，默认 "trade_date ASC"

    示例:
        # 查询某天所有板块资金流向
        records = query_sector_flow_daily(trade_date="2024-06-03")

        # 查询某个板块历史资金流向
        records = query_sector_flow_daily(ts_codes=["BK0475"])
    """
    conditions = []
    params: dict = {}

    if len(ts_codes) != 0:
        keys = [f"ts_code_{i}" for i in range(len(ts_codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"ts_code IN ({placeholders})")
        for k, v in zip(keys, ts_codes):
            params[k] = v
    if trade_date is not None:
        conditions.append("DATE(trade_date) = :trade_date")
        params["trade_date"] = trade_date
    else:
        if start_date is not None:
            conditions.append("DATE(trade_date) >= DATE('{0}')".format(start_date))
        if end_date is not None:
            conditions.append("DATE(trade_date) <= DATE('{0}')".format(end_date))

    sql = "SELECT * FROM sector_flow_daily"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [SectorFlowDaily.from_dict(dict(row._mapping)) for row in rows]


def query_index_basic(
    ts_code: Optional[str] = None,
    market: Optional[str] = None,
    publisher: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[IndexBasic]:
    """
    从本地 SQLite 数据库查询 index_basic 表，返回 IndexBasic 对象列表。

    参数:
        ts_code   按指数代码精确过滤
        market    按市场精确过滤
        publisher 按发布方精确过滤
        limit     返回最大记录数；为 None 表示不限
        offset    分页偏移量，默认 0

    示例:
        # 查询所有指数
        records = query_index_basic()

        # 查询上证指数信息
        records = query_index_basic(ts_code="000001.SH")
    """
    conditions = []
    params: dict = {}

    if ts_code is not None:
        conditions.append("ts_code = :ts_code")
        params["ts_code"] = ts_code
    if market is not None:
        conditions.append("market = :market")
        params["market"] = market
    if publisher is not None:
        conditions.append("publisher = :publisher")
        params["publisher"] = publisher

    sql = "SELECT * FROM index_basic"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [IndexBasic.from_dict(dict(row._mapping)) for row in rows]


def query_index_daily(
    ts_codes: List[str] = [],
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: str = "trade_date ASC",
) -> List[IndexDaily]:
    """
    从本地 SQLite 数据库查询 index_daily 表，返回 IndexDaily 对象列表。

    参数:
        ts_codes    按指数代码列表过滤
        trade_date  按具体交易日期精确过滤，格式 "YYYY-MM-DD"
        start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
        end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
        limit       返回最大记录数；为 None 表示不限
        offset      分页偏移量，默认 0
        order_by    排序表达式，默认 "trade_date ASC"

    示例:
        # 查询上证指数历史日线
        records = query_index_daily(ts_codes=["000001.SH"])

        # 查询某天所有指数行情
        records = query_index_daily(trade_date="2024-06-03")
    """
    conditions = []
    params: dict = {}

    if len(ts_codes) != 0:
        keys = [f"ts_code_{i}" for i in range(len(ts_codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"ts_code IN ({placeholders})")
        for k, v in zip(keys, ts_codes):
            params[k] = v
    if trade_date is not None:
        conditions.append("DATE(trade_date) = :trade_date")
        params["trade_date"] = trade_date
    else:
        if start_date is not None:
            conditions.append("DATE(trade_date) >= DATE('{0}')".format(start_date))
        if end_date is not None:
            conditions.append("DATE(trade_date) <= DATE('{0}')".format(end_date))

    sql = "SELECT * FROM index_daily"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [IndexDaily.from_dict(dict(row._mapping)) for row in rows]


def query_index_weekly(
    ts_codes: List[str] = [],
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: str = "trade_date ASC",
) -> List[IndexWeekly]:
    """
    从本地 SQLite 数据库查询 index_weekly 表，返回 IndexWeekly 对象列表。

    参数:
        ts_codes    按指数代码列表过滤
        trade_date  按具体日期精确过滤，格式 "YYYY-MM-DD"
        start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
        end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
        limit       返回最大记录数；为 None 表示不限
        offset      分页偏移量，默认 0
        order_by    排序表达式，默认 "trade_date ASC"

    示例:
        # 查询上证指数周线
        records = query_index_weekly(ts_codes=["000001.SH"])
    """
    conditions = []
    params: dict = {}

    if len(ts_codes) != 0:
        keys = [f"ts_code_{i}" for i in range(len(ts_codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"ts_code IN ({placeholders})")
        for k, v in zip(keys, ts_codes):
            params[k] = v
    if trade_date is not None:
        conditions.append("DATE(trade_date) = :trade_date")
        params["trade_date"] = trade_date
    else:
        if start_date is not None:
            conditions.append("DATE(trade_date) >= DATE('{0}')".format(start_date))
        if end_date is not None:
            conditions.append("DATE(trade_date) <= DATE('{0}')".format(end_date))

    sql = "SELECT * FROM index_weekly"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [IndexWeekly.from_dict(dict(row._mapping)) for row in rows]


def query_index_monthly(
    ts_codes: List[str] = [],
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: str = "trade_date ASC",
) -> List[IndexMonthly]:
    """
    从本地 SQLite 数据库查询 index_monthly 表，返回 IndexMonthly 对象列表。

    参数:
        ts_codes    按指数代码列表过滤
        trade_date  按具体日期精确过滤，格式 "YYYY-MM-DD"
        start_date  按日期范围过滤下限（含），格式 "YYYY-MM-DD"
        end_date    按日期范围过滤上限（含），格式 "YYYY-MM-DD"
        limit       返回最大记录数；为 None 表示不限
        offset      分页偏移量，默认 0
        order_by    排序表达式，默认 "trade_date ASC"

    示例:
        # 查询上证指数月线
        records = query_index_monthly(ts_codes=["000001.SH"])
    """
    conditions = []
    params: dict = {}

    if len(ts_codes) != 0:
        keys = [f"ts_code_{i}" for i in range(len(ts_codes))]
        placeholders = ",".join(f":{k}" for k in keys)
        conditions.append(f"ts_code IN ({placeholders})")
        for k, v in zip(keys, ts_codes):
            params[k] = v
    if trade_date is not None:
        conditions.append("DATE(trade_date) = :trade_date")
        params["trade_date"] = trade_date
    else:
        if start_date is not None:
            conditions.append("DATE(trade_date) >= DATE('{0}')".format(start_date))
        if end_date is not None:
            conditions.append("DATE(trade_date) <= DATE('{0}')".format(end_date))

    sql = "SELECT * FROM index_monthly"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"

    with getEngine().connect() as conn:
        cursor = conn.execute(text(sql), params)
        rows = cursor.fetchall()
        return [IndexMonthly.from_dict(dict(row._mapping)) for row in rows]


def get_local_patch_ver() -> int:
    """从 table_patch 表中读取当前本地 patch 版本号，无记录时返回 -1。"""
    with getEngine().connect() as conn:
        row = conn.execute(text("SELECT patch FROM table_patch LIMIT 1")).fetchone()
    print(int(row[0]) if row else -1)
    return int(row[0]) if row else -1

def download_data_file(file_name: str, output_path: str, max_retries: int = 3) -> bool:
    """
    从服务器下载数据文件。

    参数:
        file_name:   要下载的文件名（如 data_1.0.bin）
        output_path: 保存路径
        max_retries: 最大重试次数

    返回:
        bool: 下载成功返回 True，否则返回 False
    """
    token = config.get_token()
    if not token:
        log("错误:未设置 Token，无法下载数据文件")
        return False

    for retry in range(max_retries):
        try:
            download_url = remote_api.request_download_url(file_name, token)
            if not download_url:
                log(f"错误:获取 {file_name} 下载链接失败，请检查 Token 是否有效")
                return False

            log(f"开始下载 {file_name} ...")
            log(f"下载地址: {download_url}")

            with requests.get(download_url, stream=True, timeout=300) as response:
                if response.status_code != 200:
                    log(f"下载失败，HTTP 状态码: {response.status_code}")
                    if retry < max_retries - 1:
                        log(f"重试 {retry + 1}/{max_retries} ...")
                        continue
                    return False

                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                chunk_size = 1024 * 1024

                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                pct = (downloaded / total_size) * 100
                                if downloaded % (10 * chunk_size) < chunk_size:
                                    log(f"下载进度: {pct:.1f}%")

            log(f"文件下载完成: {output_path}")
            return True

        except Exception as e:
            log(f"下载出错: {str(e)}")
            if retry < max_retries - 1:
                log(f"重试 {retry + 1}/{max_retries} ...")
            else:
                log(f"下载失败，已达到最大重试次数")
                return False

    return False

def download_from_url(url: str, output_path: str, timeout: int = 300) -> bool:
    """
    从指定 URL 下载文件到指定路径。

    参数:
        url:         下载链接
        output_path: 保存路径
        timeout:     超时时间（秒）

    返回:
        bool: 下载成功返回 True，否则返回 False
    """
    try:
        log(f"从 URL 下载文件: {url}")
        log(f"保存路径: {output_path}")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with requests.get(url, stream=True, timeout=timeout) as response:
            if response.status_code != 200:
                log(f"下载失败，HTTP 状态码: {response.status_code}")
                return False

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            chunk_size = 1024 * 1024

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = downloaded / total_size * 100
                            if downloaded % (10 * chunk_size) < chunk_size:
                                log(f"下载进度: {pct:.1f}%")

        log(f"文件下载完成: {output_path}")
        return True

    except Exception as e:
        log(f"下载出错: {str(e)}")
        return False

def syn_table_datas() -> List[str]:
    """
    根据表名，获取需要下载的 patch 列表。

    逻辑：
        1. 调用 request_patch_list() 获取服务器上该表的全部可用 patch 列表
        2. 查询本地 table_patch 表，找到该表当前已应用的 patch
        3. 返回当前 patch 之后（不含）的所有 patch，即待下载的部分；
           若本地无记录，则返回全部可用 patch

    参数:
        table_name  指定表的名称

    返回:
        List[str]  待下载的 patch 名称列表（按顺序）
    """
    
    local_patch_ver = -1
    with getEngine().connect() as conn:
        cursor = conn.execute(
            text("SELECT patch FROM table_patch")
        )
        row = cursor.fetchone()
        if row:
            local_patch_ver = int(row[0])
        conn.commit()
    
    log(f"本地数据patch ver:{local_patch_ver}")
    if local_patch_ver < 0:
        log(f"导入基础数据...")
        assets_dir = utils.get_skill_assets_dir()
        name = "data_1.0.bin"
        base_patch_zip = os.path.join(assets_dir, name)
        base_patch_decrypt_zip = os.path.join(utils.get_skill_work_dir(), "data_1.0_decrypt.zip")
        decrypt_key = remote_api.request_decrypt_key(name, config.get_token())
        if len(decrypt_key) == 0:
            log("错误:没有数据读取权限，请先注册")
            return
        decrypt_patch.process_file(base_patch_zip, base_patch_decrypt_zip, decrypt_key, False)
        base_patch_dir = os.path.join(utils.get_skill_work_dir(), "data_1.0")
        if os.path.exists(base_patch_dir):
            shutil.rmtree(base_patch_dir)
        utils.unzip_file(base_patch_decrypt_zip, base_patch_dir)
        import_datas_in_dir(base_patch_dir)

        with getEngine().connect() as conn:
            conn.execute(text("DELETE FROM table_patch"))
            conn.execute(text("INSERT INTO table_patch (patch) VALUES (0)"))
            conn.commit()
            os.remove(base_patch_decrypt_zip)
            shutil.rmtree(base_patch_dir)

    remote_patchs: List[PatchItem] = remote_api.request_patch_list()
    log(f"remote patch list:{','.join([str(r_patch.version) for r_patch in remote_patchs])}")
    for r_patch in remote_patchs:
        if r_patch.version > local_patch_ver:
            request_and_import_remote_patch_by_name(r_patch.patch_name, r_patch.version)

def request_and_import_remote_patch_by_name(patch_name:str, patch_ver: int):
    log(f"更新remote patch ver:{patch_ver}, name:{patch_name}......")
    url = f"{BASE_URL}/api/download_file"
    params = {
        "file_name": patch_name,
        "token_key": config.get_token()
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        download_url = data.get("download_url")
        tmp_patch_zip = os.path.join(utils.get_skill_work_dir(), patch_name)
        tmp_patch_decrypt_zip = os.path.join(utils.get_skill_work_dir(), f"decrypt_{patch_name}")
        tmp_patch_dir = os.path.join(utils.get_skill_work_dir(), "tmp_patch_unzip")
        # 下载
        utils.download_file(download_url, tmp_patch_zip)
        # 解密
        decrypt_key = remote_api.request_decrypt_key(patch_name, config.get_token())
        if len(decrypt_key) == 0:
                log("错误:没有数据读取权限，请先注册")
                return
        decrypt_patch.process_file(tmp_patch_zip, tmp_patch_decrypt_zip, decrypt_key, False)
        # 解压
        utils.unzip_file(tmp_patch_decrypt_zip, tmp_patch_dir)
        import_datas_in_dir(tmp_patch_dir)
        with getEngine().connect() as conn:
            conn.execute(text("DELETE FROM table_patch"))
            conn.execute(text(f"INSERT INTO table_patch (patch) VALUES ({patch_ver})"))
            conn.commit()
            shutil.rmtree(tmp_patch_dir)
            os.remove(tmp_patch_zip)
            os.remove(tmp_patch_decrypt_zip)
        log(f"更新本地数据patch ver:{patch_ver}")

def import_datas_in_dir(dir: str):
    files = utils.scan_files_in_dir(dir)
    for file in files:
        basename = os.path.basename(file)
        for table_name in g_table_name_to_pk.keys():
            if basename.startswith(table_name):
                import_data_to_table(file, table_name)

def import_data_to_table(input_file:str, table_name:str):
    log(f"导入表{table_name} from {input_file}")
    if input_file.endswith('.csv.gz'):
        df = pd.read_csv(input_file, compression='gzip')
    elif input_file.endswith('.csv'):
        df = pd.read_csv(input_file)
    elif input_file.endswith('.pkl'):
        df = pd.read_pickle(input_file)
    else:
        assert False

    engine = getEngine()
    raw_conn = engine.raw_connection()
    try:
        df.to_sql("tmp_import", raw_conn, if_exists="replace", index=False)
        cursor = raw_conn.cursor()
        cursor.execute(f"INSERT OR REPLACE INTO {table_name} SELECT * FROM tmp_import")
        raw_conn.commit()
        cursor.close()
    finally:
        raw_conn.close()

def syn_vip_basic_data():
    """
    更新vip基础数据包
    """
    url = f"{BASE_URL}/api/history_data"
    response = requests.get(url, params={"token": config.get_token()})
    if response.status_code == 200:
        file_url = response.json().get("download_url")
        filename = os.path.basename(urlparse(file_url).path)
        print("下载中...")
        tmp_patch_zip = os.path.join(utils.get_skill_work_dir(), filename)
        tmp_patch_decrypt_zip = os.path.join(utils.get_skill_work_dir(), f"decrypt_{filename}")
        tmp_patch_dir = os.path.join(utils.get_skill_work_dir(), "tmp_history_unzip")
        decrypt_key = remote_api.request_decrypt_key(filename, config.get_token())
        # 解密
        if len(decrypt_key) == 0:
                log("错误:没有数据读取权限，请先注册")
                return
        # 下载
        utils.download_file(file_url, tmp_patch_zip)
        decrypt_patch.process_file(tmp_patch_zip, tmp_patch_decrypt_zip, decrypt_key, False)
        # 解压
        utils.unzip_file(tmp_patch_decrypt_zip, tmp_patch_dir)
        import_datas_in_dir(tmp_patch_dir)


if __name__ == "__main__":
    log(f"数据库路径:{DB_PATH}")
    init_db()
    syn_table_datas()
    # syn_vip_basic_data()
    # testfunc()