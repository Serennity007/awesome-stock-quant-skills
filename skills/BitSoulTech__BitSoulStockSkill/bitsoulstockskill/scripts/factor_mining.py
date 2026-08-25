"""
factor_mining.py — 因子挖矿实现模块

包含 random_alpha_backtest 的完整实现逻辑。
stock_api.StockApi.random_alpha_backtest() 是对外接口，内部委托此模块执行。

外部勿直接调用本模块，请统一通过 StockApi.random_alpha_backtest() 调用。
"""

import random
import statistics as _stat
from datetime import datetime, timedelta
from typing import Dict, List, Optional, TYPE_CHECKING

import numpy as np
import pandas as pd

from formulaicAlphas import AlphaDataLoader, Alpha101, ALPHA_DESCRIPTIONS

if TYPE_CHECKING:
    from stock_api import StockApi


def run_random_alpha_backtest(
    api: "StockApi",
    codes: Optional[List[str]] = None,
    max_screen_factors: int = 5,
    max_signal_factors: int = 7,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    initial_cash: float = 1_000_000.0,
    warmup_days: int = 90,
    random_seed: Optional[int] = None,
    top_n_stocks: int = 5,
    max_pool_size: int = 30,
    max_holdings: int = 5,
) -> Dict:
    """
    因子挖矿核心逻辑（两阶段：选股 + 交易信号）。

    流程：
      1. 随机抽取 k_screen 个选股因子 + k_signal 个信号因子
      2. 选股阶段：以 start_date 为截面日，每个选股因子随机保留 5%~20% 的股票
      3. 若过滤后股票数仍超过 max_pool_size，按各选股因子综合得分再截取前 max_pool_size 只
      4. 信号阶段：逐日计算信号因子横截面分位排名，综合排名 >= buy_thresh 时买入，
         <= sell_thresh 时卖出（阈值在合理范围内随机生成）
      5. 每日最多同时持仓 max_holdings 只，优先买入综合排名最高的股票
      6. 输出 Top N 个股的每笔交易时的具体因子值与排名

    Args:
        api:                 StockApi 实例（用于调用 get_all_symbols、load_alpha_data 等方法）
        codes:               股票池；None 时取全市场
        max_screen_factors:  选股因子最大数量（默认 5）
        max_signal_factors:  信号因子最大数量（默认 7）
        start_date:          回测起始日，None 取 end_date 前 90 天
        end_date:            回测截止日，None 取今日
        initial_cash:        初始资金（默认 100 万）
        warmup_days:         因子预热天数（默认 90）
        random_seed:         随机种子，None 不固定
        top_n_stocks:        输出详细交易记录的个股数量（默认 5）
        max_pool_size:       最终候选池上限，超过时按综合得分截取（默认 30）
        max_holdings:        最大同时持仓数，优先持有综合排名最高的股票（默认 5）
    """
    # ── 1. 日期默认值 ──────────────────────────────────────────────────────
    if end_date is None:
        end_date = datetime.today().strftime('%Y-%m-%d')
    if start_date is None:
        start_date = (
            datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=90)
        ).strftime('%Y-%m-%d')

    # ── 2. 股票池 ──────────────────────────────────────────────────────────
    if codes is None:
        codes = api.get_all_symbols()
    if not codes:
        return {'error': '股票池为空'}

    # ── 3. 随机抽取因子（选股 / 信号各自独立不重复，两组间允许重叠）────────
    rng = random.Random(random_seed)
    k_screen = rng.randint(1, max(1, max_screen_factors))
    k_signal = rng.randint(1, max(1, max_signal_factors))
    screen_nums = rng.sample(range(1, 102), k_screen)
    signal_nums = rng.sample(range(1, 102), k_signal)

    screen_names = [f'alpha{n:03d}' for n in screen_nums]
    signal_names = [f'alpha{n:03d}' for n in signal_nums]
    all_nums  = list(dict.fromkeys(screen_nums + signal_nums))
    all_names = list(dict.fromkeys(screen_names + signal_names))
    all_descs = {name: ALPHA_DESCRIPTIONS.get(name, '') for name in all_names}

    # 选股因子：每个因子随机保留比例 [0.05, 0.20]
    screen_top_pcts = {name: round(rng.uniform(0.05, 0.20), 2) for name in screen_names}

    # 信号因子阈值
    signal_buy_thresh  = round(rng.uniform(0.55, 0.82), 2)
    signal_sell_thresh = round(rng.uniform(0.30, 0.55), 2)

    # ── 4. 加载面板数据（含预热段）────────────────────────────────────────
    warmup_start = (
        datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=warmup_days)
    ).strftime('%Y-%m-%d')
    panel = api.load_alpha_data(codes, warmup_start, end_date)
    if not panel:
        return {'error': '无法加载面板数据',
                'screen_factors': screen_names, 'signal_factors': signal_names}

    close_panel = panel['close']
    start_ts = pd.Timestamp(start_date)
    end_ts   = pd.Timestamp(end_date)
    valid_idx = close_panel.index[close_panel.index <= start_ts]
    ref_date  = valid_idx[-1] if len(valid_idx) > 0 else close_panel.index[0]

    # ── 5. 计算所有因子 ────────────────────────────────────────────────────
    alpha_obj = Alpha101(panel)
    factor_panels: Dict[str, object] = {}
    for num in all_nums:
        name   = f'alpha{num:03d}'
        method = getattr(alpha_obj, name, None)
        if method is None:
            continue
        try:
            factor_panels[name] = method()
        except Exception:
            pass

    # ── 6. 选股阶段：逐因子顺序过滤 ───────────────────────────────────────
    current_pool = set(close_panel.columns.tolist())
    filter_log: List[Dict] = []

    for name in screen_names:
        before   = len(current_pool)
        top_pct  = screen_top_pcts[name]
        if not current_pool or name not in factor_panels:
            filter_log.append({'factor': name, 'status': 'skipped',
                               'before': before, 'after': before, 'top_pct': top_pct})
            continue
        fp = factor_panels[name]
        if ref_date not in fp.index:
            filter_log.append({'factor': name, 'status': 'no_ref_date',
                               'before': before, 'after': before, 'top_pct': top_pct})
            continue
        pool_cols = [c for c in current_pool if c in fp.columns]
        snapshot  = fp.loc[ref_date, pool_cols].dropna()
        if snapshot.empty:
            filter_log.append({'factor': name, 'status': 'all_nan',
                               'before': before, 'after': before, 'top_pct': top_pct})
            continue
        n_keep    = max(1, int(len(snapshot) * top_pct))
        top_codes = set(snapshot.nlargest(n_keep).index)
        current_pool &= top_codes
        filter_log.append({'factor': name, 'status': 'ok',
                           'before': before, 'after': len(current_pool),
                           'ref_date': str(ref_date.date()),
                           'snapshot_size': len(snapshot),
                           'kept': n_keep, 'top_pct': top_pct})

    final_codes = sorted(current_pool)
    if not final_codes:
        return {'screen_k': k_screen, 'signal_k': k_signal,
                'screen_factors': screen_names, 'signal_factors': signal_names,
                'factor_descriptions': all_descs,
                'initial_pool': len(codes), 'filter_log': filter_log,
                'final_pool': [], 'final_pool_count': 0,
                'error': '过滤后股票池为空，无法回测'}

    # ── 二次裁剪：候选池超过 max_pool_size 时按综合得分取 Top N ──────────
    if max_pool_size > 0 and len(final_codes) > max_pool_size:
        score_map: Dict[str, float] = {c: 0.0 for c in final_codes}
        for name in screen_names:
            if name not in factor_panels:
                continue
            fp = factor_panels[name]
            if ref_date not in fp.index:
                continue
            pool_cols = [c for c in final_codes if c in fp.columns]
            snap = fp.loc[ref_date, pool_cols].dropna()
            if snap.empty:
                continue
            ranked = snap.rank(pct=True)
            for c, v in ranked.items():
                score_map[c] = score_map.get(c, 0.0) + float(v)
        sorted_by_score = sorted(final_codes, key=lambda c: score_map.get(c, 0.0), reverse=True)
        final_codes = sorted(sorted_by_score[:max_pool_size])

    # ── 7. 信号阶段：逐日模拟买卖 ─────────────────────────────────────────
    bt_mask     = (close_panel.index >= start_ts) & (close_panel.index <= end_ts)
    avail_codes = [c for c in final_codes if c in close_panel.columns]
    bt_close    = close_panel.loc[bt_mask, avail_codes]

    if bt_close.empty or len(bt_close) < 2:
        return {'screen_k': k_screen, 'signal_k': k_signal,
                'screen_factors': screen_names, 'signal_factors': signal_names,
                'factor_descriptions': all_descs,
                'initial_pool': len(codes), 'filter_log': filter_log,
                'final_pool': final_codes, 'final_pool_count': len(final_codes),
                'error': '回测期内收盘数据不足（< 2 个交易日）'}

    trading_dates = bt_close.index.tolist()

    # 预提取信号因子回测期面板（在筛选后的股票池内计算横截面排名）
    sig_panels: Dict[str, object] = {}
    for name in signal_names:
        if name in factor_panels:
            fp = factor_panels[name]
            sig_cols = [c for c in avail_codes if c in fp.columns]
            if sig_cols:
                sig_panels[name] = fp.loc[bt_mask, sig_cols]

    fee_rate         = 0.001
    n_slots          = max(1, min(max_holdings, len(avail_codes)))
    per_stock_budget = initial_cash / n_slots
    cash             = initial_cash
    positions: Dict[str, Dict] = {}
    equity_curve: List[float]  = [initial_cash]
    trade_log: List[Dict]      = []

    for date in trading_dates:
        date_str = str(date.date())

        # 计算各信号因子当日横截面分位排名
        factor_day_ranks: Dict[str, Dict] = {}
        composite_ranks:  Dict[str, float] = {}

        valid_sig = [n for n in signal_names if n in sig_panels]
        for code in avail_codes:
            per_factor = {}
            rank_vals  = []
            for sname in valid_sig:
                sp = sig_panels[sname]
                if code not in sp.columns or date not in sp.index:
                    continue
                day_series = sp.loc[date].dropna()
                if day_series.empty or code not in day_series.index:
                    continue
                raw  = float(day_series[code])
                rank = float(day_series.rank(pct=True)[code])
                per_factor[sname] = {'value': round(raw, 6), 'rank': round(rank, 4)}
                rank_vals.append(rank)
            factor_day_ranks[code] = per_factor
            composite_ranks[code]  = round(float(np.mean(rank_vals)), 4) if rank_vals else 0.5

        # ── 先执行卖出信号 ──────────────────────────────────────────────────
        for code in list(positions.keys()):
            comp = composite_ranks.get(code, 0.5)
            if code not in bt_close.columns:
                continue
            price_raw = bt_close.loc[date, code]
            if pd.isna(price_raw) or float(price_raw) <= 0:
                continue
            price = float(price_raw)
            if comp <= signal_sell_thresh:
                pos      = positions[code]
                proceeds = pos['shares'] * price * (1 - fee_rate)
                pnl      = proceeds - pos['entry_value']
                pnl_pct  = (proceeds / pos['entry_value'] - 1) * 100
                hold_days = (date - pd.Timestamp(pos['entry_date'])).days
                cash += proceeds
                trade_log.append({
                    'date': date_str, 'code': code, 'action': 'SELL',
                    'price': round(price, 3), 'shares': pos['shares'],
                    'amount': round(proceeds, 2),
                    'composite_rank': comp,
                    'factor_values': factor_day_ranks.get(code, {}),
                    'signal_buy_thresh': signal_buy_thresh,
                    'signal_sell_thresh': signal_sell_thresh,
                    'hold_days': hold_days,
                    'pnl': round(pnl, 2),
                    'pnl_pct': round(pnl_pct, 4),
                })
                del positions[code]

        # ── 再执行买入信号：候选排名最高、持仓数未满 max_holdings ────────────
        slots_free = max_holdings - len(positions)
        if slots_free > 0:
            buy_candidates = []
            for code in avail_codes:
                if code in positions:
                    continue
                comp = composite_ranks.get(code, 0.5)
                if comp < signal_buy_thresh:
                    continue
                if code not in bt_close.columns:
                    continue
                price_raw = bt_close.loc[date, code]
                if pd.isna(price_raw) or float(price_raw) <= 0:
                    continue
                buy_candidates.append((comp, code, float(price_raw)))
            buy_candidates.sort(key=lambda x: x[0], reverse=True)
            for comp, code, price in buy_candidates[:slots_free]:
                budget = min(per_stock_budget, cash * 0.99)
                if budget < price * 100:
                    continue
                shares = int(budget / price / 100) * 100
                if shares <= 0:
                    continue
                cost = shares * price * (1 + fee_rate)
                if cost > cash:
                    continue
                cash -= cost
                positions[code] = {'shares': shares, 'entry_price': price,
                                   'entry_date': date_str, 'entry_value': cost}
                trade_log.append({
                    'date': date_str, 'code': code, 'action': 'BUY',
                    'price': round(price, 3), 'shares': shares, 'amount': round(cost, 2),
                    'composite_rank': comp,
                    'factor_values': factor_day_ranks.get(code, {}),
                    'signal_buy_thresh': signal_buy_thresh,
                    'signal_sell_thresh': signal_sell_thresh,
                })

        # 当日组合净值
        pos_val = sum(
            positions[c]['shares'] * float(bt_close.loc[date, c])
            for c in positions
            if c in bt_close.columns and not pd.isna(bt_close.loc[date, c])
        )
        equity_curve.append(cash + pos_val)

    # 末日强制清仓
    last_date     = trading_dates[-1]
    last_date_str = str(last_date.date())
    for code in list(positions.keys()):
        pos = positions[code]
        if code in bt_close.columns and not pd.isna(bt_close.loc[last_date, code]):
            price     = float(bt_close.loc[last_date, code])
            proceeds  = pos['shares'] * price * (1 - fee_rate)
            pnl       = proceeds - pos['entry_value']
            pnl_pct   = (proceeds / pos['entry_value'] - 1) * 100
            hold_days = (last_date - pd.Timestamp(pos['entry_date'])).days
            cash += proceeds
            trade_log.append({
                'date': last_date_str, 'code': code, 'action': 'SELL(强平)',
                'price': round(price, 3), 'shares': pos['shares'],
                'amount': round(proceeds, 2),
                'composite_rank': None, 'factor_values': {},
                'signal_buy_thresh': signal_buy_thresh,
                'signal_sell_thresh': signal_sell_thresh,
                'hold_days': hold_days,
                'pnl': round(pnl, 2),
                'pnl_pct': round(pnl_pct, 4),
            })
    equity_curve[-1] = cash

    # ── 8. 计算业绩指标 ────────────────────────────────────────────────────
    total_ret_dec = (equity_curve[-1] / initial_cash) - 1.0
    trading_days  = len(trading_dates)
    bt_result = {
        'start_date':            start_date,
        'end_date':              end_date,
        'trading_days':          trading_days,
        'initial_cash':          initial_cash,
        'final_value':           round(equity_curve[-1], 2),
        'total_return_pct':      round(total_ret_dec * 100, 4),
        'annualized_return_pct': round(
            api.get_annualized_return(total_ret_dec, trading_days) * 100, 4),
        'max_drawdown_pct':      round(
            api.get_max_drawdown_pct(equity_curve) * 100, 4),
        'sharpe_ratio':          round(api.get_sharpe_ratio(equity_curve), 4),
        'equity_curve':          [round(v, 2) for v in equity_curve],
    }

    # ── 8.5. 基准线对比 ────────────────────────────────────────────────────
    _BENCHMARKS = [
        ('000001.SH', '上证指数'),
        ('000300.SH', '沪深300'),
        ('000905.SH', '中证500'),
        ('399006.SZ', '创业板指'),
    ]
    benchmarks_result: List[Dict] = []

    def _fetch_bench_close(ts_code: str, s_date: str, e_date: str) -> Dict[str, float]:
        """优先查本地 index_daily 表；若表不存在则 fallback 到东方财富爬虫。"""
        try:
            rows = api.get_index_daily(ts_codes=[ts_code], start_date=s_date, end_date=e_date)
            if rows:
                return {r.trade_date: r.close for r in rows}
        except Exception:
            pass
        import requests as _req
        code_part, mkt = ts_code.split('.')
        secid = f"1.{code_part}" if mkt == 'SH' else f"0.{code_part}"
        url = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'
        params = {
            'secid': secid,
            'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
            'klt': '101', 'fqt': '0',
            'beg': s_date.replace('-', ''), 'end': e_date.replace('-', ''),
            'lmt': '2000',
        }
        headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.eastmoney.com/'}
        resp = _req.get(url, params=params, headers=headers, timeout=10)
        klines = resp.json().get('data', {}).get('klines', [])
        result: Dict[str, float] = {}
        for kl in klines:
            parts = kl.split(',')
            if len(parts) >= 3:
                result[parts[0]] = float(parts[2])
        return result

    try:
        bench_map: Dict[str, Dict[str, float]] = {}
        for bcode, _ in _BENCHMARKS:
            try:
                bench_map[bcode] = _fetch_bench_close(bcode, start_date, end_date)
            except Exception:
                bench_map[bcode] = {}

        strat_daily_rets = []
        for i in range(1, len(equity_curve)):
            prev = equity_curve[i - 1]
            strat_daily_rets.append((equity_curve[i] / prev - 1.0) if prev else 0.0)

        for bcode, bname in _BENCHMARKS:
            date_close = bench_map.get(bcode, {})
            aligned: List[float] = []
            last_val: Optional[float] = None
            for d in trading_dates:
                v = date_close.get(str(d.date()))
                if v is not None:
                    last_val = v
                if last_val is not None:
                    aligned.append(last_val)
                elif aligned:
                    aligned.append(aligned[-1])

            if len(aligned) < 2:
                benchmarks_result.append({'code': bcode, 'name': bname, 'error': '数据不足'})
                continue

            base0 = aligned[0]
            bench_curve = [initial_cash] + [
                round(initial_cash * v / base0, 2) for v in aligned]

            b_total_ret_dec = (bench_curve[-1] / initial_cash) - 1.0
            b_td = len(bench_curve) - 1
            b_ann = api.get_annualized_return(b_total_ret_dec, b_td) if b_td > 0 else 0.0
            b_dd  = api.get_max_drawdown_pct(bench_curve)

            excess_ret_pct = round(bt_result['total_return_pct'] - b_total_ret_dec * 100, 4)

            bench_daily_rets = []
            for i in range(1, len(bench_curve)):
                prev = bench_curve[i - 1]
                bench_daily_rets.append((bench_curve[i] / prev - 1.0) if prev else 0.0)
            n_common = min(len(strat_daily_rets), len(bench_daily_rets))
            if n_common > 1:
                excess_daily = [strat_daily_rets[i] - bench_daily_rets[i] for i in range(n_common)]
                mu  = sum(excess_daily) / n_common
                std = _stat.stdev(excess_daily) if n_common > 1 else 0.0
                ir  = round((mu / std) * (252 ** 0.5), 4) if std > 1e-10 else 0.0
            else:
                ir = 0.0

            benchmarks_result.append({
                'code':                  bcode,
                'name':                  bname,
                'total_return_pct':      round(b_total_ret_dec * 100, 4),
                'annualized_return_pct': round(b_ann * 100, 4),
                'max_drawdown_pct':      round(b_dd * 100, 4),
                'excess_return_pct':     excess_ret_pct,
                'information_ratio':     ir,
                'equity_curve':          bench_curve,
            })
    except Exception as _e:
        benchmarks_result = [{'error': str(_e)}]

    # ── 8.6. 因子 IC 计算（Rank IC，斯皮尔曼相关系数，纯 numpy 实现）──────
    def _spearman_corr(x: np.ndarray, y: np.ndarray) -> float:
        rx = np.argsort(np.argsort(x)).astype(float)
        ry = np.argsort(np.argsort(y)).astype(float)
        mx, my = rx.mean(), ry.mean()
        num = ((rx - mx) * (ry - my)).sum()
        den = np.sqrt(((rx - mx) ** 2).sum() * ((ry - my) ** 2).sum())
        return float(num / den) if den > 1e-10 else 0.0

    ic_stats: Dict[str, Dict] = {}
    for _fname in list(dict.fromkeys(screen_names + signal_names)):
        if _fname not in factor_panels:
            continue
        _fp = factor_panels[_fname]
        _daily_ic: List[float] = []
        for _i in range(len(trading_dates) - 1):
            _d_cur  = trading_dates[_i]
            _d_next = trading_dates[_i + 1]
            if _d_cur not in _fp.index or _d_next not in bt_close.index:
                continue
            _factor_day = _fp.loc[_d_cur, avail_codes].dropna()
            _codes_c    = [c for c in _factor_day.index if c in bt_close.columns]
            if len(_codes_c) < 5:
                continue
            _ret_next = (bt_close.loc[_d_next, _codes_c] /
                         bt_close.loc[_d_cur,  _codes_c] - 1).dropna()
            _codes_v  = [c for c in _codes_c if c in _ret_next.index]
            if len(_codes_v) < 5:
                continue
            _rho = _spearman_corr(
                _factor_day[_codes_v].values,
                _ret_next[_codes_v].values,
            )
            if not np.isnan(_rho):
                _daily_ic.append(_rho)

        if len(_daily_ic) < 2:
            ic_stats[_fname] = {'error': '数据不足'}
            continue

        _ic_arr  = np.array(_daily_ic)
        _ic_mean = float(np.mean(_ic_arr))
        _ic_std  = float(np.std(_ic_arr, ddof=1))
        _ic_ir   = round(_ic_mean / _ic_std * (252 ** 0.5), 4) if _ic_std > 1e-10 else 0.0
        ic_stats[_fname] = {
            'ic_mean':     round(_ic_mean, 4),
            'ic_std':      round(_ic_std, 4),
            'ic_ir':       round(_ic_ir, 4),
            'ic_win_rate': round(float(np.mean(_ic_arr > 0)), 4),
            'ic_abs_mean': round(float(np.mean(np.abs(_ic_arr))), 4),
            'ic_series':   [round(v, 4) for v in _daily_ic],
            'n_days':      len(_daily_ic),
        }

    # ── 9. 统计各股表现，取 Top N ──────────────────────────────────────────
    stock_pnl: Dict[str, float] = {}
    for tr in trade_log:
        if tr['action'] in ('SELL', 'SELL(强平)'):
            code = tr['code']
            stock_pnl[code] = stock_pnl.get(code, 0.0) + tr.get('pnl', 0.0)

    top_codes = sorted(stock_pnl, key=lambda c: stock_pnl[c], reverse=True)[:top_n_stocks]
    top_stocks_detail = []
    for code in top_codes:
        code_trades = [tr for tr in trade_log if tr['code'] == code]
        top_stocks_detail.append({
            'code':      code,
            'total_pnl': round(stock_pnl[code], 2),
            'trades':    code_trades,
        })

    result = {
        'screen_k':            k_screen,
        'signal_k':            k_signal,
        'screen_factors':      screen_names,
        'signal_factors':      signal_names,
        'factor_descriptions': all_descs,
        'signal_config': {
            'buy_thresh':  signal_buy_thresh,
            'sell_thresh': signal_sell_thresh,
        },
        'screen_top_pcts':    screen_top_pcts,
        'initial_pool':       len(codes),
        'filter_log':         filter_log,
        'final_pool':         final_codes,
        'final_pool_count':   len(final_codes),
        'trade_log':          trade_log,
        'backtest':           bt_result,
        'benchmarks':         benchmarks_result,
        'ic_stats':           ic_stats,
        'top_stocks':         top_stocks_detail,
    }
    import io
    _buf = io.StringIO()
    import sys as _sys
    _old_stdout = _sys.stdout
    _sys.stdout = _buf
    try:
        _print_mining_result(result)
    finally:
        _sys.stdout = _old_stdout
    result['summary_text'] = _buf.getvalue()
    return result


