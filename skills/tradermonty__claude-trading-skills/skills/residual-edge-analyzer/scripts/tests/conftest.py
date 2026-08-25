"""Load the residual edge analyzer script as an importable test module."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def analyzer_module():
    script = Path(__file__).resolve().parents[1] / "analyze_residual_edge.py"
    spec = importlib.util.spec_from_file_location("analyze_residual_edge", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
