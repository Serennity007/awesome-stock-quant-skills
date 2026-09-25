# templeton-global-contrarian

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007（オリジナル作品）。

A株テンプルトン式グローバル逆行投資スキル：52週安値圏、PE/PB過去10パーセンタイル以下、出来高縮小後の安定化、黒字維持銘柄をスクリーニングし、極度の悲観から逆張り買いのウォッチリストを作成します。

## ディレクトリ構成

- `SKILL.md` — スキル定義と使い方
- `scripts/contrarian_scan.py` — テンプルトン式逆行シグナルの一括スキャン（CSV＋ターミナル表）
- `references/templeton_rules.md` — テンプルトンの「極度悲観原則」、16の投資法則、グローバルな割安探し、サイクル観

## クイックスタート

```bash
pip install akshare pandas

# スクリーニング（デフォルトのプール：CSI300 構成銘柄）
python scripts/contrarian_scan.py --pool hs300 --top 20 --out result.csv

# カスタムプール
python scripts/contrarian_scan.py --codes 600519,000858,600036 --out result.csv
```

依存：`akshare` 1.18.96、`pandas`（Python 3.11+）。

## 免責事項

学習・研究目的のみ。投資助言ではありません。スキャン結果はあくまでウォッチリストであり、最終判断は企業、業界サイクル、貸借対照表への独自の理解（能力圏の原則）に基づく必要があります。