def _split_desc(desc: str):
    """从描述字符串提取 (定义, 方向标签, 高值解读)"""
    import re
    parts = desc.split('。', 1)
    definition = parts[0] if parts else desc
    rest = parts[1] if len(parts) > 1 else ''
    if '正向因子' in rest:
        dir_tag = '↑正向'
    elif '反向因子' in rest:
        dir_tag = '↓反向'
    elif '反转因子' in rest:
        dir_tag = '↺反转'
    elif '条件正向' in rest:
        dir_tag = '◈条件'
    else:
        dir_tag = '  ─  '
    m = re.search(r'高值(?:\(\+1\))?表示(.+?)(?:，|$)', rest)
    high_interp = m.group(1).strip() if m else ''
    return definition, dir_tag, high_interp


def _ic_line(ic: dict) -> str:
    if not ic or 'error' in ic:
        return '（数据不足）'
    icir = ic['ic_ir']
    grade = '★★★优秀' if icir > 1 else ('★★良好' if icir > 0.5 else ('★一般' if icir > 0 else '✗反向'))
    return (f'ICIR={icir:.2f} {grade}  '
            f'IC均值={ic["ic_mean"]:+.4f}  '
            f'胜率={ic["ic_win_rate"]*100:.1f}%  '
            f'|IC|均值={ic["ic_abs_mean"]:.4f}')


