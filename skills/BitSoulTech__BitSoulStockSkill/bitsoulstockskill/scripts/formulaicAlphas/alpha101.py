"""
alpha101.py — WorldQuant《101 Formulaic Alphas》完整实现

使用方法：
    from formulaicAlphas.data_loader import AlphaDataLoader
    from formulaicAlphas.alpha101 import Alpha101

    loader = AlphaDataLoader()
    data = loader.load(codes, start_date='2025-01-01', end_date='2026-03-14')

    a = Alpha101(data)
    alpha1  = a.alpha001()   # DataFrame: 行=日期, 列=股票代码
    alpha50 = a.alpha050()

    # 取最新一日横截面
    latest = alpha1.iloc[-1].dropna().sort_values()

设计说明：
- 每个 alpha 方法返回与输入面板同形的 DataFrame（行=日期，列=股票）
- 参数中的小数（如 3.65595）来自机器优化，实现时直接取整
- 带 IndNeutralize 的 alpha 需传入 ind（行业面板），否则跳过中性化直接使用原值
- sum / max / min 在公式中均指时间序列滚动操作（ts_sum / ts_max / ts_min）
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Optional

from .operators import (
    rank, scale, ind_neutralize,
    delay, delta, ts_sum, mean, stddev,
    ts_max, ts_min, ts_rank, ts_argmax, ts_argmin,
    correlation, covariance, decay_linear, product,
    signedpower, log, sign, abs_, adv, where,
)

Panel = pd.DataFrame


class Alpha101:
    """
    WorldQuant Alpha 101 因子库。

    Args:
        data: AlphaDataLoader.load() 返回的字段字典，需包含：
              open, high, low, close, volume, vwap, returns
              可选：ind（行业面板，带 IndNeutralize 的 alpha 所需）
    """

    def __init__(self, data: dict[str, Panel]):
        self.open    = data["open"].astype(float)
        self.high    = data["high"].astype(float)
        self.low     = data["low"].astype(float)
        self.close   = data["close"].astype(float)
        self.volume  = data["volume"].astype(float)
        self.vwap    = data["vwap"].astype(float)
        self.returns = data["returns"].astype(float)
        self.ind: Optional[Panel] = data.get("ind")

        self._adv_cache: dict[int, Panel] = {}

    # ── 内部辅助 ─────────────────────────────────────────────────────────────

    def _adv(self, n: int) -> Panel:
        """缓存各 n 日平均成交量。"""
        if n not in self._adv_cache:
            self._adv_cache[n] = adv(self.volume, n)
        return self._adv_cache[n]

    def _ind_neu(self, x: Panel) -> Panel:
        """如有行业数据则中性化，否则原样返回。"""
        if self.ind is not None:
            return ind_neutralize(x, self.ind)
        return x

    # ── Alpha 001 ── Alpha 010 ───────────────────────────────────────────────

    def alpha001(self) -> Panel:
        """rank(ts_argmax(signedpower(where(returns<0,stddev(returns,20),close),2),5)) - 0.5"""
        cond = self.returns < 0
        base = where(cond, stddev(self.returns, 20), self.close)
        return rank(ts_argmax(signedpower(base, 2), 5)) - 0.5

    def alpha002(self) -> Panel:
        """(-1) * correlation(rank(delta(log(volume),2)), rank((close-open)/open), 6)"""
        x = rank(delta(log(self.volume), 2))
        y = rank((self.close - self.open) / self.open)
        return -1 * correlation(x, y, 6)

    def alpha003(self) -> Panel:
        """(-1) * correlation(rank(open), rank(volume), 10)"""
        return -1 * correlation(rank(self.open), rank(self.volume), 10)

    def alpha004(self) -> Panel:
        """(-1) * ts_rank(rank(low), 9)"""
        return -1 * ts_rank(rank(self.low), 9)

    def alpha005(self) -> Panel:
        """rank(open - ts_sum(vwap,10)/10) * (-abs(rank(close - vwap)))"""
        return rank(self.open - ts_sum(self.vwap, 10) / 10) * (-abs_(rank(self.close - self.vwap)))

    def alpha006(self) -> Panel:
        """(-1) * correlation(open, volume, 10)"""
        return -1 * correlation(self.open, self.volume, 10)

    def alpha007(self) -> Panel:
        """if adv20 < volume: (-1)*ts_rank(abs(delta(close,7)),60)*sign(delta(close,7)) else -1"""
        adv20 = self._adv(20)
        d7 = delta(self.close, 7)
        hit = -1 * ts_rank(abs_(d7), 60) * sign(d7)
        return where(adv20 < self.volume, hit, -1)

    def alpha008(self) -> Panel:
        """(-1) * rank(ts_sum(open,5)*ts_sum(returns,5) - delay(ts_sum(open,5)*ts_sum(returns,5),10))"""
        prod = ts_sum(self.open, 5) * ts_sum(self.returns, 5)
        return -1 * rank(prod - delay(prod, 10))

    def alpha009(self) -> Panel:
        """顺势/逆势：5日内单调上涨→顺势；单调下跌→顺势；震荡→逆势"""
        d1 = delta(self.close, 1)
        cond_up   = ts_min(d1, 5) > 0
        cond_down = ts_max(d1, 5) < 0
        return where(cond_up, d1, where(cond_down, d1, -d1))

    def alpha010(self) -> Panel:
        """rank(alpha009_logic_with_4day_window)"""
        d1 = delta(self.close, 1)
        cond_up   = ts_min(d1, 4) > 0
        cond_down = ts_max(d1, 4) < 0
        return rank(where(cond_up, d1, where(cond_down, d1, -d1)))

    # ── Alpha 011 ── Alpha 020 ───────────────────────────────────────────────

    def alpha011(self) -> Panel:
        """(rank(ts_max(vwap-close,3)) + rank(ts_min(vwap-close,3))) * rank(delta(volume,3))"""
        vc = self.vwap - self.close
        return (rank(ts_max(vc, 3)) + rank(ts_min(vc, 3))) * rank(delta(self.volume, 3))

    def alpha012(self) -> Panel:
        """sign(delta(volume,1)) * (-delta(close,1))"""
        return sign(delta(self.volume, 1)) * (-delta(self.close, 1))

    def alpha013(self) -> Panel:
        """(-1) * rank(covariance(rank(close), rank(volume), 5))"""
        return -1 * rank(covariance(rank(self.close), rank(self.volume), 5))

    def alpha014(self) -> Panel:
        """(-1)*rank(delta(returns,3)) * correlation(open, volume, 10)"""
        return -1 * rank(delta(self.returns, 3)) * correlation(self.open, self.volume, 10)

    def alpha015(self) -> Panel:
        """(-1) * ts_sum(rank(correlation(rank(high), rank(volume), 3)), 3)"""
        return -1 * ts_sum(rank(correlation(rank(self.high), rank(self.volume), 3)), 3)

    def alpha016(self) -> Panel:
        """(-1) * rank(covariance(rank(high), rank(volume), 5))"""
        return -1 * rank(covariance(rank(self.high), rank(self.volume), 5))

    def alpha017(self) -> Panel:
        """(-1)*rank(ts_rank(close,10)) * rank(delta(delta(close,1),1)) * rank(ts_rank(vol/adv20,5))"""
        adv20 = self._adv(20)
        return (
            -1 * rank(ts_rank(self.close, 10))
            * rank(delta(delta(self.close, 1), 1))
            * rank(ts_rank(self.volume / adv20, 5))
        )

    def alpha018(self) -> Panel:
        """(-1)*rank(stddev(abs(close-open),5) + (close-open) + correlation(close,open,10))"""
        return -1 * rank(
            stddev(abs_(self.close - self.open), 5)
            + (self.close - self.open)
            + correlation(self.close, self.open, 10)
        )

    def alpha019(self) -> Panel:
        """(-1)*sign(2*delta(close,7)) * (1 + rank(1 - ts_sum(returns,250)))"""
        # (close - delay(close,7)) + delta(close,7) = 2*delta(close,7)
        return -1 * sign(delta(self.close, 7)) * (1 + rank(1 - ts_sum(self.returns, 250)))

    def alpha020(self) -> Panel:
        """(-1)*rank(open-delay(high,1)) * rank(open-delay(close,1)) * rank(open-delay(low,1))"""
        return (
            -1
            * rank(self.open - delay(self.high, 1))
            * rank(self.open - delay(self.close, 1))
            * rank(self.open - delay(self.low, 1))
        )

    # ── Alpha 021 ── Alpha 030 ───────────────────────────────────────────────

    def alpha021(self) -> Panel:
        """布林带判断：价格突破上轨→看空，跌破下轨→看多，中间→排名。"""
        ma8  = ts_sum(self.close, 8) / 8
        std8 = stddev(self.close, 8)
        ma2  = ts_sum(self.close, 2) / 2
        cond_up   = (ma8 + std8) < ma2
        cond_down = ma2 < (ma8 - std8)
        middle    = 1 - rank(std8 + ts_max(self.close, 8))
        return where(cond_up, -1, where(cond_down, 1, middle))

    def alpha022(self) -> Panel:
        """(-1) * delta(correlation(high, volume, 5), 5) * rank(stddev(close, 20))"""
        return -1 * delta(correlation(self.high, self.volume, 5), 5) * rank(stddev(self.close, 20))

    def alpha023(self) -> Panel:
        """if ts_mean(high,20) < high: -delta(high,2) else 0"""
        cond = ts_sum(self.high, 20) / 20 < self.high
        return where(cond, -delta(self.high, 2), 0)

    def alpha024(self) -> Panel:
        """价格斜率<=5%: -(close - ts_min(close,100)); 否则 -delta(close,3)"""
        slope = delta(ts_sum(self.close, 100) / 100, 100) / delay(self.close, 100)
        cond = slope <= 0.05
        return where(cond, -(self.close - ts_min(self.close, 100)), -delta(self.close, 3))

    def alpha025(self) -> Panel:
        """复杂量价位置因子，结合 adv40、高低价相关性和7日价格变化。"""
        adv40 = self._adv(40)
        price = (2 * self.close + self.low + self.high) / 4
        part1 = rank(price * (adv40 / self.volume + 1))
        part2 = (
            (rank(correlation(self.high, self.close, 5)) + rank(correlation(self.low, self.close, 5))) / 2
            + rank(delta(self.close, 7))
        )
        return part1 * part2

    def alpha026(self) -> Panel:
        """(-1) * (rank(ts_rank(exp(close),1)) - rank(rank(correlation(high,volume,5))))"""
        return -1 * (rank(ts_rank(np.exp(self.close), 1)) - rank(rank(correlation(self.high, self.volume, 5))))

    def alpha027(self) -> Panel:
        """if rank(mean(correlation(rank(volume),rank(vwap),6),2)) > 0.5: -1 else 1"""
        cond = rank(mean(correlation(rank(self.volume), rank(self.vwap), 6), 2)) > 0.5
        return where(cond, -1, 1)

    def alpha028(self) -> Panel:
        """scale(correlation(adv20, low, 5) + (high+low)/2 - close)"""
        adv20 = self._adv(20)
        return scale(correlation(adv20, self.low, 5) + (self.high + self.low) / 2 - self.close)

    def alpha029(self) -> Panel:
        """ts_min(rank(rank(scale(log(ts_sum(rank(rank(-rank(delta(close,5)))),2))))),5)
           + ts_rank(delay(-returns,6),5)"""
        inner = -rank(delta(self.close, 5))
        part1 = ts_min(rank(rank(scale(log(ts_sum(rank(rank(inner)), 2))))), 5)
        part2 = ts_rank(delay(-self.returns, 6), 5)
        return part1 + part2

    def alpha030(self) -> Panel:
        """(1 - rank(sign_sum_3days)) * ts_sum(vol,5) / ts_sum(vol,20)"""
        s = (
            sign(self.close - delay(self.close, 1))
            + sign(delay(self.close, 1) - delay(self.close, 2))
            + sign(delay(self.close, 2) - delay(self.close, 3))
        )
        return (1 - rank(s)) * ts_sum(self.volume, 5) / ts_sum(self.volume, 20)

    # ── Alpha 031 ── Alpha 040 ───────────────────────────────────────────────

    def alpha031(self) -> Panel:
        """(-1)*(rank(correlation(close,adv10,5)) - rank(delta(delta(close,1),1)))
              * rank(close - ts_min(close,10) + 0.001)"""
        adv10 = self._adv(10)
        return (
            -1
            * (rank(correlation(self.close, adv10, 5)) - rank(delta(delta(self.close, 1), 1)))
            * rank(self.close - ts_min(self.close, 10) + 0.001)
        )

    def alpha032(self) -> Panel:
        """scale(rank((ts_sum(close,7)/7 - close))) + 2*rank(correlation(vwap,delay(close,5),230))"""
        return (
            scale(rank(ts_sum(self.close, 7) / 7 - self.close))
            + 2 * rank(correlation(self.vwap, delay(self.close, 5), 230))
        )

    def alpha033(self) -> Panel:
        """rank(-(1 - open/close)^2)"""
        return rank(-signedpower(1 - self.open / self.close, 2))

    def alpha034(self) -> Panel:
        """(-1)*((rank(open - ts_max(close,2)) + rank(open - ts_min(close,2)))
               * rank((open - delay(close,1)) + (delay(close,1) - close)))"""
        return -1 * (
            (rank(self.open - ts_max(self.close, 2)) + rank(self.open - ts_min(self.close, 2)))
            * rank((self.open - delay(self.close, 1)) + (delay(self.close, 1) - self.close))
        )

    def alpha035(self) -> Panel:
        """(-1)*(rank(volume)*(1-rank(close-low)) + rank(open-low)*(1-rank(returns)))"""
        return -1 * (
            rank(self.volume) * (1 - rank(self.close - self.low))
            + rank(self.open - self.low) * (1 - rank(self.returns))
        )

    def alpha036(self) -> Panel:
        """2.21*rank(correlation(open,volume,5)) - 0.01*rank(delta(returns,3))
           + 1.54*rank(open - low)"""
        # Note: paper also includes vwap & low terms; using best-effort interpretation
        adv20 = self._adv(20)
        return (
            2.21 * rank(correlation(self.open, self.volume, 5))
            - 0.01 * rank(delta(self.returns, 3))
            + 1.54 * rank(self.open - self.low)
        )

    def alpha037(self) -> Panel:
        """rank(correlation(delay(open-close,1), close, 200)) + rank(open-close)"""
        return rank(correlation(delay(self.open - self.close, 1), self.close, 200)) + rank(self.open - self.close)

    def alpha038(self) -> Panel:
        """(-1)*rank(ts_rank(close,10)) * rank(close/open)"""
        return -1 * rank(ts_rank(self.close, 10)) * rank(self.close / self.open)

    def alpha039(self) -> Panel:
        """(-1)*rank(delta(close,7) * (1 - rank(decay_linear(volume/adv20,9))))
           * (1 + rank(ts_sum(returns,250)))"""
        adv20 = self._adv(20)
        return (
            -1 * rank(delta(self.close, 7) * (1 - rank(decay_linear(self.volume / adv20, 9))))
            * (1 + rank(ts_sum(self.returns, 250)))
        )

    def alpha040(self) -> Panel:
        """(-1)*rank(stddev(high,10)) * correlation(high, volume, 10)"""
        return -1 * rank(stddev(self.high, 10)) * correlation(self.high, self.volume, 10)

    # ── Alpha 041 ── Alpha 050 ───────────────────────────────────────────────

    def alpha041(self) -> Panel:
        """(high*low)^0.5 - vwap"""
        return (self.high * self.low) ** 0.5 - self.vwap

    def alpha042(self) -> Panel:
        """(vwap - close) / (vwap + close) * 0.5"""
        return (self.vwap - self.close) / (self.vwap + self.close) * 0.5

    def alpha043(self) -> Panel:
        """ts_rank(volume/adv20, 20) * ts_rank(-delta(close,7), 8)"""
        adv20 = self._adv(20)
        return ts_rank(self.volume / adv20, 20) * ts_rank(-delta(self.close, 7), 8)

    def alpha044(self) -> Panel:
        """(-1) * correlation(high, rank(volume), 5)"""
        return -1 * correlation(self.high, rank(self.volume), 5)

    def alpha045(self) -> Panel:
        """(-1) * rank(ts_sum(delay(close,5),20)/20) * correlation(close,volume,2)
               * rank(correlation(ts_sum(close,5), ts_sum(close,20), 2))"""
        return (
            -1
            * rank(ts_sum(delay(self.close, 5), 20) / 20)
            * correlation(self.close, self.volume, 2)
            * rank(correlation(ts_sum(self.close, 5), ts_sum(self.close, 20), 2))
        )

    def alpha046(self) -> Panel:
        """比较两段价格斜率：(d20-d10)/10 vs (d10-now)/10"""
        slope_far  = (delay(self.close, 20) - delay(self.close, 10)) / 10
        slope_near = (delay(self.close, 10) - self.close) / 10
        diff = slope_far - slope_near
        cond_sell = diff > 0.25
        cond_buy  = diff < 0
        return where(cond_sell, -1, where(cond_buy, 1, -delta(self.close, 1)))

    def alpha047(self) -> Panel:
        """复杂多因子：价格倒数×量/adv20 × 高价位置 / 5日均高 - rank(vwap变化)"""
        adv20 = self._adv(20)
        part1 = (
            (1 / self.close)
            * self.volume
            / adv20
            * self.high
            * rank(self.high - self.close)
            / (ts_sum(self.high, 5) / 5)
        )
        return rank(part1) - rank(delta(self.vwap, 5))

    def alpha048(self) -> Panel:
        """类似alpha030但加行业中性化"""
        s = (
            sign(self.close - delay(self.close, 1))
            + sign(delay(self.close, 1) - delay(self.close, 2))
            + sign(delay(self.close, 2) - delay(self.close, 3))
        )
        return (
            -1 * rank(s) * ts_sum(self.volume, 5) / ts_sum(self.volume, 20)
            * self._ind_neu(self.close)
        )

    def alpha049(self) -> Panel:
        """价格斜率差 < -1: 1; 否则 -delta(close,1)"""
        slope_far  = (delay(self.close, 20) - delay(self.close, 10)) / 10
        slope_near = (delay(self.close, 10) - self.close) / 10
        cond = (slope_far - slope_near) < -1
        return where(cond, 1, -delta(self.close, 1))

    def alpha050(self) -> Panel:
        """(-1) * ts_max(rank(correlation(rank(volume), rank(vwap), 5)), 5)"""
        return -1 * ts_max(rank(correlation(rank(self.volume), rank(self.vwap), 5)), 5)

    # ── Alpha 051 ── Alpha 060 ───────────────────────────────────────────────

    def alpha051(self) -> Panel:
        """价格斜率差 < -0.05: 1; 否则 -1"""
        slope_far  = (delay(self.close, 20) - delay(self.close, 10)) / 10
        slope_near = (delay(self.close, 10) - self.close) / 10
        cond = (slope_far - slope_near) < -0.05
        return where(cond, 1, -1)

    def alpha052(self) -> Panel:
        """(ts_min(low,5)变化量) * rank(长期收益加速) * ts_rank(volume,5)"""
        low_chg  = -ts_min(self.low, 5) + delay(ts_min(self.low, 5), 5)
        ret_accel = rank((ts_sum(self.returns, 240) - ts_sum(self.returns, 20)) / 220)
        return low_chg * ret_accel * ts_rank(self.volume, 5)

    def alpha053(self) -> Panel:
        """(-1) * delta((close-low - (high-close)) / (close-low+1e-8), 9)"""
        ratio = (self.close - self.low - (self.high - self.close)) / (self.close - self.low + 1e-8)
        return -1 * delta(ratio, 9)

    def alpha054(self) -> Panel:
        """(-1) * (low-close)*(open^5) / ((low-high)*(close^5) + 1e-8)"""
        denom = (self.low - self.high) * (self.close ** 5) + 1e-8
        return -1 * (self.low - self.close) * (self.open ** 5) / denom

    def alpha055(self) -> Panel:
        """(-1) * correlation(rank((close-ts_min(low,12))/(ts_max(high,12)-ts_min(low,12)+1e-8)),
                              rank(volume), 6)"""
        stoch = (self.close - ts_min(self.low, 12)) / (ts_max(self.high, 12) - ts_min(self.low, 12) + 1e-8)
        return -1 * correlation(rank(stoch), rank(self.volume), 6)

    def alpha056(self) -> Panel:
        """(-1)*(rank(ts_sum(returns,5)-ts_sum(returns,20)) + rank(close-ts_min(close,5)))
               * IndNeutralize(close, ind)"""
        part = rank(ts_sum(self.returns, 5) - ts_sum(self.returns, 20)) + rank(self.close - ts_min(self.close, 5))
        return -1 * part * self._ind_neu(self.close)

    def alpha057(self) -> Panel:
        """0 - (1 - rank((close-ts_min(close,5))/(ts_max(close,5)-ts_min(close,5)+1e-8)))"""
        stoch = (self.close - ts_min(self.close, 5)) / (ts_max(self.close, 5) - ts_min(self.close, 5) + 1e-8)
        return 0 - (1 - rank(stoch))

    def alpha058(self) -> Panel:
        """(-1)*ts_rank(decay_linear(correlation(IndNeutralize(vwap,ind),volume,4),8),6)"""
        vwap_n = self._ind_neu(self.vwap)
        return -1 * ts_rank(decay_linear(correlation(vwap_n, self.volume, 4), 8), 6)

    def alpha059(self) -> Panel:
        """类似alpha058，vwap经加权（0.728317）后中性化"""
        vwap_w = self.vwap * 0.728317 + self.vwap * (1 - 0.728317)  # == self.vwap
        vwap_n = self._ind_neu(vwap_w)
        return -1 * ts_rank(decay_linear(correlation(vwap_n, self.volume, 4), 16), 8)

    def alpha060(self) -> Panel:
        """(-1)*rank(ts_rank(correlation(rank(high),rank(volume),9),14))
               * rank(ts_rank(correlation(rank(low),rank(volume),7),8))"""
        c1 = rank(ts_rank(correlation(rank(self.high), rank(self.volume), 9), 14))
        c2 = rank(ts_rank(correlation(rank(self.low),  rank(self.volume), 7), 8))
        return -1 * c1 * c2

    # ── Alpha 061 ── Alpha 070 ───────────────────────────────────────────────

    def alpha061(self) -> Panel:
        """(-1)*rank(correlation(rank(vwap),rank(volume),4))
               * rank(correlation(rank(low),rank(volume),5))"""
        c1 = rank(correlation(rank(self.vwap), rank(self.volume), 4))
        c2 = rank(correlation(rank(self.low),  rank(self.volume), 5))
        return -1 * c1 * c2

    def alpha062(self) -> Panel:
        """if rank(corr(vwap,adv20,10)) < rank(corr(rank(low),rank(adv50),17)): -1 else 1"""
        adv20 = self._adv(20)
        adv50 = self._adv(50)
        cond = rank(correlation(self.vwap, adv20, 10)) < rank(correlation(rank(self.low), rank(adv50), 17))
        return where(cond, -1, 1)

    def alpha063(self) -> Panel:
        """类似alpha062，vwap行业中性化后比较"""
        adv50 = self._adv(50)
        vwap_n = self._ind_neu(self.vwap * 0.724108 + self.vwap * (1 - 0.724108))
        c1 = rank(correlation(vwap_n, rank(self.volume), 6))
        c2 = rank(correlation(rank(self.low), rank(adv50), 20))
        return where(c1 < c2, -1, 1)

    def alpha064(self) -> Panel:
        """比较复合量的相关性排名"""
        adv40 = self._adv(40)
        adv50 = self._adv(50)
        price = self.open * 0.178404 + self.low * (1 - 0.178404)
        c1 = rank(correlation(ts_sum(price, 13), ts_sum(adv40, 13), 5))
        c2 = rank(correlation(rank(self.low), rank(adv50), 12))
        return where(c1 < c2, -1, 1)

    def alpha065(self) -> Panel:
        """if rank(corr(open,vol,11)) < rank(corr(rank(low),rank(adv30),15)): -1 else 1"""
        adv30 = self._adv(30)
        c1 = rank(correlation(self.open, self.volume, 11))
        c2 = rank(correlation(rank(self.low), rank(adv30), 15))
        return where(c1 < c2, -1, 1)

    def alpha066(self) -> Panel:
        """if rank(corr(open,vol,5)) < rank(corr(rank(vwap),rank(vol),6)): -1 else 1"""
        c1 = rank(correlation(self.open,  self.volume, 5))
        c2 = rank(correlation(rank(self.vwap), rank(self.volume), 6))
        return where(c1 < c2, -1, 1)

    def alpha067(self) -> Panel:
        """if rank(corr(IndNeutralize(high,ind),vol,8)) < rank(corr(rank(low),rank(adv30),18)): -1 else 1"""
        adv30 = self._adv(30)
        high_n = self._ind_neu(self.high)
        c1 = rank(correlation(high_n, self.volume, 8))
        c2 = rank(correlation(rank(self.low), rank(adv30), 18))
        return where(c1 < c2, -1, 1)

    def alpha068(self) -> Panel:
        """比较两个ts_rank后相关性的排名"""
        adv20 = self._adv(20)
        c1 = rank(correlation(ts_rank(self.high, 3), ts_rank(self.volume, 3), 4))
        c2 = rank(correlation(rank(self.low), rank(adv20), 14))
        return where(c1 < c2, -1, 1)

    def alpha069(self) -> Panel:
        """if rank(corr(rank(vwap),rank(vol),12)) < rank(corr(rank(low),adv40,19)): -1 else 1"""
        adv40 = self._adv(40)
        c1 = rank(correlation(rank(self.vwap), rank(self.volume), 12))
        c2 = rank(correlation(rank(self.low), adv40, 19))
        return where(c1 < c2, -1, 1)

    def alpha070(self) -> Panel:
        """(-1) * rank(delta(vwap,1))^ts_rank(corr(IndNeutralize(close,ind),adv50,18),18)"""
        adv50 = self._adv(50)
        close_n = self._ind_neu(self.close)
        exp = ts_rank(correlation(close_n, adv50, 18), 18)
        base = rank(delta(self.vwap, 1))
        return -1 * base ** exp

    # ── Alpha 071 ── Alpha 080 ───────────────────────────────────────────────

    def alpha071(self) -> Panel:
        """max(rank(decay_linear(corr(ts_rank(close,3),ts_rank(adv50,3),12),7)),
               rank(decay_linear((h+l)/2+open-close, 15)))"""
        adv50 = self._adv(50)
        p1 = rank(decay_linear(correlation(ts_rank(self.close, 3), ts_rank(adv50, 3), 12), 7))
        p2 = rank(decay_linear((self.high + self.low) / 2 + self.open - self.close, 15))
        return p1.combine(p2, np.maximum)

    def alpha072(self) -> Panel:
        """rank(decay_linear(corr(rank(high),rank(adv30),9),4))
         - rank(decay_linear(corr(rank(low),rank(adv30),10),8))"""
        adv30 = self._adv(30)
        p1 = rank(decay_linear(correlation(rank(self.high), rank(adv30), 9), 4))
        p2 = rank(decay_linear(correlation(rank(self.low),  rank(adv30), 10), 8))
        return p1 - p2

    def alpha073(self) -> Panel:
        """rank(decay_linear(delta(vwap,3),2)) + rank(decay_linear((-low+open)/(high-low+1e-8),1))"""
        ratio = (-self.low + self.open) / (self.high - self.low + 1e-8)
        return rank(decay_linear(delta(self.vwap, 3), 2)) + rank(decay_linear(ratio, 1))

    def alpha074(self) -> Panel:
        """(-1)*(rank(corr(low,adv30,17)) + rank(delay(rank(open+close),12))
               - rank(decay_linear(corr(rank(vwap),rank(adv50),7),18)))"""
        adv30 = self._adv(30)
        adv50 = self._adv(50)
        p1 = rank(correlation(self.low, adv30, 17))
        p2 = rank(delay(rank(self.open + self.close), 12))
        p3 = rank(decay_linear(correlation(rank(self.vwap), rank(adv50), 7), 18))
        return -1 * (p1 + p2 - p3)

    def alpha075(self) -> Panel:
        """(rank(corr(rank(vwap),rank(vol),4)) + rank(corr(rank(low),rank(adv50),19)))
         - rank(decay_linear((high+low)/2, 12))"""
        adv50 = self._adv(50)
        p1 = rank(correlation(rank(self.vwap), rank(self.volume), 4))
        p2 = rank(correlation(rank(self.low), rank(adv50), 19))
        p3 = rank(decay_linear((self.high + self.low) / 2, 12))
        return p1 + p2 - p3

    def alpha076(self) -> Panel:
        """(-rank(decay_linear(delta(vwap,2),16))
         - rank(decay_linear(-(rank(close+open-low)-rank(vwap)+rank(close-vwap)),17)))
         * IndNeutralize(close,ind)"""
        inner = -(rank(self.close + self.open - self.low) - rank(self.vwap) + rank(self.close - self.vwap))
        p1 = -rank(decay_linear(delta(self.vwap, 2), 16))
        p2 = -rank(decay_linear(inner, 17))
        return (p1 + p2) * self._ind_neu(self.close)

    def alpha077(self) -> Panel:
        """(-1)*rank(decay_linear((h+l)/2+high-vwap-high,2))
           + rank(decay_linear(corr(rank(low),rank(adv50),20),9))"""
        adv50 = self._adv(50)
        ratio = (self.high + self.low) / 2 + self.high - self.vwap - self.high
        p1 = -rank(decay_linear(ratio, 2))
        p2 = rank(decay_linear(correlation(rank(self.low), rank(adv50), 20), 9))
        return p1 + p2

    def alpha078(self) -> Panel:
        """(-1)*rank(decay_linear(corr(rank(vwap),rank(adv20),4),5))
         - rank(decay_linear(-low,9)) + rank(decay_linear(open,16))"""
        adv20 = self._adv(20)
        p1 = -rank(decay_linear(correlation(rank(self.vwap), rank(adv20), 4), 5))
        p2 = -rank(decay_linear(-self.low, 9))
        p3 = rank(decay_linear(self.open, 16))
        return p1 + p2 + p3

    def alpha079(self) -> Panel:
        """rank(delta(IndNeutralize(close,ind),2)) * rank(corr(IndNeutralize(vwap,ind),adv50,15))
         - rank(decay_linear(-low,4))"""
        adv50  = self._adv(50)
        close_n = self._ind_neu(self.close)
        vwap_n  = self._ind_neu(self.vwap)
        p1 = rank(delta(close_n, 2)) * rank(correlation(vwap_n, adv50, 15))
        p2 = rank(decay_linear(-self.low, 4))
        return p1 - p2

    def alpha080(self) -> Panel:
        """(-1)*(rank(sign(delta(IndNeutralize(open,ind),2))*sign(delta(IndNeutralize(close,ind),3)))
               + rank(ts_rank(volume,5)))"""
        open_n  = self._ind_neu(self.open)
        close_n = self._ind_neu(self.close)
        p1 = rank(sign(delta(open_n, 2)) * sign(delta(close_n, 3)))
        p2 = rank(ts_rank(self.volume, 5))
        return -1 * (p1 + p2)

    # ── Alpha 081 ── Alpha 090 ───────────────────────────────────────────────

    def alpha081(self) -> Panel:
        """(-1)*(rank(log(product(rank(corr(rank(high),rank(adv10),8)),2))) - 0.5)"""
        adv10 = self._adv(10)
        return -1 * (rank(log(product(rank(correlation(rank(self.high), rank(adv10), 8)), 2))) - 0.5)

    def alpha082(self) -> Panel:
        """(-1)*(rank(log(rank(corr(rank(high),rank(adv10),8))))
               + rank(ts_rank(vol,6)) - rank(corr(open,vol,6)))"""
        adv10 = self._adv(10)
        p1 = rank(log(rank(correlation(rank(self.high), rank(adv10), 8))))
        p2 = rank(ts_rank(self.volume, 6))
        p3 = rank(correlation(self.open, self.volume, 6))
        return -1 * (p1 + p2 - p3)

    def alpha083(self) -> Panel:
        """rank(delay(high,5)*sign(delta(close,5))) + rank(vwap-close)
         - rank(corr(open,vol,13))"""
        p1 = rank(delay(self.high, 5) * sign(delta(self.close, 5)))
        p2 = rank(self.vwap - self.close)
        p3 = rank(correlation(self.open, self.volume, 13))
        return p1 + p2 - p3

    def alpha084(self) -> Panel:
        """rank(corr(vwap,adv20,6)) + rank(corr(open,vol,15))"""
        adv20 = self._adv(20)
        return rank(correlation(self.vwap, adv20, 6)) + rank(correlation(self.open, self.volume, 15))

    def alpha085(self) -> Panel:
        """(rank(corr(close,adv15,9)) + rank(corr(rank(high),rank(vol),11)))
         - rank(delta(close,6))"""
        adv15 = self._adv(15)
        p1 = rank(correlation(self.close, adv15, 9))
        p2 = rank(correlation(rank(self.high), rank(self.volume), 11))
        p3 = rank(delta(self.close, 6))
        return p1 + p2 - p3

    def alpha086(self) -> Panel:
        """(rank(corr(close,adv30,7)) + rank(corr(open,vol,13))) - rank(delta(close,6))"""
        adv30 = self._adv(30)
        p1 = rank(correlation(self.close, adv30, 7))
        p2 = rank(correlation(self.open, self.volume, 13))
        p3 = rank(delta(self.close, 6))
        return p1 + p2 - p3

    def alpha087(self) -> Panel:
        """max(rank(delta(close,3)),rank(ts_rank(vol*0.47,5)))
         - min(rank(delta(adv50,2)),rank(corr(IndNeutralize(vwap,ind),vol,11)))"""
        adv50  = self._adv(50)
        vwap_n = self._ind_neu(self.vwap)
        hi = (rank(delta(self.close, 3))).combine(rank(ts_rank(self.volume * 0.47, 5)), np.maximum)
        lo = (rank(delta(adv50, 2))).combine(rank(correlation(vwap_n, self.volume, 11)), np.minimum)
        return hi - lo

    def alpha088(self) -> Panel:
        """min(rank(decay_linear(delta(open,2),3)), rank(corr(close,vol,20)))
         + rank(decay_linear(open-low,2))"""
        p_min = (rank(decay_linear(delta(self.open, 2), 3))).combine(
            rank(correlation(self.close, self.volume, 20)), np.minimum
        )
        return p_min + rank(decay_linear(self.open - self.low, 2))

    def alpha089(self) -> Panel:
        """(-1)*(rank(ts_rank(decay_linear(corr(IndNeutralize(vwap,ind),vol,4),8),7))
              - rank(decay_linear(ts_rank(corr(rank(low),rank(adv30),12),19),16))"""
        adv30  = self._adv(30)
        vwap_n = self._ind_neu(self.vwap)
        p1 = rank(ts_rank(decay_linear(correlation(vwap_n, self.volume, 4), 8), 7))
        p2 = rank(decay_linear(ts_rank(correlation(rank(self.low), rank(adv30), 12), 19), 16))
        return -1 * (p1 - p2)

    def alpha090(self) -> Panel:
        """rank(decay_linear(corr(rank(vwap),rank(vol),14),5))
         - rank(decay_linear(ts_rank(ts_min(low,5),19),13))
         + rank(corr(IndNeutralize(close,ind),vol,16))"""
        close_n = self._ind_neu(self.close)
        p1 = rank(decay_linear(correlation(rank(self.vwap), rank(self.volume), 14), 5))
        p2 = rank(decay_linear(ts_rank(ts_min(self.low, 5), 19), 13))
        p3 = rank(correlation(close_n, self.volume, 16))
        return p1 - p2 + p3

    # ── Alpha 091 ── Alpha 101 ───────────────────────────────────────────────

    def alpha091(self) -> Panel:
        """(-1)*(rank(ts_rank(decay_linear(decay_linear(corr(IndNeutralize(close,ind),vol,3),7),6),4))
              - rank(decay_linear(ts_rank(corr(rank(vwap),rank(adv30),19),12),20))"""
        adv30   = self._adv(30)
        close_n = self._ind_neu(self.close)
        inner = decay_linear(decay_linear(correlation(close_n, self.volume, 3), 7), 6)
        p1 = rank(ts_rank(inner, 4))
        p2 = rank(decay_linear(ts_rank(correlation(rank(self.vwap), rank(adv30), 19), 12), 20))
        return -1 * (p1 - p2)

    def alpha092(self) -> Panel:
        """min(rank(decay_linear(cond_close_lt_lo_open, 15)),
               rank(decay_linear(corr(rank(high),rank(adv30),14),16)))"""
        adv30 = self._adv(30)
        cond = (self.high + self.low) / 2 + self.close < self.low + self.open
        p1 = rank(decay_linear(cond.astype(float), 15))
        p2 = rank(decay_linear(correlation(rank(self.high), rank(adv30), 14), 16))
        return p1.combine(p2, np.minimum)

    def alpha093(self) -> Panel:
        """(5/6)*ts_rank(decay_linear(corr(IndNeutralize(vwap,ind),adv50,19),8),6)
         + (1/6)*rank(decay_linear(corr(rank(vwap),rank(vol),20),4))"""
        adv50  = self._adv(50)
        vwap_n = self._ind_neu(self.vwap)
        p1 = ts_rank(decay_linear(correlation(vwap_n, adv50, 19), 8), 6)
        p2 = rank(decay_linear(correlation(rank(self.vwap), rank(self.volume), 20), 4))
        return (5 / 6) * p1 + (1 / 6) * p2

    def alpha094(self) -> Panel:
        """(rank(decay_linear(corr(vwap,low,18),12))
         - rank(decay_linear(corr(rank(low),rank(adv30),14),16)))
         + rank(decay_linear(delta(vwap,3),16))"""
        adv30 = self._adv(30)
        p1 = rank(decay_linear(correlation(self.vwap, self.low, 18), 12))
        p2 = rank(decay_linear(correlation(rank(self.low), rank(adv30), 14), 16))
        p3 = rank(decay_linear(delta(self.vwap, 3), 16))
        return p1 - p2 + p3

    def alpha095(self) -> Panel:
        """(rank(decay_linear(corr(open,vol,13),18))
         - rank(decay_linear(corr(rank(low),rank(adv30),16),12)))
         + rank(decay_linear(delta(vwap,2),17))"""
        adv30 = self._adv(30)
        p1 = rank(decay_linear(correlation(self.open, self.volume, 13), 18))
        p2 = rank(decay_linear(correlation(rank(self.low), rank(adv30), 16), 12))
        p3 = rank(decay_linear(delta(self.vwap, 2), 17))
        return p1 - p2 + p3

    def alpha096(self) -> Panel:
        """(rank(decay_linear(corr(vwap,vol,17),18))
         - rank(decay_linear(corr(rank(low),rank(adv30),18),20)))
         + rank(decay_linear(delta(vwap,3),20))"""
        adv30 = self._adv(30)
        p1 = rank(decay_linear(correlation(self.vwap, self.volume, 17), 18))
        p2 = rank(decay_linear(correlation(rank(self.low), rank(adv30), 18), 20))
        p3 = rank(decay_linear(delta(self.vwap, 3), 20))
        return p1 - p2 + p3

    def alpha097(self) -> Panel:
        """(-1)*(rank(decay_linear(delta(IndNeutralize(close,ind),3),16))
              - rank(decay_linear(corr(IndNeutralize(vwap,ind),vol,20),18)))"""
        close_n = self._ind_neu(self.close)
        vwap_n  = self._ind_neu(self.vwap)
        p1 = rank(decay_linear(delta(close_n, 3), 16))
        p2 = rank(decay_linear(correlation(vwap_n, self.volume, 20), 18))
        return -1 * (p1 - p2)

    def alpha098(self) -> Panel:
        """rank(decay_linear(corr(vwap,ts_sum(adv5,26),5),8))
         - rank(decay_linear(ts_rank(ts_argmin(corr(rank(open),rank(adv15),21),9),7),8))"""
        adv5  = self._adv(5)
        adv15 = self._adv(15)
        p1 = rank(decay_linear(correlation(self.vwap, ts_sum(adv5, 26), 5), 8))
        p2 = rank(decay_linear(ts_rank(ts_argmin(correlation(rank(self.open), rank(adv15), 21), 9), 7), 8))
        return p1 - p2

    def alpha099(self) -> Panel:
        """(rank(decay_linear(corr(high,vol,20),18))
         - rank(decay_linear(corr(low,vol,20),20)))
         + rank(decay_linear(corr(low,vol,9),1))"""
        p1 = rank(decay_linear(correlation(self.high, self.volume, 20), 18))
        p2 = rank(decay_linear(correlation(self.low,  self.volume, 20), 20))
        p3 = rank(decay_linear(correlation(self.low,  self.volume, 9),  1))
        return p1 - p2 + p3

    def alpha100(self) -> Panel:
        """(rank(decay_linear(delta(vwap,2),20))
         + rank(decay_linear(corr(IndNeutralize(vwap,ind),vol,20),18)))
         - rank(decay_linear(delta(close,2),5))"""
        vwap_n = self._ind_neu(self.vwap)
        p1 = rank(decay_linear(delta(self.vwap, 2), 20))
        p2 = rank(decay_linear(correlation(vwap_n, self.volume, 20), 18))
        p3 = rank(decay_linear(delta(self.close, 2), 5))
        return p1 + p2 - p3

    def alpha101(self) -> Panel:
        """(close - open) / (high - low + 0.001)
        当日K线实体长度与日内振幅的比值，衡量动量效率。"""
        return (self.close - self.open) / (self.high - self.low + 0.001)

    # ── 批量计算 ─────────────────────────────────────────────────────────────

    def compute_all(self, alphas: list[int] | None = None) -> dict[str, Panel]:
        if alphas is None:
            alphas = list(range(1, 102))

        results: dict[str, Panel] = {}
        for n in alphas:
            name = f"alpha{n:03d}"
            method = getattr(self, name, None)
            if method is None:
                continue
            try:
                results[name] = method()
            except Exception as exc:
                results[name] = pd.DataFrame(
                    np.nan,
                    index=self.close.index,
                    columns=self.close.columns,
                )
                import warnings
                warnings.warn(f"{name} computation failed: {exc}")
        return results


# ── 因子说明字典（供外部调用）────────────────────────────────────────────────
ALPHA_DESCRIPTIONS: dict[str, str] = {
    "alpha001": "收益率为负时用波动率替代价格，对5日最大argmax排名，捕捉下行风险中的波动偏好。值越高→预期下跌（反向因子），高值表示股票在恐慌时期仍被追捧，短期过热",
    "alpha002": "成交量二阶差分排名与收益排名的负相关，捕捉量价背离。值越高→预期下跌（反向因子），高值表示量增但价格未跟上，上涨动能衰竭",
    "alpha003": "开盘价横截面排名与成交量排名的负相关。值越高→预期下跌（反向因子），高值表示开盘价在市场中偏高而成交量相对偏小，高价低量超买",
    "alpha004": "低价时序排名取反，衡量低价的相对历史强度。值越高→预期下跌（反向因子），高值表示当前低价相对历史偏高，下行空间较大",
    "alpha005": "开盘与10日均价偏离 × 收盘与均价偏离的乘积。值越高→预期下跌（反向因子），高值表示开盘和收盘双双偏离均价，价格虚高",
    "alpha006": "开盘价与成交量的10日负相关，捕捉放量高开的反转信号。值越高→预期下跌（反向因子），高值表示开盘价与量呈强负相关，放量高开后易回落",
    "alpha007": "量超均量时取价差方向×波动排名，否则取反，量能突破动量。值越高→预期上涨（正向因子），高值表示放量上涨，量能支撑价格动量",
    "alpha008": "5日开盘×收益积的10日变化取反，捕捉短期量价加速反转。值越高→预期下跌（反向因子），高值表示近期开盘收益积加速上升，短期超买",
    "alpha009": "5日价格单调涨跌时顺势，震荡时逆势，趋势与均值回归切换。值越高→预期上涨（正向因子），高值在趋势行情中表示强势，震荡中表示超卖反弹",
    "alpha010": "alpha009的4日排名版，短周期趋势识别。值越高→预期上涨（正向因子），高值表示短期趋势或超卖反弹机会",
    "alpha011": "vwap与收盘差极值排名之和 × 成交量变化，量价极值动量。值越高→预期上涨（正向因子），高值表示vwap偏离大且成交量放大，多头动能强",
    "alpha012": "成交量变化方向 × 价格反向变化，量增价跌反转信号。值越高→预期上涨（反转因子），高值表示量增价跌，短期超卖后反弹概率高",
    "alpha013": "收盘价与成交量排名协方差取反，量价协同性逆向因子。值越高→预期下跌（反向因子），高值表示量价协同上涨强烈，短期超买",
    "alpha014": "收益3日变化排名取反 × 开盘量相关，动量衰减与量价信号。值越高→预期下跌（反向因子），高值表示近期涨速快且量价背离，动量衰竭",
    "alpha015": "高价量3日相关排名的3日累加取反，量价相关持续性反转。值越高→预期下跌（反向因子），高值表示高价伴随高量持续，短期过热后回调",
    "alpha016": "高价与成交量排名协方差取反，高位量价协同反转。值越高→预期下跌（反向因子），高值表示高价高量协同强，超买反转信号",
    "alpha017": "价格趋势排名 × 价格加速度 × 成交量比排名三重乘积。值越高→预期下跌（反向因子），三重趋势叠加后过热，均值回归",
    "alpha018": "振幅标准差+实体方向+量价相关综合取反，波动与动量综合反转。值越高→预期下跌（反向因子），高值表示波动大、阳线多且量价同向，热点股超买",
    "alpha019": "7日价格方向 × 长期累计收益排名取反，趋势延续性反转。值越高→预期下跌（反向因子），高值表示近期上涨且长期涨幅大，强势股均值回归",
    "alpha020": "开盘与前日高收低之差三乘积取反，跳空反转信号。值越高→预期下跌（反向因子），高值表示向上跳空动能强，缺口易被回补",
    "alpha021": "布林带位置判断：突破上轨=−1看空，跌破下轨=+1看多，中间取均量排名。值越高→预期上涨（条件正向因子），高值(+1)表示跌破下轨超卖，反弹概率高",
    "alpha022": "高价量5日相关的5日变化 × 收盘波动率，量价相关动量衰减。值越高→预期下跌（反向因子），高值表示高价量相关性近期大幅增加，短期热度过高",
    "alpha023": "当日高价高于20日均高时，取2日高价变化的反向排名。值越高→预期下跌（反向因子），高值表示在高价突破后近期高价仍在上升，超买信号",
    "alpha024": "斜率平缓时距最低点距离反转，斜率陡时3日变化反转。值越高→预期下跌（反向因子），高值表示价格高于近期低点或近期涨速过快，回调信号",
    "alpha025": "量比调整价格排名 × 高低价相关排名 × 7日价格变化。值越高→预期上涨（正向因子），高值表示量比支撑下价格动量强，多因子共振看涨",
    "alpha026": "价格时序排名 vs 高价量双重排名之差，价格趋势与量价分歧。值越高→预期上涨（正向因子），高值表示价格趋势强于量价相关性，纯价格动量信号",
    "alpha027": "量与vwap 6日相关排名超0.5则返回−1看空，量价中期相关判断。值越高→预期下跌（反向因子），高值(>−1)时量vwap相关弱，但−1时量价同步上涨后反转",
    "alpha028": "均量与低价5日相关 + 中间价偏离收盘标准化，量价位置综合。值越高→预期上涨（正向因子），高值表示均量支撑下价格位置偏低，具有上涨空间",
    "alpha029": "多层嵌套价格排名 + 延迟收益时序排名，复合价格动量衰减。值越高→预期下跌（反向因子），高值表示多周期价格排名叠加高位，综合超买",
    "alpha030": "3日价格方向符号排名 × 短期/长期量比，量价方向与量比结合。值越高→预期上涨（正向因子），高值表示近期上涨且短期放量，量价配合看涨",
    "alpha031": "(价格均量相关−价格加速度) × 价格离低点距离排名。值越高→预期上涨（正向因子），高值表示量能支撑价格且当前远离低点，多头格局",
    "alpha032": "7日均价偏离标准化 + 2×vwap与延迟价格230日相关排名。值越高→预期上涨（正向因子），高值表示均价偏低且vwap长期趋势向上，价值低估信号",
    "alpha033": "开收比反向幂次排名，日内阴线（跌）放大信号。值越高→预期上涨（反转因子），高值表示收盘低于开盘幅度大，超卖后反弹概率高",
    "alpha034": "开盘与近期高低价差三重排名之积取反，开盘跳空反转。值越高→预期下跌（反向因子），高值表示开盘价在高低价中位置偏高，跳空高开反转",
    "alpha035": "量排名×收盘离低反向 + 开收方向×收益，综合量价反转。值越高→预期下跌（反向因子），高值表示高量且价格偏高，量价双重超买",
    "alpha036": "开量相关×2.21 − 收益变化×0.01 + 开低差×1.54 线性组合。值越高→预期上涨（正向因子），高值表示开盘量能配合且开盘接近低价，支撑强",
    "alpha037": "前日开收差与今日收盘200日相关 + 开收差排名，隔日价格传导。值越高→预期上涨（正向因子），高值表示前日阳线动量通过量价相关传导，延续性强",
    "alpha038": "价格趋势排名 × 收开比排名取反，趋势中相对强度反转。值越高→预期下跌（反向因子），高值表示价格趋势向上但收盘相对开盘偏弱，动能衰减",
    "alpha039": "7日价格变化×量比因子排名 × 长期累计收益取反。值越高→预期下跌（反向因子），高值表示短期和长期均强势，长牛股均值回归风险",
    "alpha040": "高价10日波动率排名 × 高价量10日相关取反，高价波动量价背离。值越高→预期下跌（反向因子），高值表示高价波动大且量价同向，波动放大后超买",
    "alpha041": "高低价几何均值 − vwap，价格重心与均价偏离。值越高→预期上涨（正向因子），高值表示高低价均值高于vwap，买方在均价之上交易，多头强势",
    "alpha042": "(vwap − 收盘) / (vwap + 收盘)，vwap相对收盘溢价率。值越高→预期上涨（正向因子），高值表示vwap高于收盘价，机构平均成本在收盘之上，支撑反弹",
    "alpha043": "成交量比时序排名 × 7日价格逆变化时序排名，量能与价格反转共振。值越高→预期上涨（反转因子），高值表示放量且价格近期回调，量增价跌反弹信号",
    "alpha044": "高价与成交量排名负相关取反，高位放量反转。值越高→预期下跌（反向因子），高值表示高价伴随大量，量价同步超买后回调",
    "alpha045": "延迟均价排名 × 量价短期相关 × 均价多周期相关排名取反。值越高→预期下跌（反向因子），高值表示均价多周期均强且量价同向，综合超买",
    "alpha046": "远近斜率差>0.25返回−1看空，<0返回1看多，否则取价格变化。值越高→预期上涨（条件正向因子），高值(+1)表示短期斜率转正，趋势反转向上",
    "alpha047": "价格倒数×超额量×高价位置/均高 − vwap变化排名，量价位置偏离。值越高→预期上涨（正向因子），高值表示低价格高量能，vwap上升，价值洼地放量",
    "alpha048": "3日价格方向排名×量比（行业中性化），行业内量价方向信号。值越高→预期上涨（正向因子），高值表示在同行业中近期涨势配合放量，相对强势",
    "alpha049": "价格斜率差<−1时返回1看多，否则取价格变化反转。值越高→预期上涨（条件正向因子），高值(+1)表示短期斜率骤降，极度超卖后强力反弹",
    "alpha050": "量与vwap相关排名的5日最大值取反，量价相关极值反转。值越高→预期下跌（反向因子），高值取反后实为量vwap相关性弱，量价不同向时反而易跌",
    "alpha051": "远近价格斜率差<−0.05返回1看多，否则返回−1看空，二值趋势判断。值为+1→预期上涨，为−1→预期下跌，高值(+1)表示短期急跌后斜率逆转，超卖反弹",
    "alpha052": "5日低价变化量 × 长期收益加速排名 × 成交量时序排名，低价突破动量。值越高→预期上涨（正向因子），高值表示低价突破且长期动量加速放量，强势突破",
    "alpha053": "价格在高低间位置比的9日变化取反，位置动量反转。值越高→预期下跌（反向因子），高值表示价格在高低区间位置近期快速上升，超买后回调",
    "alpha054": "低收差×开盘5次方 / 低高差×收盘5次方 取反，高次方放大价格位置信号。值越高→预期下跌（反向因子），高值表示收盘接近最高且开盘价高，高位阳线超买",
    "alpha055": "12日随机指标与成交量排名的负相关，超买区放量反转。值越高→预期下跌（反向因子），高值表示超买区成交量大，高位接盘多后回调概率高",
    "alpha056": "短长期收益差排名+收盘离低排名 × 行业中性化收盘，行业内价格位置。值越高→预期上涨（正向因子），高值表示行业内近期超跌且收盘接近低位，相对低估",
    "alpha057": "5日随机指标排名取反，价格在近期区间相对位置。值越高→预期上涨（反转因子），高值表示收盘接近5日低点，超卖区间内反弹概率高",
    "alpha058": "行业中性化vwap量相关衰减时序排名取反，行业内量价趋势。值越高→预期下跌（反向因子），高值取反表示行业内量价相关趋势弱化，热度消退",
    "alpha059": "alpha058加权版，16日衰减更长周期，行业内量价中期趋势。值越高→预期下跌（反向因子），高值取反表示中期量价同向信号衰减，中线热度减退",
    "alpha060": "高价量9日相关×14日时序排名 × 低价量7日相关×8日时序排名取反。值越高→预期下跌（反向因子），高值表示高低价均与量相关性强，全面超买",
    "alpha061": "vwap量4日相关排名 × 低价量5日相关排名取反，量价双重相关反转。值越高→预期下跌（反向因子），高值表示均价和低价均与量同向，双重超买信号",
    "alpha062": "vwap均量相关 vs 低价大均量相关的条件判断，流动性对比信号。值为+1→预期上涨，为−1→预期下跌，高值(+1)表示低价流动性优于vwap流动性，低位承接强",
    "alpha063": "行业中性化vwap量相关 vs 低价大均量相关，行业内流动性判断。值为+1→预期上涨，为−1→预期下跌，高值(+1)表示行业内低位流动性好，相对强势",
    "alpha064": "复合价格均量相关 vs 低价大均量相关，价量结构对比。值为+1→预期上涨，为−1→预期下跌，高值(+1)表示低价区流动性结构更优，低位筹码稳定",
    "alpha065": "开盘量11日相关 vs 低价均量15日相关，开盘流动性信号。值为+1→预期上涨，为−1→预期下跌，高值(+1)表示开盘位置流动性强于低价区，开盘承接好",
    "alpha066": "开盘量5日相关 vs vwap量排名6日相关，vwap流动性结构判断。值为+1→预期上涨，为−1→预期下跌，高值(+1)表示开盘量能优于vwap区间，短期开盘动力强",
    "alpha067": "行业中性化高价量8日相关 vs 低价均量18日相关，行业高低量能对比。值为+1→预期上涨，为−1→预期下跌，高值(+1)表示低价区量能相对行业内更强，低位有支撑",
    "alpha068": "高价量ts_rank×4日相关 vs 低价均量14日相关，趋势量价结构对比。值为+1→预期上涨，为−1→预期下跌，高值(+1)表示低价成交更活跃，底部筑牢",
    "alpha069": "vwap量排名12日相关 vs 低价大均量19日相关，量价趋势与流动性。值为+1→预期上涨，为−1→预期下跌，高值(+1)表示低价区长期量能充沛，底部支撑强",
    "alpha070": "vwap日变化排名的幂次（指数=量价相关时序排名）取反，非线性量价动量。值越高→预期下跌（反向因子），高值表示vwap非线性上升且量价相关强，过热后回调",
    "alpha071": "收盘趋势衰减相关 vs 中间价开收差衰减的逐元素最大值。值越高→预期上涨（正向因子），高值表示收盘趋势与日内实体均强，多头持续",
    "alpha072": "高价量相关衰减 − 低价量相关衰减，高低价量能不对称。值越高→预期上涨（正向因子），高值表示高价区量能强于低价区，上涨时放量下跌时缩量，多头健康",
    "alpha073": "vwap 3日变化衰减排名 + 开盘离低比衰减排名，价格趋势与开盘位置。值越高→预期上涨（正向因子），高值表示vwap上升且开盘接近低价，空间大动能足",
    "alpha074": "低价量相关排名 + 延迟开收排名 − vwap均量衰减相关排名取反。值越高→预期下跌（反向因子），高值表示低价量能和前期阳线共同过热，综合超买",
    "alpha075": "vwap量相关 + 低价大均量相关 − 中间价衰减排名，流动性综合因子。值为+1→预期上涨，为−1→预期下跌，高值(+1)表示量价流动性强，多方主导",
    "alpha076": "vwap变化衰减+价格结构衰减 × 行业中性化收盘，行业内价格趋势。值越高→预期上涨（正向因子），高值表示行业内vwap和价格结构均向上，相对强势",
    "alpha077": "中间价高价差衰减排名取反 + 低价大均量相关衰减排名，价格位置偏离。值越高→预期上涨（正向因子），高值表示日内价格偏向下沿且低价量能强，逢低做多",
    "alpha078": "vwap均量相关衰减取反 + 低价衰减取反 + 开盘衰减，多因子价格偏离。值越高→预期上涨（正向因子），高值表示vwap量价背离且价格低位，反转看涨",
    "alpha079": "行业中性化收盘变化×vwap均量相关排名 − 低价衰减排名，行业内趋势。值越高→预期上涨（正向因子），高值表示行业内价格上涨量价配合，低价区相对强势",
    "alpha080": "行业中性化开收变化方向 + 成交量时序排名取反，行业内价格动量反转。值越高→预期下跌（反向因子），高值表示行业内阳线多且成交量偏大，超买后均值回归",
    "alpha081": "高价均量8日相关乘积log排名−0.5取反，量价相关乘积信号。值越高→预期下跌（反向因子），高值取反表示量价相关乘积低，放量但高价配合差，看空",
    "alpha082": "高量相关log排名 + 量时序排名 − 开量相关排名取反，多因子量价。值越高→预期下跌（反向因子），高值取反表示量排名虽高但开盘量价相关强，高开后易跌",
    "alpha083": "延迟高价×价格方向 + vwap收盘差 − 开量13日相关排名，综合量价。值越高→预期上涨（正向因子），高值表示前期高价延续且vwap高于收盘，价值支撑",
    "alpha084": "vwap均量6日相关 + 开盘量15日相关，双重流动性正向信号。值越高→预期上涨（正向因子），高值表示vwap和开盘均与量同向，量价双重共振看涨",
    "alpha085": "收盘均量相关 + 高价量排名相关 − 价格6日变化，量价与动量综合。值越高→预期上涨（正向因子），高值表示量价相关强但近期价格涨幅有限，上涨空间大",
    "alpha086": "收盘均量相关 + 开盘量相关 − 价格6日变化，类alpha085版本。值越高→预期上涨（正向因子），高值表示开盘收盘量能充沛但涨价不多，后续补涨潜力",
    "alpha087": "max(价格3日变化, 量47%时序) − min(均量变化, 行业vwap量相关)，极值差。值越高→预期上涨（正向因子），高值表示价格或量的上行极值强，下行极值弱，多头偏强",
    "alpha088": "min(开盘2日变化衰减, 收盘量相关) + 开低差衰减，价格开盘综合。值越高→预期上涨（正向因子），高值表示开盘动能量价配合且开盘接近低价，稳健看涨",
    "alpha089": "行业中性化vwap量相关双重衰减时序 − 低价均量相关衰减，量价行业中性。值越高→预期上涨（正向因子），高值表示行业内vwap量价趋势强于低价量能，中高位放量",
    "alpha090": "vwap量相关衰减 − 低价ts_min衰减 + 行业中性化收盘量相关。值越高→预期上涨（正向因子），高值表示vwap量价配合且非近期最低，行业内收盘也强",
    "alpha091": "行业中性化收盘量相关三重衰减时序 − vwap均量相关衰减取反。值越高→预期上涨（正向因子），高值表示行业内收盘量价持续配合，长期多头结构",
    "alpha092": "min(条件衰减, 高价量相关衰减)，价格位置与量能最小值信号。值越高→预期上涨（正向因子），高值表示价格位置和高价量能双双强，保守估计看涨",
    "alpha093": "行业中性化vwap均量相关衰减时序×5/6 + 量价相关衰减排名×1/6。值越高→预期上涨（正向因子），高值表示行业内量价综合趋势强，主力资金配合",
    "alpha094": "vwap低价相关衰减 − 低价均量相关衰减 + vwap变化衰减，三因子vwap偏离。值越高→预期上涨（正向因子），高值表示vwap趋势向上且高于低价水平，多头结构",
    "alpha095": "开盘量相关衰减 − 低价均量相关衰减 + vwap变化衰减，类alpha094版本。值越高→预期上涨（正向因子），高值表示开盘量能及vwap趋势强，开盘多头",
    "alpha096": "vwap量相关衰减 − 低价均量相关衰减 + vwap 3日变化，vwap量价综合。值越高→预期上涨（正向因子），高值表示vwap量价结构优于低价，且vwap近期上升",
    "alpha097": "行业中性化收盘变化衰减 − 行业中性化vwap量相关衰减取反。值越高→预期下跌（反向因子），高值取反表示行业内收盘涨幅强但量价相关弱，价升量缩警惕",
    "alpha098": "vwap均量相关衰减 − 开盘均量相关argmin时序衰减，vwap趋势与开盘底部。值越高→预期上涨（正向因子），高值表示vwap量价强且开盘远离近期低量时刻，多头延续",
    "alpha099": "高价量相关衰减 − 低价量相关衰减 + 低价量9日短期相关，高低量能不对称。值越高→预期上涨（正向因子），高值表示上涨时放量下跌时缩量，高低量能分化利多",
    "alpha100": "vwap变化衰减 + 行业中性化vwap量相关衰减 − 收盘变化衰减，量价趋势综合。值越高→预期上涨（正向因子），高值表示vwap趋势和量价强而收盘涨幅有限，补涨空间",
    "alpha101": "当日K线实体长度与日内振幅之比，即(收盘−开盘)/(最高−最低+0.001)。值越高→预期上涨（正向因子），高正值表示收盘远高于开盘、阳线强势，惯性动量延续看涨",
}
