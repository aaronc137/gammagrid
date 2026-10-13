"""morning-bites: 托管版有、开源版没有的几样行情功能, 本地补上(10-12 对照 app.gammagrid.io)。

都只用库里已有的快照, 不发任何网络请求; 文案中英两套, 按 app.zh.lang() 取
(不进 zh_text 的对照表 —— 这是本站自己的内容, 不是上游英文的译文)。
挂在 dashboard.py 的几行 `mb_extras.xxx(...)` 上, 上游文件其余不动, 合并上游少冲突。

  since_strip      天气卡片下一行: 今天第一班到现在, 翻转位 / 净 GEX / 天气怎么变了
  max_pain_extras  最大痛点建立在多少有持仓的合约上; 该到期日的预期波动与 1σ 碰墙警示
  compare_presets  「变化」视图的 1 天 / 1 周 / 1 月 快捷对比
  price_chart      合约价格图加一条 Black-Scholes 理论价; 希腊值单位说明
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import streamlit as st

from app import config, market_calendar, metrics, weather, zh
from app.metrics_core import _bs_price, years_to_expiry_by_moment
from app.viewtime import timezone_label, to_viewer


def _t(english: str, chinese: str) -> str:
    return zh._tidy(chinese) if zh.lang() == "zh" else english


def _weather_word(state: str) -> str:
    label = weather.WEATHER_WORDS.get(state, (state, ""))[0]
    return zh.tr(label)


# --- A2 日内变化条 ---------------------------------------------------------------


def since_strip(conn, ticker: str, source: str | None, latest_df: pd.DataFrame, latest_reading, with_iv) -> None:
    """今天第一班 → 最新一班, 只在当天有两班以上时画。共享标的(SPY/QQQ/SPX)的时刻是
    晨刊 raw 的报价时刻, 印出来的就是那个。"""
    from app import db

    if not latest_reading or latest_df.empty or source is None:
        return
    latest = pd.Timestamp(latest_df["collected_at"].max())
    day = market_calendar.market_day(latest.to_pydatetime())
    moments = [pd.Timestamp(m) for m in db.get_collection_moments(conn, ticker, days=3, source=source)]
    today = [m for m in moments if market_calendar.market_day(m.to_pydatetime()) == day and m < latest]
    if not today:
        return
    first = min(today)
    earlier = with_iv(db.get_snapshots_at(conn, ticker, [first], source=source))
    before = metrics.gamma_weather(earlier) if not earlier.empty else None
    if not before:
        return
    st.markdown(_since_line(before, latest_reading, first), unsafe_allow_html=True)


def _since_line(before: dict, after: dict, first: pd.Timestamp) -> str:
    def flip(reading):
        value = reading.get("gamma_flip")
        return "—" if value is None else f"{value:,.2f}"

    when = to_viewer(pd.Series([first])).dt.strftime("%H:%M").iloc[0]
    parts = [
        f"{_t('Flip', '翻转位')} {flip(before)} → <b>{flip(after)}</b>",
        f"{_t('Net GEX', '净 GEX')} {weather.format_gex(before['net_gex'])} → <b>{weather.format_gex(after['net_gex'])}</b>",
    ]
    if before.get("state") != after.get("state"):
        parts.append(f"{_t('Weather', '天气')} {_weather_word(before['state'])} → <b>{_weather_word(after['state'])}</b>")
    label = _t(f"SINCE {when} {timezone_label()}", f"自 {when}（{timezone_label()}）起")
    return (
        '<div class="gg-since" style="font-size:12px;color:#8B948F;margin:-0.35rem 0 0.4rem 2px;">'
        f'<span style="color:#F5B342;">●</span> {label}　' + "　·　".join(parts) + "</div>"
    )


# --- B2 + B3 最大痛点的底子与预期波动 ------------------------------------------------


def expiry_walls(chain: pd.DataFrame) -> dict:
    """单个到期日的 Call 墙 / Put 墙: 该到期日未平仓量最大的行权价(卡片上的墙是 30 天合计)。"""
    out = {}
    oi = pd.to_numeric(chain.get("open_interest"), errors="coerce").fillna(0)
    for side in ("call", "put"):
        rows = chain[(chain["option_type"] == side) & (oi > 0)]
        if not rows.empty:
            out[side] = float(rows.loc[pd.to_numeric(rows["open_interest"], errors="coerce").idxmax(), "strike"])
    return out


def wall_hits(move: dict, walls: dict) -> list[tuple[str, float]]:
    """1σ 区间够得着的墙: Put 墙在 [下沿, 现价], Call 墙在 [现价, 上沿](边界含)。"""
    spot, hits = move["underlying_price"], []
    if "put" in walls and move["lower"] <= walls["put"] <= spot:
        hits.append(("put", walls["put"]))
    if "call" in walls and spot <= walls["call"] <= move["upper"]:
        hits.append(("call", walls["call"]))
    return hits


def max_pain_extras(latest_df: pd.DataFrame, expiry, latest_moment) -> None:
    chain = latest_df[pd.to_datetime(latest_df["expiry"]) == pd.Timestamp(expiry)]
    if chain.empty:
        return
    carrying = int((pd.to_numeric(chain["open_interest"], errors="coerce").fillna(0) > 0).sum())
    st.caption(_t(
        f"Max pain here rests on the {carrying} of {len(chain)} contracts in this expiry that have open interest; "
        "with only a handful, the level means little.",
        f"由该到期日 {len(chain)} 张合约中有未平仓量的 {carrying} 张算出; 有持仓的太少时, 最大痛点没有意义。",
    ))

    st.subheader(_t("Expected move to expiry", "到期预期波动"))
    move = metrics.expected_move(latest_df, pd.Timestamp(expiry), pd.Timestamp(latest_moment))
    if move is None:
        st.caption(_t(
            "No expected move: this expiry has no time left, or its at-the-money volatility is unknown.",
            "算不出预期波动: 这个到期日已没有剩余时间, 或平值隐含波动率缺失。",
        ))
        return
    left, middle, right = st.columns(3)
    left.metric(_t(f"Expected move (1σ, ±{move['move_pct']:.2f}%)", f"预期波动(1σ, ±{move['move_pct']:.2f}%)"),
                f"±{move['move']:,.2f}")
    middle.metric(_t("Range low", "区间下沿"), f"{move['lower']:,.2f}")
    right.metric(_t("Range high", "区间上沿"), f"{move['upper']:,.2f}")
    for side, strike in wall_hits(move, expiry_walls(chain)):
        name = "Put" if side == "put" else "Call"
        st.warning(_t(
            f"The 1σ range touches the {name} wall at {strike:g} (this expiry's largest {name} open interest).",
            f"1σ 波动够得着 {strike:g} 的 {name} 墙 —— 这个到期日 {name} 未平仓量最集中的行权价。",
        ), icon="⚠️")
    days = move["years"] * 365
    st.caption(_t(
        f"At-the-money implied volatility {move['implied_volatility']:.1%}, {days:.1f} days to expiry. "
        "One standard deviation: about two chances in three of finishing inside the range — so about one "
        "expiry in three finishes outside it, and that is normal.",
        f"平值隐含波动率 {move['implied_volatility']:.1%}, 距到期 {days:.1f} 天。一个标准差: 约三分之二的概率收在区间内,"
        " 也就是大约每三个到期日有一个收在区间外, 那是正常的。这里的墙只算这个到期日, 和天气卡片(30 天合计)可能不同。",
    ))


# --- B4 变化视图的快捷对比 ----------------------------------------------------------

_PRESET_KEY = "_mb_compare_preset"
_PRESETS = ((1, "1 day", "1 天"), (7, "1 week", "1 周"), (30, "1 month", "1 月"))


def preset_day(days: list[dt.date], span: int) -> dt.date | None:
    """`days` 新到旧。1 天 = 上一个有记录的交易日; 其余 = 离最新一天至少 span 天的最近一天
    (按记录里的交易日挑, 周末和假期不会落空)。不够远就 None。"""
    if len(days) < 2:
        return None
    if span == 1:
        return days[1]
    latest = days[0]
    for day in days[1:]:
        if (latest - day).days >= span:
            return day
    return None


def _apply_preset(day) -> None:
    for key in ("changes_from", "changes_to"):
        st.session_state.pop(key, None)  # 清掉选择框的状态, 让下面的默认值生效(直接改状态会冒警告)
    st.session_state[_PRESET_KEY] = day


def compare_presets(days: list[dt.date], default_before):
    """在两个日期选择框上方画三个按钮; 返回「对比起点」的默认值(点过按钮就是按钮那天)。"""
    columns = st.columns([1, 1, 1, 9])
    for column, (span, english, chinese) in zip(columns, _PRESETS):
        target = preset_day(days, span)
        column.button(
            _t(english, chinese), key=f"mb_preset_{span}", disabled=target is None,
            on_click=_apply_preset, args=(target,), use_container_width=True,
            help=None if target else _t("Not enough history yet.", "历史还不够长。"),
        )
    chosen = st.session_state.pop(_PRESET_KEY, None)
    return chosen if chosen in days else default_before


# --- B5 合约理论价 --------------------------------------------------------------------


def theoretical_prices(history: pd.DataFrame, strike: float, expiry, option_type: str) -> pd.Series:
    """每一班按当时的标的价与隐含波动率用 Black-Scholes 算一遍。利率用配置里的平利率,
    股息率记 0(开源版不取国债曲线与股息); 到期或缺数的那几班为 NaN。"""
    spot = pd.to_numeric(history["underlying_price"], errors="coerce").to_numpy(dtype=float)
    sigma = pd.to_numeric(history["implied_volatility"], errors="coerce").to_numpy(dtype=float)
    years = years_to_expiry_by_moment(expiry, pd.to_datetime(history["collected_at"])).to_numpy(dtype=float)
    valid = (spot > 0) & (sigma > 0) & (years > 0)
    out = np.full(len(history), np.nan)
    if valid.any():
        out[valid] = _bs_price(spot[valid], float(strike), years[valid], sigma[valid],
                               config.RISK_FREE_RATE, option_type == "call", 0.0)
    return pd.Series(out, index=history.index)


def price_chart(history: pd.DataFrame, strike: float, expiry, option_type: str, with_viewer_index, colors) -> None:
    frame = history[["collected_at", "last_price"]].copy()
    frame["theoretical"] = theoretical_prices(history, strike, expiry, option_type)
    names = {"last_price": _t("Last price", "最新成交价"), "theoretical": _t("Theoretical", "理论价")}
    st.line_chart(with_viewer_index(frame)[["last_price", "theoretical"]].rename(columns=names), color=colors)
    st.caption(_t(
        f"The model line prices each collection with Black-Scholes from that moment's underlying and the implied "
        f"volatility charted below (solved from the quote midpoint when both sides are quoted), using a flat "
        f"{config.RISK_FREE_RATE:.2%} rate and zero dividend. When the two lines part, the trade print has usually "
        "gone stale on a quiet contract; it is rarely a mispricing.",
        f"理论价 —— 用下方的隐含波动率(有买卖报价时从中间价反解, 否则用最新成交价)按 Black-Scholes 算出, 利率按"
        f"固定 {config.RISK_FREE_RATE:.2%}、不计股息。最新成交价是最后一笔成交, 冷门合约可能是几小时甚至几天前的;"
        " 两条线拉开, 多半是成交价陈旧, 不是定价错了。",
    ))


def greek_units() -> None:
    st.caption(_t(
        "Units: delta and gamma per $1 of the underlying; theta per calendar day; vega and rho per 1 pp of "
        "volatility and rate; charm per year.",
        "单位: Delta、Gamma 按标的每变动 1 美元; Theta 按每个自然日; Vega、Rho 按波动率、利率每变动 1 个百分点; Charm 按每年。",
    ))