def _print_mining_result(result: dict) -> None:
    """格式化打印因子挖矿结果（从 run_factor_mining.py 迁移）。"""
    import sys
    # 确保中文正常输出
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    sc          = result['signal_config']
    _scr_names  = result['screen_factors']
    _sig_names  = result['signal_factors']
    _descs      = result['factor_descriptions']
    _top_pcts   = result['screen_top_pcts']
    _ic_stats   = result.get('ic_stats', {})
    _flog       = result.get('filter_log', [])
    _buy_thr    = sc['buy_thresh']
    _sell_thr   = sc['sell_thresh']
    sep = '='*60

    # ── 本次挖矿战绩 ───────────────────────────────────────────────────────
    print(f'\n{sep}')
    print('【本次挖矿战绩】')
    print(sep)
    if result.get('backtest'):
        bt = result['backtest']
        tl = result.get('trade_log', [])
        n_buy  = sum(1 for t in tl if t['action'] == 'BUY')
        n_sell = sum(1 for t in tl if 'SELL' in t['action'])
        ret    = bt['total_return_pct']
        ann    = bt['annualized_return_pct']
        dd     = bt['max_drawdown_pct']
        ret_flag = '▲' if ret >= 0 else '▼'
        ann_flag = '▲' if ann >= 0 else '▼'
        print(f'  挖矿日期:   {datetime.today().strftime("%Y-%m-%d")}')
        print(f'  回测区间:   {bt["start_date"]}  →  {bt["end_date"]}（{bt["trading_days"]} 交易日）')
        print(f'  初始资金:   {bt["initial_cash"]:>14,.0f} 元')
        print(f'  期末资金:   {bt["final_value"]:>14,.2f} 元')
        print(f'  总收益率:   {ret_flag} {abs(ret):>10.4f} %')
        print(f'  年化收益率: {ann_flag} {abs(ann):>10.4f} %')
        print(f'  最大回撤:   ▼ {dd:>10.4f} %')
        print(f'  夏普比率:     {bt["sharpe_ratio"]:>10.4f}')
        print(f'  交易笔数:   买入 {n_buy} 笔 / 卖出 {n_sell} 笔（共 {n_buy+n_sell} 笔）')

    # ── 基准对比表 ─────────────────────────────────────────────────────────
    benchmarks = result.get('benchmarks', [])
    if benchmarks and result.get('backtest') and not any('error' in b and len(b) == 1 for b in benchmarks):
        bt = result['backtest']
        strat_ret = bt['total_return_pct']
        strat_ann = bt['annualized_return_pct']
        strat_dd  = bt['max_drawdown_pct']
        print(f'  {"─"*54}')
        print(f'  {"基准对比（同期）":<10}  {"总收益":>8}  {"年化收益":>8}  {"最大回撤":>8}  {"超额收益":>9}  {"信息比率":>8}')
        print(f'  {"─"*54}')
        ret_sym = '▲' if strat_ret >= 0 else '▼'
        ann_sym = '▲' if strat_ann >= 0 else '▼'
        print(f'  {"策略本身":<10}  {ret_sym}{abs(strat_ret):>7.2f}%  {ann_sym}{abs(strat_ann):>7.2f}%  ▼{strat_dd:>7.2f}%  {"—":>9}  {"—":>8}')
        for b in benchmarks:
            if 'error' in b:
                print(f'  {b.get("name", b.get("code", "?")):<10}  {"数据不足":>38}')
                continue
            b_ret = b['total_return_pct']
            b_ann = b['annualized_return_pct']
            b_dd  = b['max_drawdown_pct']
            exc   = b['excess_return_pct']
            ir    = b['information_ratio']
            rs  = '▲' if b_ret >= 0 else '▼'
            as_ = '▲' if b_ann >= 0 else '▼'
            es  = '▲' if exc >= 0 else '▼'
            print(f'  {b["name"]:<10}  {rs}{abs(b_ret):>7.2f}%  {as_}{abs(b_ann):>7.2f}%  ▼{abs(b_dd):>7.2f}%  {es}{abs(exc):>8.2f}%  {ir:>8.2f}')
        print(f'  {"─"*54}')
    print(sep)

    # ── 因子IC汇总表 ───────────────────────────────────────────────────────
    ic_stats = result.get('ic_stats', {})
    if ic_stats:
        _scr_set = set(_scr_names)
        _sig_set = set(_sig_names)
        print(f'\n{sep}')
        print('【因子IC评估（Rank IC，预测能力分析）】')
        print(f'  说明：IC为当日因子截面排名与次日收益率排名的斯皮尔曼相关系数')
        print(f'  {"─"*58}')
        print(f'  {"因子":<10} {"类型":>5}  {"IC均值":>8}  {"ICIR":>7}  {"胜率":>7}  {"|IC|均值":>9}  {"评级":<10}')
        print(f'  {"─"*58}')
        _all_ic_names = list(dict.fromkeys(_scr_names + _sig_names))
        for _fn in _all_ic_names:
            _ic = ic_stats.get(_fn, {})
            _tag = '[选+信]' if (_fn in _scr_set and _fn in _sig_set) else \
                   ('[选股]' if _fn in _scr_set else '[信号]')
            if 'error' in _ic:
                print(f'  {_fn:<10} {_tag:>5}  {"—":>8}  {"—":>7}  {"—":>7}  {"—":>9}  {"数据不足":<10}')
                continue
            _icm  = _ic['ic_mean']
            _icir = _ic['ic_ir']
            _win  = _ic['ic_win_rate'] * 100
            _abs  = _ic['ic_abs_mean']
            _grade = '★★★ 优秀' if _icir > 1 else ('★★ 良好' if _icir > 0.5 else
                     ('★ 一般' if _icir > 0 else '✗ 反向'))
            _icm_s = f'+{_icm:.4f}' if _icm >= 0 else f'{_icm:.4f}'
            print(f'  {_fn:<10} {_tag:>5}  {_icm_s:>8}  {_icir:>7.2f}  {_win:>6.1f}%  {_abs:>9.4f}  {_grade:<10}')
        print(f'  {"─"*58}')
        print(f'  评级标准：ICIR>1优秀 / >0.5良好 / >0一般 / ≤0反向（负IC因子通常反向使用）')

    # ── 因子深度解析 ───────────────────────────────────────────────────────
    print(f'\n{sep}')
    print('【因子深度解析】')
    print(sep)

    print(f'\n▌ 选股因子（{len(_scr_names)} 个，串联过滤压缩股票池至候选股）')
    for _i, _name in enumerate(_scr_names, 1):
        _pct   = _top_pcts.get(_name, 0)
        _ic    = _ic_stats.get(_name, {})
        _step  = next((s for s in _flog if s['factor'] == _name and s['status'] == 'ok'), {})
        _defn, _dtag, _hi = _split_desc(_descs.get(_name, ''))
        _before = _step.get('before', '?')
        _after  = _step.get('after', '?')
        print(f'\n  ▶ 第{_i}层  {_name}  [{_dtag}]  保留前{int(_pct*100)}%  （{_before} → {_after} 只）')
        print(f'    预测能力: {_ic_line(_ic)}')
        print(f'    因子定义: {_defn}')
        if _hi:
            print(f'    高值含义: {_hi}')

    print(f'\n▌ 信号因子（{len(_sig_names)} 个，逐日横截面排名驱动买卖）')
    print(f'  买入阈值: {_buy_thr}  → 综合排名前 {int((1-_buy_thr)*100)}% 触发买入')
    print(f'  卖出阈值: {_sell_thr}  → 综合排名后 {int(_sell_thr*100)}% 触发卖出')
    for _name in _sig_names:
        _ic   = _ic_stats.get(_name, {})
        _defn, _dtag, _hi = _split_desc(_descs.get(_name, ''))
        print(f'\n  ▶ {_name}  [{_dtag}]')
        print(f'    预测能力: {_ic_line(_ic)}')
        print(f'    因子定义: {_defn}')
        if _hi:
            print(f'    高值含义: {_hi}')

    # ── 选股过滤过程 ───────────────────────────────────────────────────────
    print()
    if result.get('filter_log'):
        print('【选股过滤过程】')
        for step in result['filter_log']:
            status  = step['status']
            pct_str = f'保留前{int(step.get("top_pct", 0)*100)}%'
            if status == 'ok':
                print(f'  {step["factor"]}  {pct_str}  截面日={step["ref_date"]}  '
                      f'{step["before"]} → {step["after"]} 只  '
                      f'（实留 {step["kept"]}/{step["snapshot_size"]}）')
            else:
                print(f'  {step["factor"]}  {pct_str}  跳过（{status}）  {step["before"]} 只不变')

    print(f'\n【最终入选】  {result["final_pool_count"]} 只')
    if result['final_pool']:
        print(f'  {result["final_pool"]}')

    # ── 回测结果 ───────────────────────────────────────────────────────────
    if 'error' in result:
        print(f'\n【错误】 {result["error"]}')
    elif 'backtest' in result:
        bt = result['backtest']
        print()
        print('【回测结果】（信号驱动买卖 / 等额资金分配）')
        print(f'  回测区间:   {bt["start_date"]}  →  {bt["end_date"]}')
        print(f'  交易天数:   {bt["trading_days"]} 日')
        print(f'  初始资金:   {bt["initial_cash"]:,.0f} 元')
        print(f'  期末资金:   {bt["final_value"]:,.2f} 元')
        print(f'  总收益率:   {bt["total_return_pct"]:+.4f} %')
        print(f'  年化收益率: {bt["annualized_return_pct"]:+.4f} %')
        print(f'  最大回撤:   {bt["max_drawdown_pct"]:.4f} %')
        print(f'  夏普比率:   {bt["sharpe_ratio"]:.4f}')
        ec  = bt['equity_curve']
        mid = len(ec) // 2
        print(f'  权益曲线（首/中/尾）:  [{ec[0]:,.0f}  ...  {ec[mid]:,.0f}  ...  {ec[-1]:,.0f}]')
        tl  = result.get('trade_log', [])
        print(f'  交易笔数:   买入 {sum(1 for t in tl if t["action"]=="BUY")} 笔 / '
              f'卖出 {sum(1 for t in tl if "SELL" in t["action"])} 笔')

    # ── Top N 个股详情 ─────────────────────────────────────────────────────
    top_stocks = result.get('top_stocks', [])
    buy_thr    = sc['buy_thresh']
    if top_stocks:
        print(f'\n{sep}')
        print(f'【Top {len(top_stocks)} 盈利个股详情】')
        for rank_i, stock in enumerate(top_stocks, 1):
            code      = stock['code']
            total_pnl = stock['total_pnl']
            trades    = stock['trades']
            print(f'\n  #{rank_i}  {code}   累计盈亏: {total_pnl:+,.2f} 元')
            print(f'  {"─"*54}')
            for tr in trades:
                action    = tr['action']
                comp_rank = tr.get('composite_rank')
                comp_str  = f'{comp_rank:.4f}' if comp_rank is not None else 'N/A'
                if action == 'BUY':
                    flag = f'>={buy_thr} ✓' if (comp_rank is not None and comp_rank >= buy_thr) else ''
                    print(f'  [买入]  {tr["date"]}  价格={tr["price"]:.3f}  综合排名={comp_str}  {flag}')
                else:
                    label = '卖出' if action == 'SELL' else '强平'
                    print(f'  [{label}]  {tr["date"]}  价格={tr["price"]:.3f}  '
                          f'持仓{tr.get("hold_days", "?")}日  '
                          f'盈亏={tr.get("pnl", 0):+,.2f}元 ({tr.get("pnl_pct", 0):+.2f}%)')

    # ── 本次策略参数速查卡 ─────────────────────────────────────────────────
    print(f'\n{sep}')
    print('【本次策略参数速查卡】')
    print(sep)
    _ref_date_str = next((s['ref_date'] for s in _flog if 'ref_date' in s), '?')
    print(f'\n▌ 选股因子  {len(_scr_names)} 个（截面日 {_ref_date_str} 静态过滤）')
    print(f'  保留比例随机范围: [5%, 20%]  每层独立抽取')
    for _i, _name in enumerate(_scr_names, 1):
        _pct  = _top_pcts.get(_name, 0)
        _step = next((s for s in _flog if s['factor'] == _name and s['status'] == 'ok'), {})
        _defn, _dtag, _hi = _split_desc(_descs.get(_name, ''))
        _b = _step.get('before', '?')
        _a = _step.get('after', '?')
        _ic = _ic_stats.get(_name, {})
        _ic_tag = ''
        if _ic and 'error' not in _ic:
            _icir = _ic['ic_ir']
            _ic_tag = f'  ICIR={_icir:.2f}{"★★★" if _icir>1 else ("★★" if _icir>0.5 else ("★" if _icir>0 else "✗"))}'
        print(f'  第{_i}层  {_name}  [{_dtag}]  本次保留前 {int(_pct*100)}%{_ic_tag}')
        print(f'         {_defn}')
        if _hi:
            print(f'         高值: {_hi}')
        print(f'         过滤: {_b} → {_a} 只')

    print(f'\n▌ 信号因子  {len(_sig_names)} 个（逐日截面排名，均值作综合排名）')
    print(f'  ┌ 买入阈值: {_buy_thr}  （随机范围 [0.55, 0.82]）  综合排名前 {int((1-_buy_thr)*100)}% 买入')
    print(f'  └ 卖出阈值: {_sell_thr}  （随机范围 [0.30, 0.55]）  综合排名后 {int(_sell_thr*100)}% 卖出')
    for _name in _sig_names:
        _defn, _dtag, _hi = _split_desc(_descs.get(_name, ''))
        _ic = _ic_stats.get(_name, {})
        _ic_tag = ''
        if _ic and 'error' not in _ic:
            _icir = _ic['ic_ir']
            _ic_tag = f'  ICIR={_icir:.2f}{"★★★" if _icir>1 else ("★★" if _icir>0.5 else ("★" if _icir>0 else "✗"))}'
        print(f'  {_name}  [{_dtag}]{_ic_tag}')
        print(f'         {_defn}')
        if _hi:
            print(f'         高值: {_hi}')

    print(f'\n▌ 持仓参数')
    if result.get('backtest'):
        bt = result['backtest']
        print(f'  候选池上限: {result["final_pool_count"]} 只  最大持仓: 5 只  单仓预算: 初始资金 ÷ 5')
        print(f'  回测区间: {bt["start_date"]} → {bt["end_date"]}  手续费: 买入+卖出各 0.1%')
    print(sep)
