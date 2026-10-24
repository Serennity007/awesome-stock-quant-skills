# Awesome Stock Quant Skills

**株式リサーチの問いを、実行・検証できるワークフローへ。**

[中文](README.md) · [English](README.en.md) · [日本語](README.ja.md)


<!-- inventory: originals=30 mirrors=16 vendored=225 -->

**オリジナル skill 30 件 · 第三者ソースのスナップショット 16 件 · 収録 SKILL.md 225 ファイル · 中英日ドキュメント**

A 株の企業品質・割安度・成長・モメンタム・テーマ・指数配分と、米国の注目銘柄追跡を扱う Agent Skills ツールボックスです。Python スクリプトを直接実行するほか、対応する AI アシスタントから利用できます。

**手法の選択 → データ取得 → 項目別評価 → 複数手法の比較 → 過去の検証**を、入力・ルール・制約までたどれる形で進めます。

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

## まずオフラインで実行

リポジトリ直下で実行します。入力は**合成データ**で、現在の株価ではありません。API key は不要です。

```bash
git clone https://github.com/Serennity007/awesome-stock-quant-skills.git
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

取得はネットワーク・データ提供元・API 版に依存します。実際の取引日と財務報告期を記録してください。今回の更新では全市場 API の再検証は行っていません。

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
