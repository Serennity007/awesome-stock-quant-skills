# 🚀 張磊・高瓴の長期構造価値投資｜A株“時間の友”を4次元レーダーで発見

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | ライセンス：MIT | データ：akshare（東方財富・新浪公開API）

> **「私たちは起業家であり、たまたま投資家の役割を担っているだけだ。」**

このスキルは、張磊（チャン・レイ）の著書『Value（価値）』で提唱された**長期構造価値投資**フレームワークをA株市場に応用します。チャート予測もホットテーマ追跡もせず、4つの財務指標を継続的に適用して「時間の友」となる企業の成長質を測定します：連続増収増益、長期投資、業界成長余地、ROE上昇。結果は構造化されたCSVで出力され、経営者、モート、能力の輪による定性的分析へつなげられます。

## ファイル一覧

- `SKILL.md` — スキル定義、4次元スコアリングロジック、使い方
- `scripts/screen.py` — A株長期構造価値スクリーナー（CSV + ターミナル表）
- `references/zhang_lei_principles.md` — 張磊の核心原則：長期主義、動的モート、人が最大のリスク管理、中国・テクノロジー創新への集中、バーベル戦略

## クイックスタート

```bash
pip install akshare pandas

# デフォルト：沪深300成分銘柄を対象に、上位20銘柄を出力
python scripts/screen.py --pool hs300 --top 20 --out result.csv

# カスタムの小さな銘柄プールで検証
python scripts/screen.py --codes 600519,000858,600036 --out result.csv
```

## パラメータ

- `--pool`: 銘柄プール。現在は `hs300`（沪深300）をサポート。
- `--codes`: カンマ区切りのカスタム銘柄コード。`--pool` より優先される。
- `--top`: ターミナル表示する上位件数（デフォルト 20）。
- `--out`: CSV出力パス（デフォルト `zhang_lei_screen_result.csv`）。

## 4次元成長質レーダー

| 次元 | 指標 | 説明 |
|---|---|---|
| 連続増収増益 | 直近5年間で売上高・純利益ともに前年比プラスだった年数 | 4–5年が理想 |
| 長期投資 | 研究開発費率 または 設備投資/売上高比率 | 高くかつ上昇傾向なら未来への投資 |
| 業界成長余地 | 最新年度の売上高成長率 vs 業界平均 | 業界を上回る成長は構造的シェア拡大のサイン |
| ROEトレンド | 直近5年のROE推移 | 最新ROEが平均を上回り、上昇傾向が理想 |

## 出力フィールド

- `code` / `name` / `industry`：銘柄コード / 名称 / 業界
- `score_total`：総合スコア（満点100）
- `score_growth` / `score_investment` / `score_industry` / `score_roe_trend`：各次元スコア
- `double_growth_years`：売上・利益両成長年数
- `avg_rev_growth` / `avg_profit_growth`：直近5年の平均成長率
- `rd_ratio_avg` / `capex_to_rev_avg`：平均R&D比率 / 設備投資対売上高比率
- `industry_avg_rev_growth` / `market_median_rev_growth`：業界平均 / 全市場中央値
- `roe_latest` / `roe_5y`：最新ROE / 5年系列
- `data_years` / `source` / `note`：有効年数 / データソース / フォールバック説明

## 免責事項

本スキルは学習・研究目的のみであり、投資助言を構成しません。過去の財務指標が将来のパフォーマンスを保証するものではありません。スクリーニング結果は、あなた自身の事業理解（能力の輪）で再確認してください。
