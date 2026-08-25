"""
moe_signal.py — MoE 混合专家买卖时机分析 + 遗传算法权重训练

功能一：分析单只股票当前买卖时机
    python moe_signal.py --code 000001.SZ [--date 2026-03-01]
    python moe_signal.py analyze --code 000001.SZ

功能二：跑回测训练最优权重（遗传算法，目标：最大化总收益）
    python moe_signal.py train --start-date 2025-09-01 --end-date 2026-03-01
    python moe_signal.py train  # 默认最近半年

输出 analyze：JSON 格式的综合评分和 BUY/SELL/HOLD 建议
输出 train：优化后的权重写入 moe_weights.json
"""
import sys
import os
import json
import argparse
import random
import copy
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

from data_fetcher import (
    query_daily_basic, query_stock_limit, query_top_list,
    query_daily_kline, query_stock_basic,
)
import indicators as ind
from indicators import init_indicators_db
import config

# ─────────────────────────────────────────────────────────────────────────────
# 权重配置文件
# ─────────────────────────────────────────────────────────────────────────────

_WEIGHTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'moe_weights.json')

_DEFAULT_WEIGHTS: Dict[str, Any] = {
    'expert_weights': {'technical': 0.35, 'alpha': 0.35, 'fundamental': 0.15, 'behavior': 0.15},
    'signal_thresholds': {'buy': 0.65, 'sell': 0.35},
}


