# Localization verification / 本地化验证

Revision: 2026-11-24（上次：2026-10-25）。

- Scope: English-default repository README, preserved Chinese guide, language coverage and bilingual source-release notes; the compatibility `README.en.md` entry and the futures/options Skill additions were checked in this revision.
- Command: `python -X utf8 -m unittest discover -s tests -q`
- Result in this revision: **112 tests passed**.
- Local Markdown targets in the edited root entry guides were checked. Original calculation scripts and frozen evidence were not modified.
- This verifies documentation changes and existing behavior; it does not verify market data authenticity, translation of every research artifact, or investment performance.

本次范围为默认英语入口、保留中文指南、语言范围与双语源码发布说明，并核对兼容入口 `README.en.md` 与新增期货/期权 Skill。上述 112 项测试通过；入口文档的本地链接已检查。未修改计算脚本或冻结证据。这不证明市场数据真实性、全部研究资料已翻译或投资绩效。
