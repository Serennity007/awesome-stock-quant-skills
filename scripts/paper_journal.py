#!/usr/bin/env python3
"""Freeze screening evidence and append buy-and-hold paper-account reviews. No network I/O."""
import argparse
import csv
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
import hashlib
import io
import json
from pathlib import Path
import re


MODEL = "equal-budget-round-lot-buy-and-hold-v1"
MARKET_TZ = timezone(timedelta(hours=8))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def number(value, label, positive=False):
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"invalid {label}") from exc
    if not result.is_finite() or (positive and result <= 0):
        raise ValueError(f"invalid {label}")
    return result


def money(value):
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def read_screen(path):
    raw = path if isinstance(path, bytes) else Path(path).read_bytes()
    with io.StringIO(raw.decode("utf-8-sig"), newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"code", "total", "score_status", "decision"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("screen CSV requires code,total,score_status,decision")
        rows = list(reader)
    if not rows:
        raise ValueError("screen CSV is empty")
    seen = set()
    for row in rows:
        if not re.fullmatch(r"[0-9]{6}", row["code"]) or row["code"] in seen:
            raise ValueError("screen codes must be unique six-digit codes")
        seen.add(row["code"])
        row["total"] = float(number(row["total"], "score"))
        if not 0 <= row["total"] <= 100:
            raise ValueError("screen score must be in [0,100]")
        if row["score_status"] not in ("complete", "partial"):
            raise ValueError("unknown score_status")
        if row["decision"] not in ("review_moat", "needs_data", "has_gaps", "not_fit"):
            # Older/custom screen exports may use other decisions, but none qualify silently.
            if not row["decision"]:
                raise ValueError("decision is required")
    return rows


def seal(folder, name, files):
    (folder / name).write_text(dump({file: digest(folder / file) for file in files}), encoding="utf-8")


def verify_seal(folder, name):
    payload = json.loads((folder / name).read_text(encoding="utf-8"))
    if not payload:
        raise ValueError("empty checksum record")
    for file, expected in payload.items():
        if Path(file).name != file or not (folder / file).is_file() or digest(folder / file) != expected:
            raise ValueError(f"evidence checksum mismatch: {file}")


def create_journal(screen, output, signal_date, data_kind, top=3, cash=1000000, cost_bps=10, lot_size=100):
    screen, output = Path(screen), Path(output)
    signal = date.fromisoformat(signal_date)
    if signal > datetime.now(MARKET_TZ).date():
        raise ValueError("signal date cannot be in the future")
    capital = number(cash, "initial cash", positive=True)
    rate = number(cost_bps, "cost bps")
    if top <= 0 or lot_size <= 0 or not 0 <= rate < 10000:
        raise ValueError("top/lot must be positive and cost bps in [0,10000)")
    if data_kind not in ("market_snapshot", "synthetic"):
        raise ValueError("explicit data kind required")
    source_bytes = screen.read_bytes()
    rows = read_screen(source_bytes)
    eligible = sorted((r for r in rows if r["score_status"] == "complete" and
                       r["decision"] == "review_moat" and r["total"] >= 70),
                      key=lambda r: (-r["total"], r["code"]))
    selected = eligible[:top]
    for row in selected:
        valuation = row.get("valuation_date", "")
        if not valuation or date.fromisoformat(valuation) > signal:
            raise ValueError("selected rows require a valuation date on/before the signal date")
    created = datetime.now(timezone.utc)
    snapshot = {
        "schema_version": 1, "model": MODEL, "created_at_utc": created.isoformat(),
        "engine_sha256": digest(Path(__file__)),
        "signal_date": signal_date, "data_kind": data_kind,
        "timing": "retrospective" if signal < created.astimezone(MARKET_TZ).date() else "created_on_signal_date",
        "state": "watchlist_pending_execution" if selected else "no_eligible_candidates",
        "initial_cash": money(capital), "cost_bps": float(rate), "lot_size": lot_size,
        "selection_rule": "score_status=complete AND decision=review_moat AND total>=70; score descending, code ascending",
        "top": top, "universe_count": len(rows),
        "complete_count": sum(r["score_status"] == "complete" for r in rows),
        "partial_count": sum(r["score_status"] == "partial" for r in rows),
        "eligible_count": len(eligible), "candidates": selected,
        "excluded": [{"code": r["code"], "score_status": r["score_status"],
                      "decision": r["decision"], "data_issues": r.get("data_issues", "")}
                     for r in rows if r not in eligible],
        "source_file": screen.name, "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "execution_assumption": "Buy at the first common imported closing-price observation strictly AFTER signal_date; fixed equal budgets, round lots, no rebalancing or forced final sale",
        "benchmark": "BENCHMARK rows in imported prices; untraded normalized price reference",
        "limitations": ["paper account, not broker trades or personal invested capital",
                        "imported data not independently verified; local timestamps/hashes are not notarized",
                        "closing-price execution assumption; no suspension, limit-price, spread or market-impact model",
                        "no dividend/corporate-action adjustment; provide consistently defined prices",
                        "review-observation drawdown is not a full daily drawdown"],
    }
    codes = ", ".join(r["code"] for r in selected) or "无符合条件标的"
    lines = ["# 模拟研究账户：起始记录", "",
             f"**数据类型：{data_kind}。仅为模拟研究记录，不是实盘账户或收益证明。**", "",
             f"- 创建时间：{snapshot['created_at_utc']}；信号日期：{signal_date}；时间属性：{snapshot['timing']}。",
             f"- 原始样本 {len(rows)} 只；完整 {snapshot['complete_count']} 只；不完整 {snapshot['partial_count']} 只。",
             f"- 固定规则：仅选择 complete / review_moat / 得分≥70，按得分与代码排序取前 {top} 只。",
             f"- 观察清单：{codes}。这是规则选择，尚未完成人工护城河复核。",
             f"- 模拟初始资金：{snapshot['initial_cash']:,.2f}；每笔买入假设成本 {float(rate):g} bps；每手 {lot_size} 股。", "",
             "## 初始复盘", "",
             "已冻结筛选结果、规则与参数。数据不完整的标的不进入候选清单。",
             "尚无后续价格、成交或持仓；收益、净值、基准比较均为待观察，不能写成 0% 实盘收益。",
             "下一步：在信号日之后收集候选与基准的同日收盘观察，核对来源和价格口径，再追加模拟复盘。", "",
             "## 文件", "", "- [冻结快照](snapshot.json) · [筛选输入](screen.csv) · [校验记录](checksums.json)",
             "- 后续复盘保存在 `reviews/`，同一复盘日期禁止覆盖。", ""]
    output.mkdir(parents=True, exist_ok=False)
    (output / "screen.csv").write_bytes(source_bytes)
    (output / "snapshot.json").write_text(dump(snapshot), encoding="utf-8")
    (output / "INITIAL_REVIEW.md").write_text("\n".join(lines), encoding="utf-8")
    files = ["screen.csv", "snapshot.json", "INITIAL_REVIEW.md"]
    metadata = Path(str(screen) + ".meta.json")
    if metadata.is_file():
        (output / "screen.meta.json").write_bytes(metadata.read_bytes())
        files.append("screen.meta.json")
    seal(output, "checksums.json", files)
    return snapshot


def read_reviews(folder, snapshot_hash):
    events, previous_hash = [], None
    for file in sorted((folder / "reviews").glob("????-??-??.json")):
        verify_seal(file.parent, file.stem + ".sha256.json")
        event = json.loads(file.read_text(encoding="utf-8"))
        if event["snapshot_sha256"] != snapshot_hash or event["previous_review_sha256"] != previous_hash:
            raise ValueError("review chain does not match the frozen snapshot")
        if event["review_date"] != file.stem:
            raise ValueError("review date/file mismatch")
        events.append(event)
        previous_hash = digest(file)
    return events, previous_hash


def read_prices(path, review_date):
    data = {}
    raw = path if isinstance(path, bytes) else Path(path).read_bytes()
    with io.StringIO(raw.decode("utf-8-sig"), newline="") as handle:
        reader = csv.DictReader(handle)
        if not {"date", "code", "close"}.issubset(reader.fieldnames or []):
            raise ValueError("price CSV requires date,code,close; include BENCHMARK rows")
        for row in reader:
            day = date.fromisoformat(row["date"])
            if day > review_date:
                raise ValueError("price input contains observations after the review date")
            code = row["code"]
            if code != "BENCHMARK" and not re.fullmatch(r"[0-9]{6}", code):
                raise ValueError("invalid observation code")
            key = (row["date"], code)
            if key in data:
                raise ValueError("duplicate price observation")
            data[key] = number(row["close"], "close", positive=True)
    return data


def append_review(folder, prices, review_date, notes=""):
    folder, prices = Path(folder), Path(prices)
    day = date.fromisoformat(review_date)
    if day > datetime.now(MARKET_TZ).date():
        raise ValueError("review date cannot be in the future")
    verify_seal(folder, "checksums.json")
    snapshot = json.loads((folder / "snapshot.json").read_text(encoding="utf-8"))
    if snapshot["model"] != MODEL:
        raise ValueError("unsupported paper-account model")
    snap_hash = digest(folder / "snapshot.json")
    events, previous_hash = read_reviews(folder, snap_hash)
    if review_date <= (events[-1]["review_date"] if events else snapshot["signal_date"]):
        raise ValueError("review dates must strictly increase after the signal date")
    if not snapshot["candidates"]:
        raise ValueError("no eligible candidates in this frozen snapshot")
    price_bytes = prices.read_bytes()
    observed = read_prices(price_bytes, day)
    codes = [r["code"] for r in snapshot["candidates"]]
    required = codes + ["BENCHMARK"]
    if any((review_date, code) not in observed for code in required):
        raise ValueError("review-date prices missing for a candidate or BENCHMARK")
    capital = number(snapshot["initial_cash"], "capital", positive=True)
    if events:
        entry_date, entries = events[0]["entry_date"], events[0]["entries"]
        cash = number(events[0]["cash_after_entry"], "cash")
        benchmark_entry = number(events[0]["benchmark_entry"], "benchmark entry", positive=True)
        if (entry_date, "BENCHMARK") in observed and observed[(entry_date, "BENCHMARK")] != benchmark_entry:
            raise ValueError("input revises the frozen benchmark entry price")
        # New input may extend history but cannot silently revise a recorded observation.
        for event in events:
            for code, close in event["observed_closes"].items():
                key = (event["review_date"], code)
                if key in observed and observed[key] != number(close, "recorded close"):
                    raise ValueError("input revises a previously recorded price")
        for entry in entries:
            key = (entry_date, entry["code"])
            if key in observed and observed[key] != number(entry["entry_price"], "entry price"):
                raise ValueError("input revises the frozen entry price")
    else:
        common = sorted({d for d, _ in observed if d > snapshot["signal_date"] and
                         all((d, code) in observed for code in required)})
        if not common:
            raise ValueError("no common observation strictly after the signal date")
        entry_date = common[0]
        budget, rate = capital / len(codes), number(snapshot["cost_bps"], "cost") / 10000
        entries, cash = [], capital
        for code in codes:
            price = observed[(entry_date, code)]
            lot = snapshot["lot_size"]
            shares = int((budget / (price * (1 + rate)) / lot).to_integral_value(rounding=ROUND_DOWN)) * lot
            if not shares:
                raise ValueError(f"equal budget cannot buy one lot of {code}")
            notional = Decimal(str(money(price * shares)))
            fee = Decimal(str(money(notional * rate)))
            cash -= notional + fee
            entries.append({"code": code, "shares": shares, "entry_price": float(price), "fee": float(fee)})
        if cash < 0:
            raise ValueError("entry costs exceed paper capital")
        benchmark_entry = observed[(entry_date, "BENCHMARK")]
    holdings = [{**entry, "close": float(observed[(review_date, entry["code"])]),
                 "market_value": money(observed[(review_date, entry["code"])] * entry["shares"])} for entry in entries]
    equity = cash + sum((Decimal(str(h["market_value"])) for h in holdings), Decimal(0))
    net_return = float(equity / capital - 1)
    benchmark_return = float(observed[(review_date, "BENCHMARK")] / benchmark_entry - 1)
    peak = max([capital, equity] + [number(e["equity"], "equity") for e in events])
    drawdown = min([float(equity / peak - 1), 0.0] + [e["max_drawdown_at_reviews"] for e in events])
    event = {"schema_version": 1, "data_kind": snapshot["data_kind"], "model": MODEL,
             "engine_sha256": digest(Path(__file__)),
             "created_at_utc": datetime.now(timezone.utc).isoformat(), "review_date": review_date,
             "signal_date": snapshot["signal_date"], "entry_date": entry_date,
             "state": "paper_holding", "snapshot_sha256": snap_hash,
             "previous_review_sha256": previous_hash, "prices_sha256": hashlib.sha256(price_bytes).hexdigest(),
             "entries": entries, "holdings": holdings, "cash_after_entry": money(cash),
             "benchmark_entry": float(benchmark_entry), "equity": money(equity),
             "net_pnl": money(equity - capital), "net_return": net_return,
             "benchmark_return": benchmark_return, "excess_return_pp": (net_return - benchmark_return) * 100,
             "max_drawdown_at_reviews": drawdown,
             "observed_closes": {code: float(observed[(review_date, code)]) for code in required},
             "notes": notes, "note_origin": "user_supplied" if notes else "none",
             "limitations": snapshot["limitations"]}
    lines = [f"# 模拟复盘 {review_date}", "",
             f"**{snapshot['data_kind']} / {MODEL}。模拟核算，不是实盘经历或真实成交。**", "",
             f"- 实际生成时间：{event['created_at_utc']}。历史日期是观察标签，不代表当日已发布。",
             f"- 冻结信号日：{snapshot['signal_date']}；首次共同价格观察日（模拟建仓）：{entry_date}。",
             f"- 模拟总资产：{event['equity']:,.2f}；现金：{money(cash):,.2f}；累计净损益：{event['net_pnl']:,.2f}。",
             f"- 模拟净收益：{net_return:.4%}；同起点基准价格收益：{benchmark_return:.4%}；差值：{event['excess_return_pp']:.4f} 个百分点。",
             f"- 仅按已有复盘观察点计算的最大回撤：{drawdown:.4%}，不是完整日频回撤。", "",
             "## 持仓与核算", "", "| 代码 | 股数 | 模拟买入价 | 当前观察价 | 首次买入费用 | 市值 |", "|---|---:|---:|---:|---:|---:|"]
    lines += [f"| {h['code']} | {h['shares']} | {h['entry_price']:.4f} | {h['close']:.4f} | {h['fee']:.2f} | {h['market_value']:.2f} |" for h in holdings]
    lines += ["", "## 复盘结论（按记录自动生成）", "",
              "入选依据保持起始快照中的规则与排序。本次只更新观察价格，不根据事后涨跌修改入选理由。",
              "成本在首次建仓时计入；当前模型继续持有，不生成卖出、止损或再平衡交易。",
              "价格变化的市场原因未在本记录中核实，不编写新闻归因或虚构人工交易心得。", "",
              "## 人工补充", "", notes or "未提供人工复盘。可通过 --notes-file 附加带出处的观察与下一步假设。", "",
              "## 下一步", "", "补充下一个共同观察日的候选与基准价格，核对数据来源、复权口径和实际可成交条件。", "",
              f"[结构化记录]({review_date}.json) · [导入价格]({review_date}.prices.csv) · [校验记录]({review_date}.sha256.json)", ""]
    reviews = folder / "reviews"
    reviews.mkdir(exist_ok=True)
    names = [review_date + ext for ext in (".json", ".md", ".prices.csv", ".sha256.json")]
    if any((reviews / name).exists() for name in names):
        raise ValueError("review output already exists; previous records cannot be overwritten")
    (reviews / names[0]).write_text(dump(event), encoding="utf-8")
    (reviews / names[1]).write_text("\n".join(lines), encoding="utf-8")
    (reviews / names[2]).write_bytes(price_bytes)
    seal(reviews, names[3], names[:3])
    return event


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("start", help="freeze screening data; no entry price or return is invented")
    start.add_argument("--screen", type=Path, required=True)
    start.add_argument("--output", type=Path, required=True)
    start.add_argument("--signal-date", required=True)
    start.add_argument("--data-kind", choices=("market_snapshot", "synthetic"), required=True)
    start.add_argument("--top", type=int, default=3)
    start.add_argument("--cash", type=float, default=1000000)
    start.add_argument("--cost-bps", type=float, default=10)
    start.add_argument("--lot-size", type=int, default=100)
    review = sub.add_parser("review", help="append a dated review using explicit imported observations")
    review.add_argument("--journal", type=Path, required=True)
    review.add_argument("--prices", type=Path, required=True)
    review.add_argument("--review-date", required=True)
    review.add_argument("--notes-file", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "start":
            result = create_journal(args.screen, args.output, args.signal_date, args.data_kind,
                                    args.top, args.cash, args.cost_bps, args.lot_size)
        else:
            notes = args.notes_file.read_text(encoding="utf-8") if args.notes_file else ""
            result = append_review(args.journal, args.prices, args.review_date, notes)
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")
    print(f"Recorded: {result['state']} / {result['data_kind']}; paper research only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
