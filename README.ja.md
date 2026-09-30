# awesome-stock-quant-skills

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

![GitHub stars](https://img.shields.io/github/stars/Serennity007/awesome-stock-quant-skills?style=flat-square) ![License](https://img.shields.io/github/license/Serennity007/awesome-stock-quant-skills?style=flat-square) ![収録スキル](https://img.shields.io/badge/収録スキル-16-blue?style=flat-square) ![オリジナルスキル](https://img.shields.io/badge/オリジナルスキル-29-green?style=flat-square) ![言語](https://img.shields.io/badge/言語-中文%20%7C%20EN%20%7C%20JA-orange?style=flat-square)

株式トレード / クオンツトレード / 銘柄スクリーニング AI Skill コレクション：国内外の GitHub から株式分析・クオンツトレード・スクリーニング戦略の Agent Skills（Claude Code / Agent Skills 形式）を収録し、インデックスとライセンス遵守の転載を付記。

- **コンプライアンス原則**：`skills/` ディレクトリには MIT / Apache-2.0 / BSD / CC0 ライセンスのプロジェクトのみを収録し、元の LICENSE ファイルと SOURCE.md の出典情報を保持します。ライセンスなし・GPL・AGPL・NOASSERTION のプロジェクトはインデックスのみで、ファイルはコピーしません。
- 収録日：2026-08-25。

## 免責事項

本リポジトリの内容は学習・研究目的のみを対象とし、投資助言を構成するものではありません。市場にはリスクが伴います。投資は慎重に行ってください。すべてのスキルの著作権は原作者および元リポジトリに帰属します。削除をご希望の場合はご連絡ください。

## 使い方

`skills/` から必要なスキルディレクトリを自分のスキルディレクトリにコピーするだけです：

```bash
# Claude Code
cp -r skills/<作者>__<スキル名> ~/.claude/skills/

# または汎用 agents skills ディレクトリ
cp -r skills/<作者>__<スキル名> ~/.agents/skills/
```

複数スキルのコレクション（例：`agiprolabs__claude-trading-skills/skills/...`）の場合は、内部の具体的なスキルサブディレクトリをコピーしてください。各収録ディレクトリの `SOURCE.md` に元リポジトリの URL・作者・ライセンスが記録されています。

## 収録済みスキル

| ディレクトリ | 概要 | 出典 | License |
|---|---|---|---|
| [simonlin1212__a-stock-data](skills/simonlin1212__a-stock-data) | A株フルスタックデータ SKILL | [simonlin1212/a-stock-data](https://github.com/simonlin1212/a-stock-data) | Apache-2.0 |
| [wbh604__UZI-Skill](skills/wbh604__UZI-Skill) | 遊資UZIトレードスキル（深層分析／龍虎榜／罠検出など） | [wbh604/UZI-Skill](https://github.com/wbh604/UZI-Skill) | MIT |
| [BitSoulTech__BitSoulStockSkill](skills/BitSoulTech__BitSoulStockSkill) | A株スクリーニング＋ファクター＋バックテスト（コア部分のみ、assets は未収録） | [BitSoulTech/BitSoulStockSkill](https://github.com/BitSoulTech/BitSoulStockSkill) | Apache-2.0 |
| [fadewalk__serenity-stock-choke](skills/fadewalk__serenity-stock-choke) | A株「チョークポイント」スクリーニング | [fadewalk/serenity-stock-choke](https://github.com/fadewalk/serenity-stock-choke) | MIT |
| [shouldnotappearcalm__a-share-skill](skills/shouldnotappearcalm__a-share-skill) | A株分析＋スクリーニング＋模擬取引（複数スキルのサブディレクトリ） | [shouldnotappearcalm/a-share-skill](https://github.com/shouldnotappearcalm/a-share-skill) | MIT |
| [StanleyChanH__Tushare-Finance-Skill](skills/StanleyChanH__Tushare-Finance-Skill) | Tushare データスキルパック | [StanleyChanH/Tushare-Finance-Skill-for-Claude-Code](https://github.com/StanleyChanH/Tushare-Finance-Skill-for-Claude-Code) | MIT |
| [Geralt-L__Stock-Analysis-3D](skills/Geralt-L__Stock-Analysis-3D) | 3D スコア株式分析 | [Geralt-L/Stock-Analysis-3D](https://github.com/Geralt-L/Stock-Analysis-3D) | MIT |
| [atorber__qmt-trading-skill](skills/atorber__qmt-trading-skill) | QMT トレード 21 スキル | [atorber/qmt-trading-skill](https://github.com/atorber/qmt-trading-skill) | MIT |
| [staruhub__a-share-analyst](skills/staruhub__a-share-analyst) | A株アナリストスキル（ClaudeSkills より） | [staruhub/ClaudeSkills](https://github.com/staruhub/ClaudeSkills) | MIT |
| [tradermonty__claude-trading-skills](skills/tradermonty__claude-trading-skills) | 米国株分析 / CANSLIM スクリーニングなど | [tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills) | MIT |
| [agiprolabs__claude-trading-skills](skills/agiprolabs__claude-trading-skills) | 67 のトレードスキル（暗号資産／オプション／リスク管理） | [agiprolabs/claude-trading-skills](https://github.com/agiprolabs/claude-trading-skills) | MIT |
| [zubair-trabzada__ai-trading-claude](skills/zubair-trabzada__ai-trading-claude) | 16 の trade-* スキル ＋ 5 エージェント | [zubair-trabzada/ai-trading-claude](https://github.com/zubair-trabzada/ai-trading-claude) | MIT |
| [yennanliu__InvestSkill](skills/yennanliu__InvestSkill) | 米国株分析 ＋ stock-screener など | [yennanliu/InvestSkill](https://github.com/yennanliu/InvestSkill) | MIT |
| [tellmefrankie__ai-investment-skills](skills/tellmefrankie__ai-investment-skills) | オプションフロー／ニュースセンチメント／価格アラートなど 5 つの投資スキル | [tellmefrankie/ai-investment-skills](https://github.com/tellmefrankie/ai-investment-skills) | MIT |
| [cruisekkk__trading-ledger](skills/cruisekkk__trading-ledger) | 取引日誌スキル | [cruisekkk/trading-ledger](https://github.com/cruisekkk/trading-ledger) | MIT |
| [AlexLiu0130__ibkr-options-assistant](skills/AlexLiu0130__ibkr-options-assistant) | IBKR オプションアシスタント | [AlexLiu0130/ibkr-options-assistant](https://github.com/AlexLiu0130/ibkr-options-assistant) | MIT |

## オリジナルスキル

本リポジトリ作者（Serennity007）のオリジナルスキル。収録区の `skills/` と区別するため `my-skills/` に配置：

### 投資マスター方法論シリーズ

| ディレクトリ | 概要 | License |
|---|---|---|
| [buffett-value-investing](my-skills/buffett-value-investing) | A株バフェット式バリュー投資分析：堀評価、5年連続 ROE／粗利率／負債比率／営業キャッシュフローのスクリーニング、安全マージン評価（akshare ベース、スクリーニングと個別株分析スクリプト付き） | MIT |
| [munger-quality-investing](my-skills/munger-quality-investing) | A株マンガー式クオリティ投資：5年連続ROIC/ROE、低負債、高く安定した粗利率、収益の質、希薄化の少なさで5次元品質スコアリング | MIT |
| [lynch-garp-investing](my-skills/lynch-garp-investing) | A株ピーター・リンチGARP/テンバガー選別：PEG、連続利益成長、低負債率、リンチ6分類タグ | MIT |
| [graham-defensive-investing](my-skills/graham-defensive-investing) | A株グラハム防御型投資スクリーナー：規模、流動比率、継続的収益、継続的配当、収益成長、低PER/PBRの定量選別 | MIT |
| [dalio-all-weather](my-skills/dalio-all-weather) | A株レイ・ダリオ式オールウェザー／債務サイクル参照配分：幅基指数、国債ETF、金ETF、商品指数から相関・ボラティリティ・リスクパリティ風ウェイトを算出し、年率リターン・最大ドローダウン・シャープレシオでバックテスト | MIT |
| [howard-marks-cycle](my-skills/howard-marks-cycle) | A株ハワード・マークスサイクル温度計：滬深300/中证全指のバリュエーション分位、株式・債券収益差、出来高熱度、信用取引残高トレンドから0-100のサイクル位置スコアと行動フレームワークを出力 | MIT |
| [soros-reflexivity](my-skills/soros-reflexivity) | A株ソロス反身性／マクロ投機スキャナー：価格モメンタムとファンダメンタルの乖離から正のフィードバック／負のフィードバック段階と転換点候補をマーク | MIT |
| [druckenmiller-macro-flex](my-skills/druckenmiller-macro-flex) | ドラッケンミラー式マクロ・フレックス・ダッシュボード：USD/CNY、中米10年国債利回り、金、原油、銅、A株指数と個別銘柄のN日トレンド/モメンタムを追跡し、多空バイアス・スナップショットを出力 | MIT |
| [livermore-trend-trading](my-skills/livermore-trend-trading) | A株ジェシー・リバモア流トレンド投機：N日高値の軸となるポイントブレイクアウト、出来高確認、縮量押し目の2次エントリー、一日反転/出来高伴う行き詰まり危険シグナルを識別し、シグナル表とピラミッド建玉試行フレームワークを出力 | MIT |
| [simons-factor-quant](my-skills/simons-factor-quant) | A株シモンズ式マルチファクター採点器：モメンタム/逆張り/ボラティリティ/出来高/移動平均乖離の5次元で総合スコアを合成 | MIT |
| [klarman-margin-safety](my-skills/klarman-margin-safety) | A株クラーマン流安全マージン・ディープバリュー選別：PB/PE歴史分位、時価総額/ネットキャッシュ比、52週高値からの下落幅、ST・赤字株を除外 | MIT |
| [templeton-global-contrarian](my-skills/templeton-global-contrarian) | A株テンプルトン流最悲観逆張りスキャナー：52週位置、PE/PBの自己歴史低位、出来高縮小からの安定、黒字維持で逆張り監視リストを出力 | MIT |
| [fisher-growth-15](my-skills/fisher-growth-15) | A株フィリップ・フィッシャー成長株15のポイントの機械化：売上CAGR、研究開発比率、利益率トレンド、持続ROE、キャッシュの質、財務健全性の6次元スコアリング、「スカトルバット」調査の候補絞り込み | MIT |
| [neff-low-pe-total-return](my-skills/neff-low-pe-total-return) | A株ジョン・ネフ低PER投資法：全市場中央値比PER割引、(成長率+配当利回り)/PER≥2の総リターン比率、スパン年間化配当利回り、ファンダメンタル下限の7次元スコアリング | MIT |
| [bogle-index-investing](my-skills/bogle-index-investing) | A株ジョン・ボーグル・インデックス投資法：幅基指数PE/PB直近10年分位バリュエーション温度計、ボーグル式期待リターン3分解（配当利回り+利益成長+バリュエーション回帰）、積立ペース目安、月積立vs一括投資バックテスト | MIT |
| [oneil-canslim](my-skills/oneil-canslim) | A株ウィリアム・オニールCANSLIM7要素スコアリング：C四半期利益YoY≥25%、A年間成長、N250日高値接近、S出来高、L沪深300比超過強度、I機関保有、M市場50日移動平均——アルファベット別合否表+プール内RPSパーセンタイル | MIT |

### 中国投資偉人シリーズ

| ディレクトリ | 概要 | License |
|---|---|---|
| [duan-yongping-business-first](my-skills/duan-yongping-business-first) | A株段永平「ビジネスモデル第一」6次元スコアリング：粗利率の安定性、連続ROE、営業CF/純利益、低負債、収益安定性、業界内リーダー順位（「敢為天下後」で良いビジネスを発見） | MIT |
| [zhang-lei-longterm](my-skills/zhang-lei-longterm) | A株張磊・高瓴の長期構造価値投資：連続増収増益、長期投資（R&D/設備投資）、業界成長余地、ROEトレンドの4次元成長質レーダー、「時間の友」スクリーナー | MIT |
| [qiu-guolu-simple-rules](my-skills/qiu-guolu-simple-rules) | A株邱国鷺「投資で最も単純なこと」三好スコアラー：良い業種（月を数え星を数えず）、良い企業（リーダー+高ROE）、良い価格（PE/PB歴史分位） | MIT |
| [feng-liu-weak-side](my-skills/feng-liu-weak-side) | A株馮柳「弱者体系」逆張りスキャナー：52週下落幅、PE/PB3年歴史分位、崩れぬファンダメンタルズ（黒字+売上未失速）、低関心度——オッズ/確率ウォッチリスト | MIT |
| [lin-yuan-monopoly-consumer](my-skills/lin-yuan-monopoly-consumer) | A株林園式独占+依存性消費投資：口元関連必需品リーダー、粗利率≥50%、ROE≥15%、高配当、申万消費/医薬業種フィルタによる多次元スコアリング | MIT |
| [dan-bin-rose-of-time](my-skills/dan-bin-rose-of-time) | A株但斌「時間の薔薇」偉大な企業投資法：長い坂（売上CAGR）、深い雪（粗利率の価格決定力）、複利エンジン（連続ROE）、時間の薔薇（会計年度精度の配当年間化）、キャッシュの質、財務健全性、成長の質の7次元スコアリング | MIT |
| [li-lu-value-compounding](my-skills/li-lu-value-compounding) | A株李録バリュー複利投資法：持続的高ROE、複利トレンド（直近2年vs前3年）、再投資成長、キャッシュの質、PE/PB歴史低分位の安全マージン、低負債の6次元スコアリング | MIT |

### ホットテーマシリーズ

| ディレクトリ | 概要 | License |
|---|---|---|
| [hot-theme-scanner](my-skills/hot-theme-scanner) | A株ホットテーマスキャナー：akshareのコンセプト板・資金フローAPIを使い、N日間の人気テーマを特定し、上昇先導株をリストアップして構造化ヒート表を出力 | MIT |
| [us-hot-stocks-tracker](my-skills/us-hot-stocks-tracker) | 米国人気AI株トラッカー：AIコンピュート/ストレージ/AIアプリ/robotaxiテーマのウォッチリストを内蔵し、現在値、騰落率、20/60日モメンタム、52週高安値距離、出来高異常を出力 | MIT |
| [concept-stock-mapper](my-skills/concept-stock-mapper) | A株テーマキーワード→概念股マッパー：akshareの概念セクターインターフェースであいまい一致し、構成銘柄を取得して騰落率/回転率/主力資金で並べ替え、複数キーワードの題材強度比較に対応 | MIT |

### クロスフレームワークツール

| ディレクトリ | 概要 | License |
|---|---|---|
| [master-ensemble](my-skills/master-ensemble) | マスター合意スクリーナー：複数のマスタースキルのスコア結果CSVをフレームワーク内パーセンタイルで正規化し、合意スコア+トップヒット数を合成、「複数の独立した手法が同時に指す」クロスフレームワーク交差銘柄を出力（純ローカル合成、数秒で完了） | MIT |
| [framework-backtest](my-skills/framework-backtest) | マスター框架バックテスト検証器：各マスタースキルの採点框架をA株で月次リバランスし検証（等上位N銘柄 vs 滬深300）、時点正確（point-in-time）、未来関数なし、年率/超過/最大DD/シャープと逐年対照表を出力 | MIT |

### 既存

| ディレクトリ | 概要 | License |
|---|---|---|
| [technical-pattern-recognition](my-skills/technical-pattern-recognition) | A株テクニカルパターン認識：移動平均線のパーフェクトオーダー/逆オーダー、MACD ゴールデン/デッドクロス、出来高を伴う N 日高値ブレイク、出来高減少の押し目、シグナル表を出力（akshare 新浪日足ベース） | MIT |

## デモ

オリジナルスキルは実際に実行可能なコードで、多くは実走の出力を添付（2026-09-30 実測、akshare 1.18.96、当日の実際の相場・財務データ）：

- **バフェットスクリーニング実測**：`screen.py --codes 600519,000858,600036` → 貴州茅台 100 点（5年連続 ROE 27.7%–37.0%、粗利率 91.7%、PE/PB パーセンタイル 0.07/0.03）、五糧液 94 点、招商銀行 47 点（金融業の高レバレッジが正しく減点）。完全な出力：[my-skills/buffett-value-investing/docs/demo.ja.md](my-skills/buffett-value-investing/docs/demo.ja.md)
- **個別株分析実測**：`analyze.py 600519` → 堀チェックリスト + 5年財務トレンド + バリュエーションレンジ（保守的評価 1547.89 元 / 安全マージン参考値 1083.52 元）。
- **パターン認識実測**：`patterns.py` 6 銘柄 → 601318/000001 が `MACD_GOLDEN`、他は `NO_SIGNAL`。完全な出力：[my-skills/technical-pattern-recognition/docs/demo.ja.md](my-skills/technical-pattern-recognition/docs/demo.ja.md)
- **日次自動レポート**：GitHub Action が毎日 UTC 01:00 に 20 銘柄の A 株代表株でバフェットスクリーニングを自動実行し、結果を [`reports/`](reports/) にコミット（最新：[reports/latest.md](reports/latest.md)）。
- **段永平全プール実測**（2026-09-26）：`screen.py --pool hs300`（300銘柄）→ 山西汾酒 86 点、邁瑞医療 83 点、貴州茅台 82 点、五糧液 81 点、中国海洋石油 81 点が上位——高粗利率キャッシュカウ業種が全体をリード。
- **フィッシャー/ネフ小規模実測**（2026-09-26）：フィッシャー框架では邁瑞医療 78 点、海康威視 76 点が上位（R&D重視の成長株）、茅台は低R&Dで減点；ネフ框架では招商銀行 88 点（PER は市場中央値の 0.18 倍、配当利回り 6.34%、総リターン比率 2.33 でゴールデンライン通過）。
- **但斌/李録/オニール小規模実測**（2026-09-28）：但斌框架では貴州茅台 88 点（粗利率 91.9%、ROE 32.9%、会計年度精度の配当利回り 4.18%）、五糧液 79 点；李録框架では茅台 88 点（PB は5年歴史の 1.9% 分位、安全マージン満点）；オニール CANSLIM では海康威視が [C,N,L] 成立（四半期YoY 39.6%）、茅台の低スコアはまさにモメンタム框架とバリュー框架の相補性。
- **ボーグル温度計実測**（2026-09-28）：滬深300 PER 12.59（10年分位 60%）、上証50 PER 10.64（58%）、中証500 は 78% 分位（積立半減）；直近5年の月積立滬深300 年率 1.81% vs 一括投資 -1.79%。
- **但斌/李録/オニール滬深300全量実測**（2026-09-28、各300/300成功）：但斌框架では山西汾酒 97 点、瀘州老窖 91 点、貴州茅台 88 点が上位（高粗利率白酒が覇権＝「深い雪」の直感どおり）；李録框架では東鵬飲料 94 点、億聯網絡 92 点、新和成 91 点；CANSLIM では瑞芯微 79 点 [C,A,N,L]、薬明康徳 77 点 [C,A,N,L,I]（当日は市場が50日移動平均下で M=0、全プール減点＝オニール規律の実践形）。結果は各スキルの `*_hs300_result.csv`。
- **マスター合意実測**（2026-09-28）：クロスフレームワークスクリーナー `master-ensemble` を公開——億聯網絡 96.4（3フレームワーク全てで上位10%）、薬明康徳 95.9、新易盛 92.0、中際旭創 91.9 が上位；通信設備セクターがバリューとモメンタムの両框架に支持される（AIコンピュート業績実現の典型形）。[my-skills/master-ensemble/consensus_hs300_demo.csv](my-skills/master-ensemble/consensus_hs300_demo.csv) 参照。
- **収録スキルの実測比較**：16 の収録スキルの構造化チェック表（SKILL.md 規範性、依存、API キー、実測可否）は [docs/skill-review.ja.md](docs/skill-review.ja.md) を参照。

## インデックス

以下のプロジェクトはリンクのインデックスのみで、ファイルは転載していません（ライセンス上転載不可、サイズ過大、または完全なアプリ／フレームワークのため）。Stars は 2026-08-25 時点のデータです。

### A. 中国語 Skill / Agent プロジェクト

| プロジェクト | 概要 | Stars | License | 備考 |
|---|---|---|---|---|
| [ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis) | LLM 駆動マルチマーケット分析システム | 63.8k | MIT | 完全なアプリ。元リポジトリ利用推奨。インデックスのみ未転載 |
| [jwangkun/claude-for-financial-services-cn](https://github.com/jwangkun/claude-for-financial-services-cn) | 63 の A株金融 Claude Skills | 720 | Apache-2.0 | サイズ大。インデックスのみ未転載 |
| [liangdabiao/Claude-Code-Stock-Deep-Research-Agent](https://github.com/liangdabiao/Claude-Code-Stock-Deep-Research-Agent) | 8段階デューデリジェンス＋28並列リサーチエージェント | 367 | ライセンスなし | インデックスのみ、未転載 |
| [MobiusQuant/Gendangzou-skill](https://github.com/MobiusQuant/Gendangzou-skill) | 跟庄走：A株セクター研究スキル | 306 | Apache-2.0 | インデックスのみ未転載 |
| [lzwme/finance-quant-skills](https://github.com/lzwme/finance-quant-skills) | A株クオンツ Agent Skills メンテナンスリポジトリ | 264 | ライセンスなし | インデックスのみ、未転載 |
| [joutaojian/arkvol-skill](https://github.com/joutaojian/arkvol-skill) | arkvol データ連携エージェント | 169 | ライセンスなし | インデックスのみ、未転載 |
| [liusai0820/Stock-Analysis-Skill](https://github.com/liusai0820/Stock-Analysis-Skill) | 株式アナリストスキル（A/香港/米国） | 130 | ライセンスなし | インデックスのみ、未転載 |
| [shouldnotappearcalm/hk-us-market-skill](https://github.com/shouldnotappearcalm/hk-us-market-skill) | 香港・米国株クオンツ研究＋模擬取引 | 3 | ライセンスなし | インデックスのみ、未転載 |
| [Patrickristal/DaA-left-side-trading-rookie](https://github.com/Patrickristal/DaA-left-side-trading-rookie) | A株・香港株 左側取引スキル（スーパーフォーキャスティング枠組み） | 2 | ライセンスなし | インデックスのみ、未転載 |
| [quantskills/skill-stock-screener](https://github.com/quantskills/skill-stock-screener) | 自然言語 A株スクリーニング | 2 | GPL-3.0 | GPL は転載不可、インデックスのみ |
| [samyakjain0606/awesome-stock-skills](https://github.com/samyakjain0606/awesome-stock-skills) | インド株式市場リサーチスキル | 24 | ライセンスなし | インデックスのみ、未転載 |
| [rigneshroot/hyperbot-ai-trading-claude-skill](https://github.com/rigneshroot/hyperbot-ai-trading-claude-skill) | 説明可能なトレードインテリジェンス枠組み | 0 | NOASSERTION | インデックスのみ、未転載 |
| [hsliuping/TradingAgents-CN](https://github.com/hsliuping/TradingAgents-CN) | 中国語マルチエージェント LLM トレードフレームワーク | 31.4k | NOASSERTION | インデックスのみ、未転載 |
| [24mlight/A_Share_investment_Agent](https://github.com/24mlight/A_Share_investment_Agent) | A株投資マルチエージェントシステム | 2.5k | NOASSERTION | インデックスのみ、未転載 |
| [HiThink-Tech/Financial-API](https://github.com/HiThink-Tech/Financial-API) | 同花順公式金融データ MCP/API | 1.8k | MIT | インデックスのみ未転載 |
| [wolfjkd/tradex-hub](https://github.com/wolfjkd/tradex-hub) | A株 AI 意思決定ハブ、129 の MCP ツール（通達信＋akshare＋同花順） | 32 | ライセンスなし | インデックスのみ、未転載 |
| [guangxiangdebizi/FinanceMCP-DCTHS](https://github.com/guangxiangdebizi/FinanceMCP-DCTHS) | 東方財富＋同花順 MCP データサービス | 39 | Apache-2.0 | インデックスのみ未転載 |
| [zhuyifang/tonghuasun-codex](https://github.com/zhuyifang/tonghuasun-codex) | ローカル同花順の Codex 連携 | 27 | ライセンスなし | インデックスのみ、未転載 |
| [binance/binance-skills-hub](https://github.com/binance/binance-skills-hub) | Binance 公式スキルマーケット | 982 | 未表記 | インデックスのみ、未転載 |

### B. AI Agent / LLM トレードフレームワーク

| プロジェクト | 概要 | Stars | License | 備考 |
|---|---|---|---|---|
| [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) | マルチエージェント LLM 金融トレードフレームワーク | 100k | Apache-2.0 | フレームワーク、インデックスのみ |
| [virattt/ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) | AI ヘッジファンド マルチエージェントシミュレーション | 63k | MIT | フレームワーク、インデックスのみ |
| [AI4Finance-Foundation/FinRL](https://github.com/AI4Finance-Foundation/FinRL) | 金融強化学習フレームワーク | 16.1k | MIT | フレームワーク、インデックスのみ |
| [AI4Finance-Foundation/FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) | LLM 金融 AI エージェントプラットフォーム | 7.9k | Apache-2.0 | フレームワーク、インデックスのみ |

### C. クオンツフレームワーク / バックテスト

| プロジェクト | 概要 | Stars | License | 備考 |
|---|---|---|---|---|
| [vnpy/vnpy](https://github.com/vnpy/vnpy) | 中国で最も有名なオープンソースクオンツ取引プラットフォーム | 44.7k | MIT | フレームワーク、インデックスのみ |
| [microsoft/qlib](https://github.com/microsoft/qlib) | Microsoft AI クオンツ投資研究プラットフォーム | 47.9k | MIT | フレームワーク、インデックスのみ |
| [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade) | 暗号資産取引ボット | 53.6k | GPL-3.0 | GPL は転載不可、インデックスのみ |
| [mementum/backtrader](https://github.com/mementum/backtrader) | 古典的バックテストライブラリ（開発終了） | 23k | GPL-3.0 | GPL は転載不可、インデックスのみ |
| [quantopian/zipline](https://github.com/quantopian/zipline) | 古典的アルゴ取引バックテストライブラリ | 20.1k | Apache-2.0 | インデックスのみ |
| [QuantConnect/Lean](https://github.com/QuantConnect/Lean) | アルゴ取引エンジン | 21.3k | Apache-2.0 | インデックスのみ |
| [polakowo/vectorbt](https://github.com/polakowo/vectorbt) | ベクトル化バックテスト | 8.8k | Apache-2.0 + Commons Clause | インデックスのみ、未転載 |
| [hummingbot/hummingbot](https://github.com/hummingbot/hummingbot) | 高頻度マーケットメイク／アービトラージ | 19.6k | Apache-2.0 | インデックスのみ |
| [jesse-ai/jesse](https://github.com/jesse-ai/jesse) | 暗号資産取引ボット | 8.4k | MIT | インデックスのみ |
| [ricequant/rqalpha](https://github.com/ricequant/rqalpha) | 米筐 A株バックテストフレームワーク | 6.7k | NOASSERTION | インデックスのみ、未転載 |
| [zvtvz/zvt](https://github.com/zvtvz/zvt) | モジュラークオンツフレームワーク | 4.3k | MIT | インデックスのみ |

### D. データインターフェース

| プロジェクト | 概要 | Stars | License | 備考 |
|---|---|---|---|---|
| [akfamily/akshare](https://github.com/akfamily/akshare) | A株データの定番オープンソースライブラリ | 22.2k | MIT | インデックスのみ |
| [waditu/tushare](https://github.com/waditu/tushare) | 老舗 A株データ（無料版は更新停止、Pro はポイント制） | 15.2k | BSD-3-Clause | インデックスのみ |
| [Micro-sheep/efinance](https://github.com/Micro-sheep/efinance) | 東方財富データの高速取得 | 4k | MIT | インデックスのみ |
| [shidenggui/easyquotation](https://github.com/shidenggui/easyquotation) | 新浪/騰訊 リアルタイム相場 | 5.4k | MIT | インデックスのみ |
| [rainx/pytdx](https://github.com/rainx/pytdx) | 通達信相場インターフェース | 1.6k | ライセンスなし・アーカイブ済み | インデックスのみ、未転載 |
| [ccxt/ccxt](https://github.com/ccxt/ccxt) | 100+ 取引所の統一 API | 43.7k | MIT | インデックスのみ |
| [OpenBB-finance/OpenBB](https://github.com/OpenBB-finance/OpenBB) | オープン金融データプラットフォーム | 72.3k | AGPL-3.0 | AGPL は転載不可、インデックスのみ |

### E. ファクター / 戦略 / 指標

| プロジェクト | 概要 | Stars | License | 備考 |
|---|---|---|---|---|
| [mpquant/MyTT](https://github.com/mpquant/MyTT) | 通達信/同花順指標の Python 移植 | 2.8k | ライセンスなし | インデックスのみ、未転載 |
| [yli188/WorldQuant_alpha101_code](https://github.com/yli188/WorldQuant_alpha101_code) | WorldQuant 101 Alpha ファクター実装 | 860 | ライセンスなし | インデックスのみ、未転載 |

### F. 学習リソース / インデックス

| プロジェクト | 概要 | Stars | License | 備考 |
|---|---|---|---|---|
| [wilsonfreitas/awesome-quant](https://github.com/wilsonfreitas/awesome-quant) | クオンツライブラリ精選リスト | 29.2k | ライセンスなし | インデックスのみ、未転載 |
| [thuquant/awesome-quant](https://github.com/thuquant/awesome-quant) | 中国クオンツリソースインデックス | 5.6k | MIT | インデックスのみ |
| [Barca0412/Introduction-to-Quantitative-Finance](https://github.com/Barca0412/Introduction-to-Quantitative-Finance) | 中国語クオンツ金融入門ナレッジベース | 1.7k | MIT | インデックスのみ |
| [VoltAgent/awesome-claude-skills](https://github.com/VoltAgent/awesome-claude-skills) | Web3/Trading セクションあり | — | — | インデックスのみ |
| [shishirui/awesome-claude-skills-zh](https://github.com/shishirui/awesome-claude-skills-zh) | 中国語スキルインデックス | 15 | CC0-1.0 | インデックスのみ |
| [yzfly/awesome-skills-zh](https://github.com/yzfly/awesome-skills-zh) | 中国語スキルインデックス | 29 | Apache-2.0 | インデックスのみ |

## License

本コレクション自体の整理コンテンツ（README、インデックス、SOURCE.md）は [MIT License](LICENSE) を適用します。`skills/` 配下の各スキルはそれぞれの元リポジトリのライセンスに従います。詳細は各ディレクトリ内の LICENSE と SOURCE.md を参照してください。
