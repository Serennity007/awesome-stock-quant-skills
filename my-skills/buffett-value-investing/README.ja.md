# buffett-value-investing

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007（オリジナル作品）。

A株バフェット式バリュー投資スキル：堀（モート）評価、5年連続 ROE／粗利率／負債比率／営業キャッシュフローのスクリーニング、安全マージン評価。

## ディレクトリ構成

- `SKILL.md` — スキル定義と使い方
- `scripts/screen.py` — バフェット基準による一括スクリーニングとスコアリング（CSV＋ターミナル表）
- `scripts/analyze.py` — 個別株の完全分析（堀チェックリスト＋財務トレンド＋バリュエーション範囲）
- `references/buffett_principles.md` — バフェットの核心原則まとめ
- `references/scoring_rules.md` — スコアリングルールと既知の制限

## クイックスタート

```bash
pip install akshare pandas

# スクリーニング（デフォルトのプール：CSI300 構成銘柄）
python scripts/screen.py --pool hs300 --top 20 --out result.csv

# カスタムプール
python scripts/screen.py --codes 600519,000858,600036

# 個別株分析
python scripts/analyze.py 600519
```

依存：`akshare`、`pandas`（Python 3.9+）。

## 免責事項

学習・研究目的のみ。投資助言ではありません。スコアリングは初回フィルターに過ぎず、最終判断はビジネス自体への理解（能力圏の原則）に基づく必要があります。

## データ充足と評価日付（2026-10-24）

`score_status`、`decision`、`data_issues`、実際の年報期と評価日、`.meta.json` を出力します。`partial` / `needs_data` は追加確認が必要で、単年の粗利益率を5年の安定性と見なしません。5年の日付範囲と TTM 列を明示し、最新の無効値を古い値で補わず、同日の価格・PE から EPS を推算します。共通処理は `scripts/research_data.py`、詳細は [SKILL.md](SKILL.md)。
