"""
formulaicAlphas — WorldQuant《101 Formulaic Alphas》实现包

快速入门：

    from formulaicAlphas import AlphaDataLoader, Alpha101

    # 1. 加载面板数据
    loader = AlphaDataLoader()
    data = loader.load(
        codes=['000001.SZ', '600519.SH', '000858.SZ'],
        start_date='2025-01-01',
        end_date='2026-03-14',
    )

    # 2. 计算 alpha 因子
    a = Alpha101(data)

    alpha1  = a.alpha001()   # DataFrame：行=日期，列=股票代码
    alpha50 = a.alpha050()

    # 3. 取最新一日横截面排名（越大越看多）
    latest = alpha1.iloc[-1].dropna().sort_values(ascending=False)
    print(latest.head(10))

    # 4. 批量计算指定 alpha
    results = a.compute_all(alphas=[1, 5, 12, 41, 101])
    for name, df in results.items():
        print(name, df.iloc[-1].describe())
"""

from .data_loader import AlphaDataLoader
from .alpha101 import Alpha101, ALPHA_DESCRIPTIONS
from . import operators

__all__ = ["AlphaDataLoader", "Alpha101", "ALPHA_DESCRIPTIONS", "operators"]