def load_weights() -> Dict[str, Any]:
    """加载权重配置文件，文件不存在则返回默认值。"""
    if os.path.exists(_WEIGHTS_PATH):
        try:
            with open(_WEIGHTS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for k, v in _DEFAULT_WEIGHTS.items():
                if k not in data:
                    data[k] = copy.deepcopy(v)
            return data
        except Exception:
            pass
    return copy.deepcopy(_DEFAULT_WEIGHTS)


def save_weights(weights: Dict[str, Any], train_period: Optional[str] = None) -> None:
    """保存权重配置文件。"""
    weights['_version'] = weights.get('_version', 1)
    weights['_trained_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if train_period:
        weights['_train_period'] = train_period
    with open(_WEIGHTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(weights, f, ensure_ascii=False, indent=2)
    print(f'[MoE] 权重已保存到 {_WEIGHTS_PATH}')


# ─────────────────────────────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────────────────────────────

def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _linear(v: float, lo: float, hi: float, reverse: bool = False) -> float:
    """将 v 线性映射到 [0,1]，lo→1(看多), hi→0(看空)；reverse=True 时反转。"""
    if hi == lo:
        return 0.5
    ratio = (v - lo) / (hi - lo)
    score = _clamp(1.0 - ratio)
    return score if not reverse else 1.0 - score


def _get_close(code: str, date: str) -> Optional[float]:
    """获取指定日期或之前最近一个交易日的收盘价。"""
    klines = query_daily_kline(codes=[code], end_date=date, limit=1, order_by="date DESC")
    if klines:
        return klines[0].close
    return None


def _prev_date(date: str, n: int = 1) -> str:
    """往前推 n 个自然日（近似交易日偏移）。"""
    return (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=n * 2)).strftime('%Y-%m-%d')


def _weighted_mean(scores: Dict[str, float], weights: Dict[str, float]) -> float:
    """按权重计算加权平均，权重自动归一化。"""
    total_w = 0.0
    total_v = 0.0
    for k, v in scores.items():
        w = weights.get(k, 1.0)
        total_w += w
        total_v += w * v
    return (total_v / total_w) if total_w > 0 else 0.5


# ─────────────────────────────────────────────────────────────────────────────
# Expert 1：技术指标专家
# ─────────────────────────────────────────────────────────────────────────────

def _score_tech(code: str, date: str, weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    close = _get_close(code, date)
    scores: Dict[str, float] = {}

    # ── 趋势均线类 ────────────────────────────────────────────────────────────
    for period, fname in [(5, 'sma5'), (10, 'sma10'), (20, 'sma20'), (60, 'sma60')]:
        v = ind.get_sma(code, date, period)
        if v is not None and close is not None:
            scores[fname] = 1.0 if close > v else 0.0

    for period, fname in [(5, 'ema5'), (12, 'ema12'), (20, 'ema20'), (26, 'ema26')]:
        v = ind.get_ema(code, date, period)
        if v is not None and close is not None:
            scores[fname] = 1.0 if close > v else 0.0

    ema5 = ind.get_ema(code, date, 5)
    ema20 = ind.get_ema(code, date, 20)
    if ema5 is not None and ema20 is not None:
        scores['ema_cross'] = 1.0 if ema5 > ema20 else 0.0

    for period, fname in [(20, 'wma20')]:
        v = ind.get_wma(code, date, period)
        if v is not None and close is not None:
            scores[fname] = 1.0 if close > v else 0.0

    for period, fname in [(20, 'tema20')]:
        v = ind.get_tema(code, date, period)
        if v is not None and close is not None:
            scores[fname] = 1.0 if close > v else 0.0

    for period, fname in [(20, 'dema20')]:
        v = ind.get_dema(code, date, period)
        if v is not None and close is not None:
            scores[fname] = 1.0 if close > v else 0.0

    v = ind.get_kama(code, date, 10)
    if v is not None and close is not None:
        scores['kama'] = 1.0 if close > v else 0.0

    v = ind.get_bbi(code, date)
    if v is not None and close is not None:
        scores['bbi'] = 1.0 if close > v else 0.0

    v = ind.get_trix(code, date, 12)
    if v is not None:
        scores['trix'] = 1.0 if v > 0 else 0.0

    dmi = ind.get_dmi(code, date, 14)
    if dmi is not None:
        adx = dmi.get('adx', 0) or 0
        pdi = dmi.get('pdi', 0) or 0
        mdi = dmi.get('mdi', 0) or 0
        scores['dmi'] = 1.0 if (adx > 25 and pdi > mdi) else (0.0 if (adx > 25 and mdi > pdi) else 0.5)

    sar_r = ind.get_sar(code, date)
    if sar_r is not None and close is not None:
        sar_v = sar_r.get('sar')
        if sar_v is not None:
            scores['sar'] = 1.0 if close > sar_v else 0.0

    v = ind.get_linearreg_slope(code, date, 14)
    if v is not None:
        scores['linearreg_slope'] = 1.0 if v > 0 else 0.0

    v = ind.get_linearreg(code, date, 14)
    if v is not None and close is not None:
        scores['linearreg'] = 1.0 if v > close else 0.0

    v = ind.get_linearreg_angle(code, date, 14)
    if v is not None:
        scores['linearreg_angle'] = 1.0 if v > 0 else 0.0

    v = ind.get_linearreg_intercept(code, date, 14)
    if v is not None and close is not None:
        scores['linearreg_intercept'] = 1.0 if close > v else 0.0

    aroon = ind.get_aroon(code, date, 14)
    if aroon is not None:
        au = aroon.get('aroon_up', 50) or 50
        ad = aroon.get('aroon_down', 50) or 50
        scores['aroon'] = 1.0 if au > ad else (0.0 if ad > au else 0.5)

    v = ind.get_tsf(code, date, 14)
    if v is not None and close is not None:
        scores['tsf'] = 1.0 if v > close else 0.0

    v = ind.get_ht_trendmode(code, date)
    if v is not None:
        scores['ht_trendmode'] = 1.0 if v == 1 else 0.5

    v = ind.get_ht_dcphase(code, date)
    if v is not None:
        scores['ht_dcphase'] = 1.0 if (0 <= v % 360 <= 180) else 0.0

    ht_sine = ind.get_ht_sine(code, date)
    if ht_sine is not None:
        sine_v = ht_sine.get('sine', 0) or 0
        scores['ht_sine'] = _clamp((sine_v + 1) / 2)

    # ── 动量振荡类 ────────────────────────────────────────────────────────────
    v = ind.get_rsi(code, date, 14)
    if v is not None:
        scores['rsi14'] = _linear(v, 70, 30)

    v = ind.get_rsi(code, date, 6)
    if v is not None:
        scores['rsi6'] = _linear(v, 70, 30)

    v = ind.get_cci(code, date, 20)
    if v is not None:
        scores['cci'] = _linear(v, 100, -100)

    for period, fname in [(10, 'mom10'), (20, 'mom20')]:
        v = ind.get_mom(code, date, period)
        if v is not None:
            scores[fname] = 1.0 if v > 0 else 0.0

    for period, fname in [(10, 'roc10')]:
        v = ind.get_roc(code, date, period)
        if v is not None:
            scores[fname] = 1.0 if v > 0 else 0.0

    for period, fname in [(10, 'rocp10')]:
        v = ind.get_rocp(code, date, period)
        if v is not None:
            scores[fname] = 1.0 if v > 0 else 0.0

    for period, fname in [(10, 'rocr10')]:
        v = ind.get_rocr(code, date, period)
        if v is not None:
            scores[fname] = 1.0 if v > 1.0 else 0.0

    v = ind.get_roc_r(code, date, 10)
    if v is not None:
        scores['roc_r'] = 1.0 if v > 0 else 0.0

    v = ind.get_williams_r(code, date, 14)
    if v is not None:
        scores['willr'] = _linear(v, -20, -80)

    v = ind.get_cmo(code, date, 14)
    if v is not None:
        scores['cmo'] = 1.0 if v > 0 else 0.0

    v = ind.get_bias(code, date, 20)
    if v is not None:
        if v < -10:
            scores['bias'] = 1.0
        elif v > 10:
            scores['bias'] = 0.0
        else:
            scores['bias'] = _clamp(0.5 - v / 20)

    v = ind.get_psycho(code, date, 12)
    if v is not None:
        scores['psycho'] = _clamp(1.0 - v / 100)

    v = ind.get_dpo(code, date, 20)
    if v is not None:
        scores['dpo'] = 1.0 if v > 0 else 0.0

    v = ind.get_mass(code, date, 25)
    if v is not None:
        scores['mass'] = 0.3 if v > 27 else 0.5

    # ── KDJ / Stoch 类 ────────────────────────────────────────────────────────
    kdj = ind.get_kdj(code, date)
    if kdj is not None:
        j = kdj.get('j', 50) or 50
        scores['kdj_j'] = _linear(j, 80, 20)
        k = kdj.get('k', 50) or 50
        d = kdj.get('d', 50) or 50
        scores['kdj_kd'] = 1.0 if k > d else 0.0

    stoch = ind.get_stoch(code, date)
    if stoch is not None:
        sk = stoch.get('slowk', 50) or 50
        scores['stoch_k'] = _linear(sk, 80, 20)

    stochf = ind.get_stochf(code, date)
    if stochf is not None:
        fk = stochf.get('fastk', 50) or 50
        scores['stochf_k'] = _linear(fk, 80, 20)

    stochrsi = ind.get_stochrsi(code, date)
    if stochrsi is not None:
        sk = stochrsi.get('fastk', 50) or 50
        scores['stochrsi'] = _linear(sk, 80, 20)

    v = ind.get_ultosc(code, date)
    if v is not None:
        scores['ultosc'] = _linear(v, 70, 30)

    # ── MACD 类 ───────────────────────────────────────────────────────────────
    macd = ind.get_macd(code, date)
    if macd is not None:
        hist = macd.get('histogram', 0) or 0
        scores['macd_hist'] = 1.0 if hist > 0 else 0.0
        macd_v = macd.get('macd', 0) or 0
        sig_v = macd.get('signal', 0) or 0
        scores['macd_cross'] = 1.0 if macd_v > sig_v else 0.0

    ppo = ind.get_ppo(code, date)
    if ppo is not None:
        hist = ppo.get('histogram', 0) or 0
        scores['ppo_hist'] = 1.0 if hist > 0 else 0.0

    v = ind.get_adosc(code, date)
    if v is not None:
        scores['adosc'] = 1.0 if v > 0 else 0.0

    # ── 成交量类 ──────────────────────────────────────────────────────────────
    v = ind.get_obv(code, date, 20)
    if v is not None:
        v_prev = ind.get_obv(code, _prev_date(date, 5), 20)
        if v_prev is not None:
            scores['obv'] = 1.0 if v > v_prev else 0.0

    v = ind.get_ad(code, date, 20)
    if v is not None:
        v_prev = ind.get_ad(code, _prev_date(date, 5), 20)
        if v_prev is not None:
            scores['ad'] = 1.0 if v > v_prev else 0.0

    v = ind.get_mfi(code, date, 14)
    if v is not None:
        scores['mfi'] = _linear(v, 80, 20)

    v = ind.get_vwap(code, date, 20)
    if v is not None and close is not None:
        scores['vwap'] = 1.0 if close > v else 0.0

    vol_d = ind.get_volume(code, date, 20)
    if vol_d is not None:
        ratio = vol_d.get('ratio', 1.0) or 1.0
        scores['volume_ratio'] = 1.0 if ratio > 1.5 else (0.3 if ratio < 0.5 else 0.5)

    v = ind.get_vr(code, date, 26)
    if v is not None:
        scores['vr'] = _linear(v, 180, 70)

    v = ind.get_pvi(code, date, 20)
    if v is not None:
        pvi_ma = ind.get_sma(code, date, 20)
        if pvi_ma is not None:
            scores['pvi'] = 1.0 if v > pvi_ma else 0.0

    v = ind.get_nvi(code, date, 20)
    if v is not None:
        nvi_ma = ind.get_sma(code, date, 20)
        if nvi_ma is not None:
            scores['nvi'] = 1.0 if v > nvi_ma else 0.0

    v = ind.get_ar(code, date, 26)
    if v is not None:
        scores['ar'] = _linear(v, 150, 50)

    v = ind.get_br(code, date, 26)
    if v is not None:
        scores['br'] = _linear(v, 200, 50)

    brar = ind.get_brar(code, date, 26)
    if brar is not None:
        ar_v = brar.get('ar', 100) or 100
        br_v = brar.get('br', 100) or 100
        scores['brar'] = _clamp(((200 - ar_v) / 300 + (200 - br_v) / 400) / 2)

    v = ind.get_asi(code, date, 26)
    if v is not None:
        scores['asi'] = 1.0 if v > 0 else 0.0

    # ── 通道类 ────────────────────────────────────────────────────────────────
    bb = ind.get_bollinger_bands(code, date, 20, 2)
    if bb is not None and close is not None:
        upper = bb.get('upper', close) or close
        lower = bb.get('lower', close) or close
        if upper != lower:
            scores['bb_pos'] = _clamp((close - lower) / (upper - lower))
            bb_score = _clamp((close - lower) / (upper - lower))
            scores['bb_signal'] = 1.0 - bb_score if bb_score > 0.8 else (1.0 if bb_score < 0.2 else 0.5)

    v = ind.get_bbands_pct(code, date, 20, 2)
    if v is not None:
        scores['bbands_pct'] = _linear(v, 1.0, 0.0)

    v = ind.get_bbands_width(code, date, 20, 2)
    if v is not None:
        scores['bbands_width'] = 0.5

    ma_ch = ind.get_ma_channel(code, date, 20, 2.0)
    if ma_ch is not None and close is not None:
        upper = ma_ch.get('upper', close) or close
        lower = ma_ch.get('lower', close) or close
        if upper != lower:
            pos = _clamp((close - lower) / (upper - lower))
            scores['ma_channel'] = 1.0 if pos < 0.2 else (0.0 if pos > 0.8 else 0.5)

    dc = ind.get_donchian(code, date, 20)
    if dc is not None and close is not None:
        upper = dc.get('upper', close) or close
        lower = dc.get('lower', close) or close
        if upper != lower:
            pos = _clamp((close - lower) / (upper - lower))
            scores['donchian'] = 1.0 - pos

    kelt = ind.get_keltner(code, date, 20, 10, 2.0)
    if kelt is not None and close is not None:
        upper = kelt.get('upper', close) or close
        lower = kelt.get('lower', close) or close
        if upper != lower:
            pos = _clamp((close - lower) / (upper - lower))
            scores['keltner'] = 1.0 if pos < 0.2 else (0.0 if pos > 0.8 else 0.5)

    xue = ind.get_xue_channel(code, date, 20, 3.0)
    if xue is not None and close is not None:
        upper = xue.get('upper', close) or close
        lower = xue.get('lower', close) or close
        if upper != lower:
            pos = _clamp((close - lower) / (upper - lower))
            scores['xue_channel'] = 1.0 - pos

    v = ind.get_midpoint(code, date, 14)
    if v is not None and close is not None:
        scores['midpoint'] = 1.0 if close > v else 0.0

    v = ind.get_midprice(code, date, 14)
    if v is not None and close is not None:
        scores['midprice'] = 1.0 if close > v else 0.0

    for key in ['atr', 'natr', 'tr', 'trange', 'stddev', 'var', 'correl', 'beta', 'ht_dcperiod']:
        scores[key] = 0.5

    for fname, fn in [('typical', ind.get_typical_price), ('median', ind.get_median_price),
                      ('wclose', ind.get_weighted_close), ('avgp', ind.get_avgp)]:
        v = fn(code, date)
        if v is not None and close is not None:
            scores[fname] = 1.0 if close > v else 0.0

    ht_ph = ind.get_ht_phasor(code, date)
    if ht_ph is not None:
        inphase = ht_ph.get('inphase', 0) or 0
        scores['ht_phasor'] = 1.0 if inphase > 0 else 0.0

    v = ind.get_consecutive_rise(code, date, 60)
    if v is not None:
        scores['consec_rise'] = _clamp(v / 10)

    v = ind.get_consecutive_fall(code, date, 60)
    if v is not None:
        scores['consec_fall'] = _clamp(v / 5)

    v = ind.get_bomb_board(code, date)
    if v is not None:
        scores['bomb_board'] = 0.0 if v > 0 else 0.5

    v = ind.get_bomb_board_count(code, date, 20)
    if v is not None:
        scores['bomb_board_count'] = _clamp(1.0 - v * 0.2)

    v = ind.get_consecutive_limit_up(code, date)
    if v is not None:
        scores['consec_limit_up'] = _clamp(v * 0.2)

    if not scores:
        return {'score': 0.5, 'valid_count': 0, 'total_count': 80, 'details': {}}

    w = weights or {}
    final = _weighted_mean(scores, w)

    return {
        'score': round(final, 4),
        'valid_count': len(scores),
        'total_count': 80,
        'details': {k: round(v, 4) for k, v in list(scores.items())[:20]},
        '_raw_scores': scores,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Expert 2：Alpha 因子专家
# ─────────────────────────────────────────────────────────────────────────────

def _score_alpha(code: str, date: str, weights: Optional[Dict[str, float]] = None) -> Optional[Dict[str, Any]]:
    try:
        from formulaicAlphas.alpha101 import Alpha101
        from formulaicAlphas.data_loader import AlphaDataLoader
    except ImportError:
        return None

    end_date = date
    start_date = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=270)).strftime('%Y-%m-%d')

    all_codes = [b.ts_code for b in query_stock_basic() if b.ts_code]
    all_codes = all_codes[:1000]
    if code not in all_codes:
        all_codes.insert(0, code)

    loader = AlphaDataLoader()
    data = loader.load(codes=all_codes, start_date=start_date, end_date=end_date)
    if not data or 'close' not in data:
        return None

    close_df = data['close']
    if code not in close_df.columns:
        return None

    target_date = pd.Timestamp(date)
    available_dates = close_df.index[close_df.index <= target_date]
    if len(available_dates) == 0:
        return None
    actual_date = available_dates[-1]

    alpha_obj = Alpha101(data)

    alpha_scores: Dict[str, float] = {}
    for i in range(1, 102):
        fname = f'alpha{i:03d}'
        try:
            fn = getattr(alpha_obj, fname, None)
            if fn is None:
                continue
            result = fn()
            if result is None or not isinstance(result, pd.DataFrame):
                continue
            if actual_date not in result.index or code not in result.columns:
                continue
            val = result.loc[actual_date, code]
            if pd.isna(val):
                continue
            row = result.loc[actual_date].dropna()
            if len(row) < 5:
                continue
            rank = float((row < val).sum()) / len(row)
            alpha_scores[fname] = rank
        except Exception:
            continue

    if not alpha_scores:
        return None

    w = weights or {}
    final = _weighted_mean(alpha_scores, w)

    return {
        'score': round(final, 4),
        'valid_count': len(alpha_scores),
        'total_count': 101,
        'details': {k: round(v, 4) for k, v in list(alpha_scores.items())[:10]},
        '_raw_scores': alpha_scores,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Expert 3：基本面专家
# ─────────────────────────────────────────────────────────────────────────────

def _score_fundamental(code: str, date: str, weights: Optional[Dict[str, float]] = None) -> Optional[Dict[str, Any]]:
    basics = query_daily_basic(ts_codes=[code], end_date=date, limit=1, order_by="trade_date DESC")
    if not basics:
        return None
    b = basics[0]

    scores: Dict[str, float] = {}

    pe = b.pe_ttm
    if pe is not None:
        if pe <= 0:
            scores['pe_ttm'] = 0.1
        elif pe < 30:
            scores['pe_ttm'] = 1.0
        elif pe < 60:
            scores['pe_ttm'] = 0.5
        else:
            scores['pe_ttm'] = 0.2

    pb = b.pb
    if pb is not None and pb > 0:
        if pb < 3:
            scores['pb'] = 1.0
        elif pb < 6:
            scores['pb'] = 0.5
        else:
            scores['pb'] = 0.2

    tr = b.turnover_rate
    if tr is not None:
        if 1 <= tr <= 5:
            scores['turnover_rate'] = 1.0
        elif 5 < tr <= 10:
            scores['turnover_rate'] = 0.7
        elif tr < 1:
            scores['turnover_rate'] = 0.4
        else:
            scores['turnover_rate'] = 0.3

    vr = b.volume_ratio
    if vr is not None:
        if 1 <= vr <= 2:
            scores['volume_ratio'] = 1.0
        elif 2 < vr <= 3:
            scores['volume_ratio'] = 0.7
        elif vr < 0.5:
            scores['volume_ratio'] = 0.3
        else:
            scores['volume_ratio'] = 0.4

    ps = b.ps_ttm
    if ps is not None and ps > 0:
        if ps < 1:
            scores['ps_ttm'] = 1.0
        elif ps < 5:
            scores['ps_ttm'] = 0.7
        elif ps < 10:
            scores['ps_ttm'] = 0.5
        else:
            scores['ps_ttm'] = 0.3

    if not scores:
        return None

    w = weights or {}
    final = _weighted_mean(scores, w)

    return {
        'score': round(final, 4),
        'details': {'pe_ttm': b.pe_ttm, 'pb': b.pb, 'turnover_rate': b.turnover_rate,
                    'volume_ratio': b.volume_ratio, 'ps_ttm': b.ps_ttm, 'scores': scores},
        '_raw_scores': scores,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Expert 4：量价行为专家
# ─────────────────────────────────────────────────────────────────────────────

def _score_behavior(code: str, date: str, weights: Optional[Dict[str, float]] = None) -> Optional[Dict[str, Any]]:
    start_d = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=30)).strftime('%Y-%m-%d')
    details: Dict[str, Any] = {}
    named_signals: Dict[str, float] = {}

    limits = query_stock_limit(ts_codes=[code], start_date=start_d, end_date=date)
    limit_up_5d = 0
    limit_down_5d = 0
    klines_5d = query_daily_kline(codes=[code], end_date=date, limit=5, order_by="date DESC")
    dates_5d = {k.date for k in klines_5d}
    for lim in limits:
        if lim.trade_date in dates_5d:
            if hasattr(lim, 'limit_up') and lim.limit_up:
                limit_up_5d += 1
            if hasattr(lim, 'limit_down') and lim.limit_down:
                limit_down_5d += 1

    details['limit_up_5d'] = limit_up_5d
    details['limit_down_5d'] = limit_down_5d
    named_signals['limit_score'] = _clamp(0.5 + limit_up_5d * 0.15 - limit_down_5d * 0.15)

    consec_up = ind.get_consecutive_limit_up(code, date)
    if consec_up is not None and consec_up > 0:
        details['consecutive_limit_up'] = consec_up
        named_signals['consecutive_limit_up'] = _clamp(consec_up * 0.2)

    bomb_cnt = ind.get_bomb_board_count(code, date, 10)
    if bomb_cnt is not None:
        details['bomb_board_10d'] = bomb_cnt
        named_signals['bomb_board'] = _clamp(1.0 - bomb_cnt * 0.15)

    top_lists = query_top_list(ts_codes=[code], start_date=start_d, end_date=date)
    if top_lists:
        net_buy = sum((getattr(tl, 'net_buy', 0) or 0) for tl in top_lists)
        details['top_list_net_buy'] = net_buy
        named_signals['top_list'] = _clamp(0.5 + (0.3 if net_buy > 0 else (-0.3 if net_buy < 0 else 0)))

    if klines_5d and len(klines_5d) >= 2:
        latest_close = klines_5d[0].close
        oldest_close = klines_5d[-1].pre_close if hasattr(klines_5d[-1], 'pre_close') else klines_5d[-1].close
        if oldest_close and oldest_close > 0:
            chg_5d = (latest_close - oldest_close) / oldest_close * 100
            details['pct_chg_5d'] = round(chg_5d, 2)
            named_signals['pct_chg_5d'] = _linear(chg_5d, 20, -20)

    if not named_signals:
        return None

    w = weights or {}
    final = _weighted_mean(named_signals, w)

    return {
        'score': round(final, 4),
        'details': details,
        '_raw_scores': named_signals,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 门控网络 + 汇总
# ─────────────────────────────────────────────────────────────────────────────

def _compute_final_score(
    tech_result: Optional[Dict],
    alpha_result: Optional[Dict],
    fund_result: Optional[Dict],
    behav_result: Optional[Dict],
    expert_weights: Dict[str, float],
    buy_thresh: float = 0.65,
    sell_thresh: float = 0.35,
) -> Dict[str, Any]:
    """门控网络：根据有效专家和权重计算最终评分。"""
    expert_results = {
        'technical': tech_result,
        'alpha': alpha_result,
        'fundamental': fund_result,
        'behavior': behav_result,
    }

    active = {k: v for k, v in expert_results.items() if v is not None}
    if not active:
        return {'error': '所有专家数据不足'}

    total_w = sum(expert_weights.get(k, 0.0) for k in active)
    if total_w <= 0:
        total_w = len(active)
        norm_weights = {k: 1.0 / total_w for k in active}
    else:
        norm_weights = {k: expert_weights.get(k, 0.0) / total_w for k in active}

    final_score = sum(norm_weights[k] * active[k]['score'] for k in active)
    final_score = round(float(final_score), 4)

    signal = 'BUY' if final_score >= buy_thresh else ('SELL' if final_score <= sell_thresh else 'HOLD')

    score_vals = [active[k]['score'] for k in active]
    variance = float(np.var(score_vals)) if len(score_vals) > 1 else 0.0
    confidence = '高' if variance < 0.005 else ('中' if variance < 0.020 else '低')

    reasons = []
    for k, v in active.items():
        s = v['score']
        label = {'technical': '技术面', 'alpha': 'Alpha因子', 'fundamental': '基本面', 'behavior': '量价行为'}[k]
        if s >= buy_thresh:
            reasons.append(f'{label}看多({s:.2f})')
        elif s <= sell_thresh:
            reasons.append(f'{label}看空({s:.2f})')
        else:
            reasons.append(f'{label}中性({s:.2f})')

    experts_out = {}
    for k in ['technical', 'alpha', 'fundamental', 'behavior']:
        if k in active:
            entry = {'score': active[k]['score'], 'weight': round(norm_weights[k], 4)}
            if 'valid_count' in active[k]:
                entry['valid_count'] = active[k]['valid_count']
                entry['total_count'] = active[k]['total_count']
            if 'details' in active[k]:
                entry['details'] = active[k]['details']
            experts_out[k] = entry
        else:
            experts_out[k] = {'score': None, 'weight': 0.0, 'note': '数据补充中，敬请期待'}

    return {
        'final_score': final_score,
        'signal': signal,
        'confidence': confidence,
        'experts': experts_out,
        'reason': '，'.join(reasons),
    }


def analyze(code: str, date: str) -> Dict[str, Any]:
    """
    功能一：基于当前价格结合 MoE 做买卖决策。

    从 moe_weights.json 加载权重（若不存在则使用默认值），
    运行 4 个专家打分，门控网络汇总，输出 BUY/SELL/HOLD。
    """
    print(f'[MoE] 正在分析 {code}  日期={date}')

    # 退市检查
    try:
        basics = query_stock_basic(ts_codes=[code])
        if basics:
            b = basics[0]
            if getattr(b, 'list_status', None) == 'D':
                delist_date = getattr(b, 'delist_date', None) or '未知'
                name = getattr(b, 'name', code)
                print(f'[MoE] ⚠️  {code}（{name}）已于 {delist_date} 退市，以下分析仅供参考，该股票已无法交易。')
    except Exception:
        pass

    weights = load_weights()
    expert_w = weights.get('expert_weights', _DEFAULT_WEIGHTS['expert_weights'])
    tech_w = weights.get('technical', {})
    alpha_w = weights.get('alpha', {})
    fund_w = weights.get('fundamental', {})
    behav_w = weights.get('behavior', {})
    buy_thresh = weights.get('signal_thresholds', {}).get('buy', 0.65)
    sell_thresh = weights.get('signal_thresholds', {}).get('sell', 0.35)

    print('[MoE] Expert 1: 技术指标...')
    tech = _score_tech(code, date, tech_w)

    print('[MoE] Expert 2: Alpha因子...')
    alpha = _score_alpha(code, date, alpha_w)

    print('[MoE] Expert 3: 基本面...')
    fund = _score_fundamental(code, date, fund_w)

    print('[MoE] Expert 4: 量价行为...')
    behav = _score_behavior(code, date, behav_w)

    result = _compute_final_score(tech, alpha, fund, behav, expert_w, buy_thresh, sell_thresh)
    result['code'] = code
    result['date'] = date

    # 退市标记写入返回值
    try:
        basics = query_stock_basic(ts_codes=[code])
        if basics:
            b = basics[0]
            if getattr(b, 'list_status', None) == 'D':
                result['delisted'] = True
                result['delist_date'] = getattr(b, 'delist_date', None) or '未知'
                result['delist_warning'] = (
                    f"⚠️ {code}（{getattr(b, 'name', code)}）已于 {result['delist_date']} 退市，"
                    f"该股票已无法交易，以下分析仅供参考。"
                )
    except Exception:
        pass

    return result


# ─────────────────────────────────────────────────────────────────────────────
# 功能二：遗传算法权重训练
# ─────────────────────────────────────────────────────────────────────────────

def _get_trading_dates(start_date: str, end_date: str) -> List[str]:
    """从数据库获取月度采样日期列表（用000001.SZ取交易日历，每月取第一个交易日）。"""
    klines = query_daily_kline(codes=['000001.SZ'], start_date=start_date, end_date=end_date,
                               order_by='date ASC', limit=None)
    dates = sorted(set(k.date for k in klines))
    monthly: Dict[str, str] = {}
    for d in dates:
        ym = d[:7]
        if ym not in monthly:
            monthly[ym] = d
    return list(monthly.values())


# ── 训练缓存结构 ──────────────────────────────────────────────────────────────
# cache[(code, date)] = {
#   'tech_raw':  Dict[str, float],   # 技术指标原始分
#   'fund_raw':  Dict[str, float],   # 基本面原始分
#   'behav_raw': Dict[str, float],   # 行为原始分
#   'future_ret': float,             # 5日后实际收益率（用于适应度）
# }
_TRAIN_CACHE: Dict[Tuple[str, str], Dict] = {}


def _precompute_cache(train_codes: List[str], train_dates: List[str], hold_days: int = 5) -> None:
    """
    预计算阶段：一次性算好所有 (code, date) 的原始指标分和未来收益，
    存入内存缓存。遗传算法迭代时只做纯内存加权，不再查DB。
    """
    global _TRAIN_CACHE
    _TRAIN_CACHE = {}
    total = len(train_codes) * len(train_dates)
    done = 0
    print(f'[预计算] 共 {len(train_codes)} 只股票 × {len(train_dates)} 个日期 = {total} 个样本点', flush=True)

    # 批量预取未来收益：查询每只股票在训练区间内的K线，避免逐条查DB
    # key: code -> {date -> (buy_price, sell_price)}
    price_map: Dict[str, Dict[str, Tuple[float, float]]] = {}
    print('[预计算] 批量加载K线价格...', flush=True)
    start_dt = train_dates[0] if train_dates else '2025-09-01'
    end_future = (datetime.strptime(train_dates[-1], '%Y-%m-%d') + timedelta(days=hold_days * 3)).strftime('%Y-%m-%d')

    batch_size = 200
    for i in range(0, len(train_codes), batch_size):
        batch = train_codes[i:i+batch_size]
        klines = query_daily_kline(codes=batch, start_date=start_dt, end_date=end_future,
                                   order_by='date ASC', limit=None)
        for kl in klines:
            if kl.code not in price_map:
                price_map[kl.code] = {}
            price_map[kl.code][kl.date] = kl.close
        if (i // batch_size) % 5 == 0:
            print(f'  K线加载: {min(i+batch_size, len(train_codes))}/{len(train_codes)} 只...', flush=True)

    def _future_ret(code: str, date: str) -> Optional[float]:
        """取买入日后第 hold_days 个已有交易日的收盘价计算收益。"""
        cdates = price_map.get(code)
        if not cdates:
            return None
        sorted_dates = sorted(cdates.keys())
        try:
            idx = sorted_dates.index(date)
        except ValueError:
            # 找最近的日期
            before = [d for d in sorted_dates if d <= date]
            if not before:
                return None
            idx = sorted_dates.index(before[-1])
        buy_price = cdates[sorted_dates[idx]]
        sell_idx = min(idx + hold_days, len(sorted_dates) - 1)
        if sell_idx == idx:
            return None
        sell_price = cdates[sorted_dates[sell_idx]]
        if buy_price > 0:
            return (sell_price - buy_price) / buy_price
        return None

    print('[预计算] 计算技术/基本面/行为指标...', flush=True)
    for ci, code in enumerate(train_codes):
        for date in train_dates:
            key = (code, date)
            try:
                tech_r = _score_tech(code, date, weights=None)
                fund_r = _score_fundamental(code, date, weights=None)
                behav_r = _score_behavior(code, date, weights=None)
                fret = _future_ret(code, date)
                _TRAIN_CACHE[key] = {
                    'tech_raw':  tech_r.get('_raw_scores', {}) if tech_r else {},
                    'fund_raw':  fund_r.get('_raw_scores', {}) if fund_r else {},
                    'behav_raw': behav_r.get('_raw_scores', {}) if behav_r else {},
                    'future_ret': fret,
                }
            except Exception:
                pass
            done += 1
        if (ci + 1) % 100 == 0 or ci == len(train_codes) - 1:
            print(f'  指标预计算: {ci+1}/{len(train_codes)} 只，缓存={len(_TRAIN_CACHE)} 条', flush=True)

    print(f'[预计算] 完成，共缓存 {len(_TRAIN_CACHE)} 个样本点', flush=True)


def _evaluate_weights_fast(wconfig: Dict[str, Any]) -> float:
    """
    快速适应度函数：直接从内存缓存读取指标原始分，
    按当前权重重新加权，统计 BUY 信号命中率（预测准确率 × 平均收益）。
    """
    tech_w  = wconfig.get('technical', {})
    fund_w  = wconfig.get('fundamental', {})
    behav_w = wconfig.get('behavior', {})
    expert_w = {k: v for k, v in wconfig['expert_weights'].items()}
    expert_w['alpha'] = 0.0  # 训练阶段不用 alpha
    buy_thresh  = wconfig.get('signal_thresholds', {}).get('buy', 0.65)
    sell_thresh = wconfig.get('signal_thresholds', {}).get('sell', 0.35)

    total_ret = 0.0
    buy_count = 0

    for (code, date), cache in _TRAIN_CACHE.items():
        future_ret = cache.get('future_ret')
        if future_ret is None:
            continue

        # 纯内存加权
        tech_score  = _weighted_mean(cache['tech_raw'],  tech_w)  if cache['tech_raw']  else None
        fund_score  = _weighted_mean(cache['fund_raw'],  fund_w)  if cache['fund_raw']  else None
        behav_score = _weighted_mean(cache['behav_raw'], behav_w) if cache['behav_raw'] else None

        experts = {}
        if tech_score  is not None: experts['technical']   = tech_score
        if fund_score  is not None: experts['fundamental'] = fund_score
        if behav_score is not None: experts['behavior']    = behav_score
        if not experts:
            continue

        total_ew = sum(expert_w.get(k, 0.0) for k in experts)
        if total_ew <= 0:
            continue
        final = sum(expert_w.get(k, 0.0) / total_ew * s for k, s in experts.items())

        if final >= buy_thresh:
            total_ret += future_ret
            buy_count += 1

    return (total_ret / buy_count) if buy_count > 0 else 0.0


def _mutate(wconfig: Dict[str, Any], mutation_rate: float = 0.15, mutation_strength: float = 0.3) -> Dict[str, Any]:
    """变异：随机扰动部分权重。"""
    new = copy.deepcopy(wconfig)

    ew = new['expert_weights']
    for k in ew:
        if random.random() < mutation_rate:
            ew[k] = max(0.01, ew[k] + random.gauss(0, mutation_strength * ew[k]))
    total = sum(ew.values())
    for k in ew:
        ew[k] = ew[k] / total

    for section in ['technical', 'fundamental', 'behavior']:
        sec = new.get(section, {})
        keys = list(sec.keys())
        n_mutate = max(1, int(len(keys) * mutation_rate))
        for k in random.sample(keys, min(n_mutate, len(keys))):
            sec[k] = max(0.0, sec[k] + random.gauss(0, mutation_strength))

    thresh = new.get('signal_thresholds', {'buy': 0.65, 'sell': 0.35})
    if random.random() < mutation_rate:
        thresh['buy'] = _clamp(thresh['buy'] + random.gauss(0, 0.05), 0.55, 0.85)
    if random.random() < mutation_rate:
        thresh['sell'] = _clamp(thresh['sell'] + random.gauss(0, 0.05), 0.15, 0.45)
    new['signal_thresholds'] = thresh

    return new


def _crossover(p1: Dict[str, Any], p2: Dict[str, Any]) -> Dict[str, Any]:
    """交叉：每个 key 随机选一个亲本。"""
    child = copy.deepcopy(p1)

    for k in child['expert_weights']:
        if random.random() < 0.5:
            child['expert_weights'][k] = p2['expert_weights'].get(k, child['expert_weights'][k])
    total = sum(child['expert_weights'].values())
    for k in child['expert_weights']:
        child['expert_weights'][k] /= total

    for section in ['technical', 'alpha', 'fundamental', 'behavior']:
        sec1 = child.get(section, {})
        sec2 = p2.get(section, {})
        for k in sec1:
            if random.random() < 0.5 and k in sec2:
                sec1[k] = sec2[k]

    if random.random() < 0.5:
        child['signal_thresholds'] = copy.deepcopy(p2.get('signal_thresholds', {'buy': 0.65, 'sell': 0.35}))

    return child


def train_weights(
    start_date: str,
    end_date: str,
    population_size: int = 20,
    generations: int = 30,
    elite_count: int = 4,
    train_stock_count: int = 0,
) -> Dict[str, Any]:
    """
    功能二：遗传算法训练最优权重，目标：最大化 BUY 信号后5日平均收益。

    架构：两阶段
      1. 预计算阶段（一次性）：批量计算所有股票×日期的指标原始分 + 未来收益，存入内存
      2. 迭代阶段（快速）：遗传算法每代只做纯内存加权，不再查DB，速度极快

    Args:
        start_date: 训练开始日期
        end_date: 训练结束日期
        population_size: 种群大小（默认20）
        generations: 迭代代数（默认30）
        elite_count: 每代保留的精英数量
        train_stock_count: 训练股票数量（0=全量）

    Returns:
        优化后的权重配置字典（已写入 moe_weights.json）
    """
    print(f'\n[遗传算法] 开始训练  {start_date} ~ {end_date}')
    print(f'  种群={population_size}  代数={generations}  精英={elite_count}  股票数={"全量" if train_stock_count <= 0 else train_stock_count}')

    all_stocks = [b.ts_code for b in query_stock_basic() if b.ts_code]
    random.seed(42)
    if train_stock_count <= 0 or train_stock_count >= len(all_stocks):
        train_codes = all_stocks
    else:
        train_codes = random.sample(all_stocks, train_stock_count)
    print(f'  训练股票: {train_codes[:5]}... 共{len(train_codes)}只')

    train_dates = _get_trading_dates(start_date, end_date)
    print(f'  训练日期: {len(train_dates)}个月度采样点  {train_dates}')

    if not train_dates:
        print('[遗传算法] 没有找到训练日期，退出')
        return load_weights()

    # ── 阶段一：预计算（只跑一次）──────────────────────────────────────────────
    _precompute_cache(train_codes, train_dates, hold_days=5)
    if not _TRAIN_CACHE:
        print('[遗传算法] 预计算缓存为空，退出')
        return load_weights()

    # ── 阶段二：遗传算法迭代（纯内存）──────────────────────────────────────────
    base = load_weights()
    population = [base]
    for _ in range(population_size - 1):
        population.append(_mutate(base, mutation_rate=0.3, mutation_strength=0.5))

    best_config = base
    best_fitness = -999.0

    for gen in range(generations):
        print(f'\n[遗传算法] 第 {gen+1}/{generations} 代  评估{len(population)}个个体...')

        fitness_scores = []
        for i, wconfig in enumerate(population):
            try:
                fit = _evaluate_weights_fast(wconfig)
            except Exception:
                fit = -1.0
            fitness_scores.append(fit)
            print(f'  个体{i+1:2d}: BUY平均收益={fit*100:.2f}%')

        ranked = sorted(zip(fitness_scores, population), key=lambda x: x[0], reverse=True)
        best_gen_fit, best_gen_cfg = ranked[0]

        if best_gen_fit > best_fitness:
            best_fitness = best_gen_fit
            best_config = copy.deepcopy(best_gen_cfg)
            print(f'  ★ 新最优: {best_fitness*100:.2f}%')

        elites = [cfg for _, cfg in ranked[:elite_count]]

        new_population = list(elites)
        while len(new_population) < population_size:
            if random.random() < 0.6 and len(elites) >= 2:
                p1, p2 = random.sample(elites, 2)
                child = _crossover(p1, p2)
            else:
                child = copy.deepcopy(random.choice(elites))
            child = _mutate(child, mutation_rate=0.15, mutation_strength=0.2)
            new_population.append(child)
        population = new_population

    print(f'\n[遗传算法] 训练完成！最优BUY平均收益: {best_fitness*100:.2f}%')
    save_weights(best_config, train_period=f'{start_date}~{end_date}')
    return best_config


# ─────────────────────────────────────────────────────────────────────────────
# 命令行入口
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MoE 混合专家买卖时机分析 + 权重训练')
    subparsers = parser.add_subparsers(dest='cmd')

    p_analyze = subparsers.add_parser('analyze', help='分析股票买卖时机（默认）')
    p_analyze.add_argument('--code', required=True, help='股票代码，如 000001.SZ')
    p_analyze.add_argument('--date', default=None, help='分析日期 YYYY-MM-DD，默认今天')

    p_train = subparsers.add_parser('train', help='遗传算法训练权重')
    p_train.add_argument('--start-date', default=None, help='训练开始日期')
    p_train.add_argument('--end-date', default=None, help='训练结束日期')
    p_train.add_argument('--population', type=int, default=20, help='种群大小')
    p_train.add_argument('--generations', type=int, default=30, help='迭代代数')
    p_train.add_argument('--stocks', type=int, default=30, help='训练股票数量')

    # 兼容旧的直接参数
    parser.add_argument('--code', default=None, help='股票代码（兼容）')
    parser.add_argument('--date', default=None, help='分析日期（兼容）')
    parser.add_argument('--train', action='store_true', help='训练模式（兼容）')
    parser.add_argument('--start-date', default=None, dest='train_start')
    parser.add_argument('--end-date', default=None, dest='train_end')

    args = parser.parse_args()
    init_indicators_db()

    is_train = (args.cmd == 'train') or getattr(args, 'train', False)

    if is_train:
        _end   = getattr(args, 'end_date',   None) or getattr(args, 'train_end',   None) \
                 or datetime.today().strftime('%Y-%m-%d')
        _start = getattr(args, 'start_date', None) or getattr(args, 'train_start', None) \
                 or (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d')
        pop   = getattr(args, 'population', 20)
        gens  = getattr(args, 'generations', 30)
        stocks = getattr(args, 'stocks', 30)
        train_weights(_start, _end, population_size=pop, generations=gens, train_stock_count=stocks)

    else:
        code = (getattr(args, 'code', None) if args.cmd == 'analyze' else None) or args.code
        if not code:
            parser.print_help()
            sys.exit(1)
        date_val = (getattr(args, 'date', None) if args.cmd == 'analyze' else None) or args.date
        analysis_date = date_val or datetime.today().strftime('%Y-%m-%d')
        result = analyze(code, analysis_date)

        print('\n' + '='*60)
        out = {k: v for k, v in result.items() if not k.startswith('_')}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        print('='*60)

        if 'signal' in result:
            sig = result['signal']
            score = result['final_score']
            conf = result['confidence']
            sig_cn = {'BUY': '买入 ▲', 'SELL': '卖出 ▼', 'HOLD': '持有 —'}[sig]
            print(f'\n  {result["code"]}  综合评分: {score:.4f}  →  {sig_cn}  （置信度: {conf}）')
            print(f'  {result["reason"]}')
