"""
data_loader.py — Alpha 101 面板数据加载器

将数据库中的个股日线数据转换为 Alpha 计算所需的面板格式：
  - 行（index） = 交易日期（pd.Timestamp）
  - 列（columns） = 股票代码

返回字段：open / high / low / close / volume / amount / vwap / returns / ind

vwap 计算：amount / (volume * 100)，volume 单位为手（100股/手），amount 单位为元。
若某日某股 vwap 计算结果异常（<=0 或 NaN），回退为 (open+high+low+close)/4。

ind（行业）：从 stock_basic.industry 获取，广播到面板同形。
"""

from __future__ import annotations
import os
import sys
import numpy as np
import pandas as pd

# 允许直接运行或被上级包导入
_scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from data_fetcher import query_daily_kline, query_stock_basic


class AlphaDataLoader:
    """加载 Alpha 因子计算所需的跨截面面板数据。"""

    def load(
        self,
        codes: list[str],
        start_date: str,
        end_date: str,
        fill_method: str = "ffill",
    ) -> dict[str, pd.DataFrame]:
        """
        加载指定股票池和日期范围的面板数据。

        Args:
            codes:       股票代码列表，如 ['000001.SZ', '600519.SH']
            start_date:  起始日期，格式 'YYYY-MM-DD'
            end_date:    截止日期，格式 'YYYY-MM-DD'
            fill_method: NaN 填充方式（'ffill' / 'bfill' / None）

        Returns:
            字典，key 为字段名，value 为 DataFrame（行=日期，列=股票代码）：
              open, high, low, close, volume, amount, vwap, returns, ind
        """
        klines = query_daily_kline(
            codes=codes,
            start_date=start_date,
            end_date=end_date,
            order_by="date ASC",
        )
        if not klines:
            return {}

        records = [
            {
                "date":   k.date,
                "code":   k.code,
                "open":   k.open,
                "high":   k.high,
                "low":    k.low,
                "close":  k.close,
                "volume": k.volume,
                "amount": k.amount,
            }
            for k in klines
        ]

        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index(["date", "code"])

        panels: dict[str, pd.DataFrame] = {}
        for field in ("open", "high", "low", "close", "volume", "amount"):
            panels[field] = df[field].unstack(level="code").astype(float)

        # 填充缺失值
        if fill_method:
            for key in list(panels.keys()):
                panels[key] = getattr(panels[key], fill_method)()

        # ── vwap ──────────────────────────────────────────────────────────
        vol_safe = panels["volume"].replace(0, np.nan)
        vwap = panels["amount"] / (vol_safe * 100)        # volume 单位：手
        typical = (panels["open"] + panels["high"] + panels["low"] + panels["close"]) / 4
        bad = (vwap <= 0) | vwap.isna()
        panels["vwap"] = vwap.where(~bad, typical)

        # ── returns ───────────────────────────────────────────────────────
        panels["returns"] = panels["close"].pct_change()

        # ── industry ──────────────────────────────────────────────────────
        basics = query_stock_basic()
        ind_map = {b.ts_code: (b.industry or "Unknown") for b in basics}
        ind_panel = pd.DataFrame(
            {
                code: ind_map.get(code, "Unknown")
                for code in panels["close"].columns
            },
            index=panels["close"].index,
        )
        panels["ind"] = ind_panel

        return panels
