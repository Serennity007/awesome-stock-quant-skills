# 収録スキル実測比較表（skill-review）

**[中文](skill-review.md) | [English](skill-review.en.md) | [日本語](skill-review.ja.md)**

チェック日：2026-08-26。方法：実機（Windows + Python 3.11）での構造化チェック。インストール可能な依存は実際にインストールし、実行可能なものは実際に実行。有料 API キーや証券端末（QMT/IBKR）など外部環境が必要なものは「外部環境が必要、未実測」と正直に記載。テスト結果の捏造はありません。

## チェック表

| スキル | 標準 SKILL.md | スクリプト/依存 | 必要な API キー | 今回の実測 | 一言コメント |
|---|---|---|---|---|---|
| simonlin1212__a-stock-data | ✅（1） | Python スクリプト + baostock/akshare/requests | 不要（baostock/akshare は無料） | ❌ 未実測 | A株データのフルスタック型。構造が規範的で、2つのデータ源が互いのフォールバック。 |
| wbh604__UZI-Skill | ✅（4つのスキル目録） | run.py 一発起動、依存 akshare/yfinance/baostock/ddgs/playwright 等 | 強制なし（Web 検索は ddgs） | ⚠️ 部分実測：依存をインストールし `run.py 600519.SH` が起動、ネットワーク自己診断を通過しデータ収集に進入（21/22 次元キャッシュ有効）したが、ローカルプロキシ環境下でフル実行が 15 分でタイムアウト | 最も包括的な A 株深層分析スキルで工学的完成度が高いが、依存が重くフル実行に時間がかかる。 |
| BitSoulTech__BitSoulStockSkill | ✅（bitsoulstockskill/ サブ目録） | Python スクリーニング/ファクター/バックテスト | 不要（公開データ源） | ❌ 未実測 | スクリーニング+ファクター+バックテスト一体。核心目録を収録、assets は未収録。 |
| fadewalk__serenity-stock-choke | ✅ | scripts/a_stock_query.py | OpenAI 互換キー必須 | ❌ 有料キー必要、未実測 | 「カード首」テーマのスクリーニングで発想が特色あるが、LLM キーに依存。 |
| shouldnotappearcalm__a-share-skill | ✅（5つのサブスキル） | Python スクリプト + akshare/baostock | 不要 | ❌ 未実測 | データ/分析/模擬取引の目録分けが明快で、パイプラインのカバーが完全。 |
| StanleyChanH__Tushare-Finance-Skill | ✅ | Python + tushare | Tushare Pro トークン必須（ポイント制） | ❌ 有料トークン必要、未実測 | Tushare ラッパーとインターフェース文書が充実。トークンが硬性の門。 |
| Geralt-L__Stock-Analysis-3D | ✅ | references/stock_data_fetcher.py、マルチソース（akshare/yfinance/efinance/tushare） | 強制なし（tushare は任意） | ❌ 未実測 | 3 次元スコアリングの枠組みが明快で、データ源の冗長設計が合理的。 |
| atorber__qmt-trading-skill | ✅（22 のサブスキル） | Python + xtquant | 証券会社 QMT 端末必須 | ❌ 外部環境（QMT）必要、未実測 | 21+ の QMT 実弾/データ橋渡しスキル。実弾取引向けだがローカル QMT 必須。 |
| staruhub__a-share-analyst | ✅（Geek-skills サブ目録） | プロンプト中心、references/scripts 付き | 不要 | ❌ 未実測 | アナリストロール型プロンプトスキル。軽量で始めやすい。 |
| tradermonty__claude-trading-skills | ✅（72 の SKILL.md） | 多数の Python スクリプト（yfinance/requests）、多くに tests 付き | 強制なし（米国株無料データ） | ❌ 未実測 | 米国株/CANSLIM/イベント駆動のカバーが最大。テスト同梱で工学規範が良い。 |
| agiprolabs__claude-trading-skills | ✅（67 の SKILL.md） | Python スクリプト | 一部に Birdeye/Helius 等のチェーン上 API キー必要 | ❌ 有料キー必要（一部）、未実測 | 暗号資産/Solana 寄りで、数は多いが A 株とは領域が異なる。 |
| zubair-trabzada__ai-trading-claude | ✅（15） | 純プロンプト（Python スクリプトなし）+ 5 エージェント | 不要 | ➖ 実測不要（実行物なし）、構造チェック済 | プロンプト型取引スキル集。構造が規範的でゼロ依存。 |
| yennanliu__InvestSkill | ✅（27） | プロンプト中心（DCF/決算/競合等） | 一部 OpenAI/Anthropic キー必要 | ❌ 有料キー必要、未実測 | 米国株ファンダメンタルズ分析スキル集。テーマ分けが細かい。 |
| tellmefrankie__ai-investment-skills | ✅（5） | プロンプト + 一部スクリプト | OpenAI/Anthropic キー必須 | ❌ 有料キー必要、未実測 | オプションフロー/ニュースセンチメント/価格アラート等の実用小スキル。 |
| cruisekkk__trading-ledger | ✅ | 純プロンプト/ログテンプレート（demo は Remotion フロントエンドで実行依存ではない） | 不要 | ➖ 実測不要（実行スクリプトなし）、構造チェック済 | 取引日誌スキル。簡潔で実用的、ゼロ依存。 |
| AlexLiu0130__ibkr-options-assistant | ✅ | Python + ib_insync（requirements.txt 完備） | IBKR TWS/Gateway 必須 | ❌ 外部環境（IBKR）必要、未実測 | オプション建玉/集中度/コスト分析スクリプトが完備。IBKR ユーザー向け。 |

## まとめ

- **今回実測で完走**：本リポジトリのオリジナル `buffett-value-investing` と `technical-pattern-recognition` のみ（各 docs/demo 参照）。
- **部分実測**：`wbh604__UZI-Skill`（入口は起動、データ収集が部分的に完了、フル実行はタイムアウト）。
- **ゼロ依存でそのまま使える**（プロンプト型、構造チェック済）：`zubair-trabzada__ai-trading-claude`、`cruisekkk__trading-ledger`。
- **有料キーまたは外部環境が必要で未実測**：Tushare トークン（StanleyChanH）、OpenAI/Anthropic キー（fadewalk、tellmefrankie、yennanliu の一部）、QMT（atorber）、IBKR（AlexLiu0130）、チェーン上 API キー（agiprolabs の一部）。
- **その他**：構造チェックは合格（SKILL.md 規範、依存明確）だが、今回は個別実行していない。

> 注意：「未実測」は品質の問題を意味しません。本実機環境でエンドツーエンド実行が完了しなかったというだけです。原作者や利用者による実測結果の補充（本表を更新する PR）を歓迎します。
