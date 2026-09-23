# 🦎 マクロ・カメレオン｜ドラッケンミラー式フレックス・ダッシュボード

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | License：MIT | データ：akshare（中国銀行/新浪/東方財富/同花順公開API）

寄り付き前に、世界の資金の流れを一目確認しましょう。本スキルはスタンレー・ドラッケンミラー（Stanley Druckenmiller）のマクロ投資哲学をベースに、**7 大資産クラス**のトレンドとモメンタムを1枚の表に圧縮します：USD/CNY、中米 10 年国債利回り、金、原油、銅、A 株主要指数、および任意の個別銘柄。出力はトレードシグナルではなく、トレンドフォロー視点の**多空バイアス・スナップショット**です。

## クイックスタート

```bash
pip install akshare pandas

# デフォルト 20 日ウィンドウ、CSV 出力
python scripts/macro_dashboard.py

# ウィンドウと出力パスを指定
python scripts/macro_dashboard.py --days 20 --out macro_dashboard.csv

# 個別銘柄を追加して同時スキャン
python scripts/macro_dashboard.py --days 20 --codes 600519,000858,600036 --out my_dashboard.csv
```

## パラメータ

- `--days`: トレンド/モメンタム計算ウィンドウ（デフォルト 20）
- `--codes`: カンマ区切りの A 株個別銘柄コード（オプション）
- `--out`: CSV 出力パス（デフォルト `macro_dashboard.csv`）
- `--no-proxy`: システムプロキシを無効化（スクリプトは既定でプロキシを迂回済み；旧呼び出しとの互換用）

> プロキシ注記：起動時に `HTTP_PROXY` / `HTTPS_PROXY` 環境変数をクリアし、ローカルプロキシ（例：`127.0.0.1:7890`）がデータ源を遮断するのを防ぎます。東方財富/優先APIを先に試し、失敗時は新浪/中国銀行/同花順に自動降格します。

## 出力フィールド

| フィールド | 説明 |
|---|---|
| `asset` | 資産名 |
| `category` | 資産カテゴリ（fx / bond_cn / bond_us / commodity / equity / stock） |
| `current` | 最新終値/利回り/為替レート |
| `ma_n` | N 日移動平均 |
| `roc_n` | N 日騰落率% |
| `roc_5` | 直近 5 日騰落率% |
| `trend` | トレンド描述（上昇/下降/もみ合い/転換） |
| `signal` | トレンドシグナル（BULLISH / BEARISH / NEUTRAL） |
| `bias` | 多空バイアス描述（例："美元偏空"、"中债偏多"） |
| `source` | 実際に使用されたデータ源 |

## 判定ロジック

```
BULLISH = 終値 > N 日移動平均 かつ N 日騰落率 > 0
BEARISH = 終値 < N 日移動平均 かつ N 日騰落率 < 0
NEUTRAL = それ以外
```

国債利回りの方向は債券価格と逆方向です：利回り上昇 = 債券偏空。スクリプトの最後には総合マクロ・スコアと全体的なスタンス・ヒントが出力されます。

## 関連ファイル

- `SKILL.md` — スキル定義と詳細な使い方
- `scripts/macro_dashboard.py` — マクロ・ダッシュボード・スクリプト
- `references/druckenmiller_style.md` — ドラッケンミラー投資思想の要点整理

## 免責事項

学習・研究目的のみ。投資助言ではありません。マクロ・トレンドとモメンタムは過去の価格統計に基づくもので、将来のパフォーマンスを保証するものではありません。結果は必ず自身のマクロ環境、流動性、リスク許容度で再確認してください。
