# 🤝 マスター合意スクリーナー｜クロスフレームワーク交差合成器

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | ライセンス：MIT | 依存：pandas のみ（純ローカルCSV合成、ネットワーク呼び出しなし）

> **「複数の独立した手法が同時に同じ銘柄を指すとき、確率に重みを付けられる。」**

本スキルは、リポジトリ内の任意のマスタースキルのスコア結果CSV（各 `screen.py` の出力、`code`/`total` 列を含む）をクロスフレームワーク合意リストに合成します：フレームワーク内パーセンタイル正規化 → 合意スコア（各フレームワークのパーセンタイル平均）+ トップヒット数 + カバーフレーム数、そして交差銘柄を出力。

## 目次

- `SKILL.md` — スキル定義、合意ロジック、使用方法
- `scripts/ensemble.py` — 合意合成器（数秒で完了、ネットワーク呼び出しなし）
- `references/ensemble_methodology.md` — 方法論：パーセンタイル正規化の理由、フレームワーク競合の解釈、合意の限界
- `consensus_hs300_demo.csv` — デモ：但斌+李録+オニール3フレームワーク滬深300全量合意

## クイックスタート

```bash
pip install pandas

# ステップ1：各マスターフレームワークを全量実行（同一プール、例：--pool hs300）
python ../dan-bin-rose-of-time/scripts/screen.py --pool hs300 --out danbin_hs300_result.csv
python ../li-lu-value-compounding/scripts/screen.py --pool hs300 --out lilu_hs300_result.csv
python ../oneil-canslim/scripts/screen.py --pool hs300 --out canslim_hs300_result.csv

# ステップ2：合意リストに合成
python scripts/ensemble.py \
    --csvs ../dan-bin-rose-of-time/danbin_hs300_result.csv \
           ../li-lu-value-compounding/lilu_hs300_result.csv \
           ../oneil-canslim/canslim_hs300_result.csv \
    --min-frameworks 2 --out consensus.csv
```

## パラメータ

- `--csvs`：最低2つの結果CSV。ファイル名から `_result` 等の接尾辞を除いたものがフレームワーク名。
- `--top-pct`：フレームワーク内「トップヒット」分位ライン（デフォルト上位10%）。
- `--min-frameworks`：出力に必要な最低カバーフレーム数（デフォルト2）。
- `--out`：合意CSV出力パス（デフォルト `consensus.csv`）。

## 出力フィールド

- `code` / `name` / `industry`：コード / 略称 / 業種
- `consensus_score`：合意スコア（カバーフレームのパーセンタイル平均、0-100）
- `top_hits`：各フレームワークの上位10%に入ったフレームワーク数
- `frameworks`：カバーフレーム数
- `<フレームワーク>_pct` / `<フレームワーク>_raw`：フレームワーク内パーセンタイルと生スコア

## 免責事項

学習・研究目的のみ。投資助言ではありません。合意スコアは共通のデータ誤りを検証せず、フレームワーク間も完全に独立ではなく、過去の一致は将来の一致を保証しません。
