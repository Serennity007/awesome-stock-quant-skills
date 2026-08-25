"""Load the optional statistical dependency with an actionable error."""

from __future__ import annotations

INSTALL_COMMAND = "uv run --with 'statsmodels>=0.14,<0.15' python"


def require_statsmodels():
    """Return the statsmodels tools used by the pair-trading scripts."""
    try:
        from statsmodels.tsa.ar_model import AutoReg
        from statsmodels.tsa.stattools import adfuller
    except ImportError as exc:
        raise RuntimeError(
            "statsmodels>=0.14,<0.15 is required for cointegration analysis. "
            f"Run the command with: {INSTALL_COMMAND} <script> [arguments]"
        ) from exc
    return AutoReg, adfuller
