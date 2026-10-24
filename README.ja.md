[中文](README.md) · [English](README.en.md) · [日本語](README.ja.md)

![Stock Quant Skills](.github/quant-research.svg)

# AI 銘柄スクリーニング・クオンツ研究ツールチェーン

`awesome-stock-quant-skills`

[![GitHub Stars](https://img.shields.io/github/stars/Serennity007/awesome-stock-quant-skills?style=flat-square&color=00d4ff)](https://github.com/Serennity007/awesome-stock-quant-skills/stargazers) [![GitHub Forks](https://img.shields.io/github/forks/Serennity007/awesome-stock-quant-skills?style=flat-square&color=8b5cf6)](https://github.com/Serennity007/awesome-stock-quant-skills/forks) [![Original code: MIT](https://img.shields.io/badge/original_code-MIT-22c55e?style=flat-square)](LICENSE)

投資手法を Agent Skills と Python スクリプトで実装。財務スクリーニング、ファクター評価、複数手法の比較、取引費用を含むバックテストに対応し、A 株研究と米国注目銘柄の追跡を扱います。

**拡張版：オリジナル Skill 30 件 · 投資手法の参考フレームワーク 23 件 · Python スクリプト 32 本 · 動作テスト 35 件合格。**

GitHub は **41 Stars / 8 Forks**（2026-10-24 時点）。オリジナル実装と第三者ソースを区分し、16 のソースディレクトリに 225 の `SKILL.md` を収録しています。

<!-- inventory: originals=30 mirrors=16 vendored=225 -->

**[拡張版を使う](https://github.com/Serennity007/awesome-stock-quant-skills/tree/codex/quant-skills-refresh) · [検証範囲](https://github.com/Serennity007/awesome-stock-quant-skills/blob/c46da26575289ddaab5587d31e7f718f9ac22a2e/docs/validation.md) · [実データ実行記録](https://github.com/Serennity007/awesome-stock-quant-skills/blob/c46da26575289ddaab5587d31e7f718f9ac22a2e/examples/verification/2026-10-24/buffett-check.json)**

## 具体的な研究タスクと出力

財務品質・割安度、成長・モメンタム・テーマ、複数フレームワークの順位比較、月次回測を扱います。項目別スコア、財報期、評価日、カバレッジ、入力ハッシュ、費用と保有明細を出力から確認できます。

拡張版は年報期・TTM・評価日の整合性、欠損財務と合意入力を検証します。23 の手法 Skill は公開投資手法のルール化した参考実装です。

## 実データと動作の検証

2026-10-24、**AKShare 1.19.3** で **600519** の取得・スクリーニングを実行。**2021–2025 年報**と **2026-10-23** の評価観測を確認し、**35 件の動作テスト**に合格しました。JSON・CSV・再現手順を公開しています。これは取得と計算の検証であり、投資収益には別の根拠が必要です。

## 実装を確認できる強み

| 機能 | 確認先 |
|---|---|
| 目的に応じて skill を選び、データ時点を確認 | [研究ワークフロー](my-skills/quant-research-workflow/SKILL.md) |
| 財務項目別のスコアリング | [Buffett ルール](my-skills/buffett-value-investing/references/scoring_rules.md)、[全オリジナル一覧](README.md#原创技能) |
| パーセンタイルによる合成と入力検証 | [ensemble.py](my-skills/master-ensemble/scripts/ensemble.py) |
| 入力 SHA-256・パラメータ・実行時刻の保存 | [合成データ](examples/ensemble)、[動作テスト](tests/test_ensemble.py) |
| 制約を明示した月次バックテスト | [回測方法論](my-skills/framework-backtest/references/backtest_methodology.md) |
| 上流コミット・ライセンス・アーカイブ状態・AKShare 版の定期確認テンプレート | [保守手順](docs/maintenance.md)、[ワークフロー](docs/workflows/upstream-watch.yml) |

件数はディレクトリとファイルの集計であり、全 API の動作保証ではありません。[検証記録](docs/validation.md)では構造検証、オフライン動作、過去の実行記録と実データ検証を区別します。

## 実行検証を伴うコア改善

今回の対象は Buffett 財務スクリーニング、個別評価、回測と合意判定の接続です。評価履歴を日付順に並べ、過去5年の範囲と TTM 列を厳密に選択。同じ取引日の価格と PE から EPS を推算します。欠損財務データを `partial` と明示し、完全な合意票として扱いません。

回測は調整時点の情報で銘柄を選び、保有後の収益を計算します。退出価格・基準データの不足は停止。実取引日を揃え、初月損失もドローダウンに含め、価格変動後のウェイトで売買額を計算します。毛収益・費用・純収益と保有明細を追跡できます。

**動作テスト35件に合格。2026-10-24 に AKShare 1.19.3 で単一銘柄の取得・評価にも成功しました。** 年報期は2021–2025、評価取引日は2026-10-23です。[記録](examples/verification/2026-10-24/buffett-check.json)と [CSV](examples/verification/2026-10-24/buffett-screen.csv)を確認できます。利益や全 API の保証ではありません。

## まずオフラインで実行

リポジトリ直下で実行します。入力は**合成データ**で、現在の株価ではありません。API key は不要です。

```bash
git clone --branch codex/quant-skills-refresh https://github.com/Serennity007/awesome-stock-quant-skills.git
cd awesome-stock-quant-skills
python -m pip install pandas
python my-skills/master-ensemble/scripts/ensemble.py --csvs examples/ensemble/quality.csv examples/ensemble/momentum.csv --out output/consensus.csv
```

期待される順序と合意スコアは `000003: 83.3`、`000001: 66.7`、`000002: 50.0` です。`consensus.csv.meta.json` に入力ハッシュなどを保存します。データ日付を指定しない場合、`as_of` は null。指定した日付も利用者の申告値であり、自動検証はしません。

実データで A 株を調べる場合：

```bash
python -m pip install akshare pandas numpy
python my-skills/buffett-value-investing/scripts/screen.py --codes 600519,000858,600036 --out output/buffett.csv
```

取得はネットワーク・データ提供元・API 版に依存します。実際の取引日と財務報告期を記録してください。`score_status` / `decision` を先に確認し、`partial` / `needs_data` なら追加データが必要です。全市場 API の再検証は行っていません。

## 費用と保有明細を再現する

```bash
python my-skills/framework-backtest/scripts/backtest.py --cache-dir examples/backtest/cache --results-dir output/backtest-demo --frameworks danbin --start 2026-07-31 --top 1 --min-stocks 2 --cost-bps 10
```

合成価格 `100 → 110 → 99`、初回購入費用10 bps、期末の強制売却なし。純期末資産は **0.98901**、基準は **1.01** です。月次毛・純収益、売買額、保有明細、入力ハッシュを確認できます。これは計算検証であり、過去の運用成績ではありません。[場面説明](examples/backtest/SCENARIO.md)。

## Agent に組み込む

必要な skill だけをコピーします。共通の agents ディレクトリを使う環境の例：

```bash
mkdir -p ~/.agents/skills
cp -r my-skills/quant-research-workflow ~/.agents/skills/
cp -r my-skills/buffett-value-investing ~/.agents/skills/
cp -r my-skills/master-ensemble ~/.agents/skills/
```

Claude Code では `~/.claude/skills/` を使えます。第三者の複数 skill 集合は、内部の `SKILL.md` を含む個別ディレクトリを選んでください。ナビゲーターは他の skill や依存パッケージを自動インストールしません。

依頼例：「quant-research-workflow でこの3社の財務品質を調べ、データ日付、減点項目、定性的な追加調査が必要な点を示してください。」

## 一覧と証拠

- [全オリジナル skill](README.md#原创技能)：価値、成長、防御、テーマ、配分、合成、回測。
- [第三者ソース一覧](README.md#第三方收录)と[権利表記](docs/NOTICE.md)。
- [外部リソース索引](docs/resource-index.md)：star 数は記載日の古い集計です。
- [過去の実行記録](docs/historical-demos.md)：今回再検証した行情や運用成績ではありません。

## 検証と継続更新

```bash
python -m pip install pandas pyyaml
python scripts/validate_repository.py
python -m unittest discover -s tests -v
python scripts/check_upstreams.py
```

最後のコマンドだけ通信が必要です。[ワークフローテンプレート](docs/workflows) は Python 3.11 / 3.13 の検証と週次巡回に対応します。現在の GitHub 認証には `workflow` 権限がなく、新ワークフローは未配置です。適切な権限で `.github/workflows/` にコピーし、既定ブランチへ反映すると有効になります。第三者コードは自動置換しません。旧ミラーのコミットが不明なら `snapshot-unpinned` と記録し、取得失敗時は非ゼロ終了します。

更新基準日：**2026-10-24**。第三者ファイルは過去のスナップショットです。[保守手順](docs/maintenance.md)と[検証範囲](docs/validation.md)を参照してください。

## 利用範囲とライセンス

学習・研究用で、投資助言ではありません。投資家名を冠した手法は公開思想のルール化で、本人の推奨・判断の再現を意味しません。合意スコアは勝率ではありません。現行回測は現在の構成銘柄と報告期末 +120 日の近似を使用し、実際の開示日や過去の訂正を検証していません。厳密な point-in-time や相対順位の正しさは保証できません。

オリジナルと整理内容は [MIT](LICENSE)。第三者作品の著作権・ライセンスは各作者に帰属します。[NOTICE](docs/NOTICE.md)に範囲を記載。MIT / Apache-2.0 / BSD / CC0 のみコピーし、その他はリンク索引とする収録方針です。
