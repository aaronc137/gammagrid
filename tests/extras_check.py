"""morning-bites: app/mb_extras.py 的纯函数检查(不连库、不渲染)。

钉的是会悄悄算错的边界: 1σ 碰墙的两端、跨周末与假期挑「一周前」、理论价对教科书算例、
单个到期日的墙。用法: python tests/extras_check.py
"""

import datetime as dt
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd  # noqa: E402

from app import mb_extras  # noqa: E402


def check_wall_hits():
    move = {"underlying_price": 100.0, "lower": 95.0, "upper": 105.0}
    # 边界含: 墙正好在区间端点上算够得着
    assert mb_extras.wall_hits(move, {"put": 95.0, "call": 105.0}) == [("put", 95.0), ("call", 105.0)]
    # 差一分就够不着
    assert mb_extras.wall_hits(move, {"put": 94.99, "call": 105.01}) == []
    # 墙在现价错误的一侧(Put 墙在上方)不算碰墙
    assert mb_extras.wall_hits(move, {"put": 101.0, "call": 99.0}) == []
    assert mb_extras.wall_hits(move, {}) == []
    print("wall-hit checks passed (both edges inclusive, wrong side ignored)")


def check_preset_day():
    # 新到旧; 10-13 周一是哥伦布日之后的交易日, 中间跨周末
    days = [dt.date(2026, 10, 13), dt.date(2026, 10, 9), dt.date(2026, 10, 8), dt.date(2026, 10, 6),
            dt.date(2026, 10, 2), dt.date(2026, 9, 11)]
    assert mb_extras.preset_day(days, 1) == dt.date(2026, 10, 9)  # 上一个有记录的交易日, 不是日历上的昨天
    assert mb_extras.preset_day(days, 7) == dt.date(2026, 10, 6)  # 第一个距今 ≥ 7 天的
    assert mb_extras.preset_day(days, 30) == dt.date(2026, 9, 11)
    assert mb_extras.preset_day(days[:3], 30) is None  # 历史不够长
    assert mb_extras.preset_day(days[:1], 1) is None
    print("compare-preset checks passed (trading days on record, weekend and short history)")


def check_theoretical_prices():
    # 教科书算例: S=100 K=100 T=1 σ=0.2 r=5% q=0 → Call 10.4506, Put 5.5735
    expiry = pd.Timestamp("2027-06-01")
    collected = expiry - pd.Timedelta(days=365.25)
    history = pd.DataFrame({
        "collected_at": [collected, collected, expiry + pd.Timedelta(days=1)],
        "underlying_price": [100.0, 100.0, 100.0],
        "implied_volatility": [0.2, None, 0.2],
        "last_price": [10.0, 10.0, 0.0],
    })
    assert mb_extras.config.RISK_FREE_RATE == 0.05, "算例按 5% 写的"
    call = mb_extras.theoretical_prices(history, 100.0, expiry, "call")
    put = mb_extras.theoretical_prices(history, 100.0, expiry, "put")
    assert abs(call.iloc[0] - 10.4506) < 0.02, call.iloc[0]
    assert abs(put.iloc[0] - 5.5735) < 0.02, put.iloc[0]
    assert pd.isna(call.iloc[1]) and pd.isna(call.iloc[2])  # 缺 IV、已到期: 不画, 不是 0
    print("theoretical-price checks passed (textbook call/put, missing IV and expired rows are NaN)")


def check_expiry_walls():
    chain = pd.DataFrame({
        "option_type": ["call", "call", "put", "put", "put"],
        "strike": [110.0, 120.0, 90.0, 95.0, 80.0],
        "open_interest": [500, 900, 300, 0, 299],
    })
    assert mb_extras.expiry_walls(chain) == {"call": 120.0, "put": 90.0}
    assert mb_extras.expiry_walls(chain[chain["option_type"] == "call"]) == {"call": 120.0}
    print("expiry-wall checks passed (largest open interest per side, zero-OI ignored)")


if __name__ == "__main__":
    check_wall_hits()
    check_preset_day()
    check_theoretical_prices()
    check_expiry_walls()
    print("\nALL EXTRAS CHECKS PASSED")
