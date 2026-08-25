"""pipeline.score · Scoring 阶段 · v3.0.0 Phase 6c · 真正接管主干.

### 相比 Phase 6a delegate 的区别

Phase 6a 做法：调 `rrt.stage1(ticker)` → stage1 内部 **重新 collect** 数据 + scoring · pipeline
只是薄包装 · 职责没转移.

Phase 6c 做法：pipeline 已经 collect 完 · 写了 raw_data.json · **只调 rrt 里的纯打分函数**
(score_dimensions / generate_panel / generate_synthesis / _autofill_qualitative_via_mx) ·
rrt.stage1 不再被 pipeline 调用 · pipeline 才是真正的主干.

依赖的 legacy 纯函数（无副作用 · 稳定 API）：
- `rrt.score_dimensions(raw) -> dims_scored`
- `rrt.generate_panel(dims_scored, raw) -> panel`
- `rrt.generate_synthesis(raw, dims_scored, panel, agent_analysis=None) -> synthesis`
- `rrt._autofill_qualitative_via_mx(raw, ticker)` (原地改 raw)

这些函数在 legacy 里也被 stage1 调用 · pipeline 调等价于 stage1 的 scoring 段 · 业务零差别.
"""
from __future__ import annotations

import json
from pathlib import Path


def score_from_cache(ticker: str) -> dict:
    """给定已有 .cache/<ticker>/raw_data.json · 执行 scoring · 落地 dimensions/panel/synthesis.

    流程（纯函数编排 · 不再调 stage1）：
      1. 读 raw_data.json
      2. _autofill_qualitative_via_mx · MX API 补齐定性维度（原地改 raw）
      3. autofill_via_playwright · v2.13 Playwright 兜底（原地改 raw）
      4. score_dimensions · 22 维打分
      5. generate_panel · 51 评委投票
      6. generate_synthesis · DCF/LBO/BCG/Porter
      7. 写 dimensions.json / panel.json / synthesis.json
    返回 {"dimensions": ..., "panel": ..., "synthesis": ...}
    """
    import run_real_test as rrt
    from lib.market_router import parse_ticker

    ti = parse_ticker(ticker)
    cache_dir = Path(rrt.__file__).parent / ".cache" / ti.full
    raw_path = cache_dir / "raw_data.json"
    if not raw_path.exists():
        raise FileNotFoundError(
            f"pipeline.score_from_cache: {raw_path} 不存在 · 必须先跑 pipeline.collect"
        )

    raw = json.loads(raw_path.read_text(encoding="utf-8"))

    # v2.6.1 · MX API 兜底补齐定性维度（原地改 raw · 不 raise）
    try:
        rrt._autofill_qualitative_via_mx(raw, ti.full)
    except Exception as e:
        print(f"   ⚠️ autofill_via_mx 跳过: {type(e).__name__}: {str(e)[:80]}")

    # v2.13 · Playwright 兜底（按 profile 决策 · 默认 lite 不启用）
    try:
        from lib.playwright_fallback import autofill_via_playwright
        autofill_via_playwright(raw, ti.full)
    except Exception as e:
        print(f"   ⚠️ Playwright 兜底跳过: {type(e).__name__}: {str(e)[:80]}")

    # v3.9.4 · 机构建模 dim 20/21/22 —— 与 legacy stage1 保持一致
    # （此前 pipeline 从未计算这三个维度，导致默认路径报告缺整个机构建模章节）
    try:
        from compute_deep_methods import compute_dim_20, compute_dim_21, compute_dim_22
        from lib.stock_features import extract_features
        _features_pre = extract_features(raw, raw.get("dimensions", {}))
        raw["dimensions"]["20_valuation_models"] = compute_dim_20(_features_pre, raw)
        _d20 = raw["dimensions"]["20_valuation_models"]["data"]
        raw["dimensions"]["21_research_workflow"] = compute_dim_21(_features_pre, raw, _d20)
        _d21 = raw["dimensions"]["21_research_workflow"]["data"]
        raw["dimensions"]["22_deep_methods"] = compute_dim_22(_features_pre, raw, _d20, _d21)
    except Exception as e:
        print(f"   ⚠️ 机构建模 dim 20/21/22 计算失败: {type(e).__name__}: {str(e)[:100]}")

    # Always derive the recovery artifact from the final, post-fallback snapshot.
    from lib.data_integrity import refresh_recovery_artifact
    refresh_recovery_artifact(raw, ti.full, cache_dir / "_data_gaps.json")

    # 重新写回 raw_data.json（autofill 已修改 · dim 20-22 已就位）
    raw_path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    # 22 维 scoring
    dims_scored = rrt.score_dimensions(raw)
    (cache_dir / "dimensions.json").write_text(
        json.dumps(dims_scored, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    # 51 评委 panel
    panel = rrt.generate_panel(dims_scored, raw)
    (cache_dir / "panel.json").write_text(
        json.dumps(panel, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    # v3.9.4 · 读 agent_analysis.json（若存在）→ generate_synthesis 合并
    # per_investor_override 等角色扮演成果 → 覆盖后写回 panel.json + synthesis.json
    _aa_path = cache_dir / "agent_analysis.json"
    _agent_analysis = _read_json(_aa_path)
    if _agent_analysis:
        print(f"   🧠 加载 agent_analysis.json · 合并 role-play 成果")

    # Synthesis（合并 agent_analysis · 若存在）
    synthesis = rrt.generate_synthesis(raw, dims_scored, panel, agent_analysis=_agent_analysis)
    (cache_dir / "synthesis.json").write_text(
        json.dumps(synthesis, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    # 覆盖后的 panel（含 per_investor_override 合并）写回 · stage2 重新读 panel.json 也能拿到
    (cache_dir / "panel.json").write_text(
        json.dumps(panel, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    return {
        "dimensions": dims_scored,
        "panel": panel,
        "synthesis": synthesis,
    }


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
