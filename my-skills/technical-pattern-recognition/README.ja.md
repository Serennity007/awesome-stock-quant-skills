# technical-pattern-recognition

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

A株テクニカルパターン認識 Skill（Claude Code / Agent Skills 形式）：akshare 新浪日足をもとに、移動平均線のパーフェクトオーダー/逆オーダー、MACD ゴールデン/デッドクロス、出来高を伴う N 日高値ブレイク、出来高減少の押し目を機械的に認識し、構造化されたシグナル表を出力して AI の解釈に供します。

作者：Serennity007 | License：MIT | データ：akshare（新浪日足、前復権）

## クイックスタート

```bash
pip install akshare pandas
python scripts/patterns.py 600519,601318 --days 250 --window 60 --out signals.csv
```

## シグナル一覧

| シグナル | 意味 |
|---|---|
| `MA_BULLISH` / `MA_BEARISH` | 移動平均線のパーフェクトオーダー / 逆オーダー |
| `MACD_GOLDEN` / `MACD_DEATH` | MACD ゴールデン / デッドクロス（直近3本以内） |
| `VOL_BREAKOUT` | 出来高を伴う N 日高値ブレイク（量比 ≥ 1.5） |
| `PULLBACK_MA` | 上昇トレンド中の出来高減少の MA20 押し目 |

判定の詳細は [references/patterns.md](references/patterns.md)、実実行の出力は [docs/demo.md](docs/demo.md) を参照。

## 免責事項

学習・研究目的のみ。投資助言ではありません。テクニカルパターンは遅行指標であり、どのシグナルも失敗し得ます。
