# awesome-stock-quant-skills

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

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

| ディレクトリ | 概要 | License |
|---|---|---|
| [buffett-value-investing](my-skills/buffett-value-investing) | A株バフェット式バリュー投資分析：堀評価、5年連続 ROE／粗利率／負債比率／フリーキャッシュフローのスクリーニング、安全マージン評価（akshare ベース、スクリーニングと個別株分析スクリプト付き） | MIT |

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
