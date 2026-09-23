# 🚀 米国人気AI株トラッカー｜8銘柄モメンタムを一画面で把握

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007（オリジナル）| License：MIT | データ：akshare（新浪財経の米国株日足）

米国AI株の潮流を一画面で追う。NVDA、AVGO、ORCL、GOOGL、SNDK、WDC、PLTR、TSLAの8銘柄をカバーし、akshareの新浪財経米国株日足をもとに現在値、日次騰落率、20/60日モメンタム、52週高安位置、出来高異常を機械的に出力。20日モメンタムで降順ソートし、強い銘柄と弱い銘柄を即座に判別できます。

## クイックスタート

```bash
pip install akshare pandas

# デフォルトリスト（AIコンピュート / ストレージ / AIアプリ / robotaxi）
python scripts/us_hot.py

# カスタム銘柄
python scripts/us_hot.py --tickers NVDA,AAPL,MSFT,AMD

# CSV出力
python scripts/us_hot.py --out us_hot.csv
```

## デフォルト追跡リスト

| テーマ | 銘柄 | キーパーソン |
|---|---|---|
| AIコンピュート | NVDA、AVGO、ORCL、GOOGL | ジェンセン・フアン（NVDA） |
| ストレージ | SNDK、WDC | — |
| AIアプリ | PLTR | Alex Karp |
| robotaxi / 人物概念 | TSLA | イーロン・マスク |

題材タグ、キーパーソン、近期の注目点とリスクについては `references/watchlist.md` を参照してください。

## 出力フィールド

| フィールド | 説明 |
|---|---|
| `ticker` | ティッカーシンボル |
| `theme` | テーマタグ |
| `price` | 最新終値（未復権日足の最新終値、`adjust=""`） |
| `change_pct` | 前日比騰落率（%、未復権終値ベース） |
| `mom_20` | 20日モメンタム（%、前復権終値ベース） |
| `mom_60` | 60日モメンタム（%、前復権終値ベース） |
| `dist_52w_high` | 過去252日高値からの距離（%、前復権高安値ベース） |
| `dist_52w_low` | 過去252日安値からの距離（%、前復権高安値ベース） |
| `vol_ratio` | 出来高 / 20日平均出来高（未復権出来高ベース） |

## 関連ファイル

- `SKILL.md` — スキル定義と使い方
- `scripts/us_hot.py` — メインスクリプト（`--tickers`、`--out`、`--sort` をサポート）
- `references/watchlist.md` — 銘柄のテーマタグ、キーパーソン、近期の注目点

## データについて

- 日足データは akshare `stock_us_daily`（新浪財経の米国株日足）から取得します。
- 現在値、騰落率、出来高は**未復権**日足（`adjust=""`）を使用し、復権係数の不備による価格の歪みを避けます。
- 20/60日モメンタム、52週高安値距離は**前復権**日足（`adjust="qfq"`）を使用し、長期間での比較可能性を確保します。

## 免責事項

学習・研究目的のみ。投資助言ではありません。過去の価格やモメンタムが将来のパフォーマンスを保証するものではなく、取引判断は必ずファンダメンタルズ、市場環境、個人のリスク許容度に基づいて独立に行ってください。
