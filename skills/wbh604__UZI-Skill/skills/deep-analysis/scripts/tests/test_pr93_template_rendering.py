"""Safe template behavior retained from the useful part of PR #93."""


def test_missing_numeric_placeholder_renders_question_mark():
    from lib.investor_evaluator import _fmt_msg

    rendered = _fmt_msg("PE {pe_ttm:.0f} · {name}", {"name": "测试公司"})

    assert rendered == "PE ? · 测试公司"
    assert "{" not in rendered


def test_youzi_fstring_escaped_braces_render_normally():
    from lib.investor_criteria import _youzi_base_rules
    from lib.investor_evaluator import _fmt_msg

    rule = next(rule for rule in _youzi_base_rules(need_lhb=True) if rule.rule_id == "lhb_hot")

    assert _fmt_msg(rule.pass_msg, {"lhb_30d_count": 2}) == "30 天上榜 2 次"
