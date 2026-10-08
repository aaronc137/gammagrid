"""Streamlit 页面 —— morning-bites 定制版(晨读 · Gamma)。只管显示与输入; 算式在 metrics.py, 入库在 ingest_archive.py。

与上游 dashboard.py 的差别(全部在这一层, metrics_core.py 不动):
  * 没有加删票 / 「Collect data」/ 采集间隔 / 搜票框 / TradingView / GitHub 星标: 采集由 morning-bites 的归档驱动
    (app/ingest_archive.py), 这一页零外部请求; 标的固定 SPX / SPY / QQQ。
  * 中文、本站暗色; 时刻一律美东(viewtime.py)。
  * GEX 展示单位换成「每 1% 波动的美元 gamma」(gammagrid 库里存的是每 $1, 只在显示处乘 现价 × 0.01), 逐处标口径;
    页头并列晨刊四件套(读 morning-bites 的 out/gex/<latest>.json, 那是 gex_calc 的口径, 两套各标各的)。
  * 墙 / 翻转位的**定义**不改(热图标注与状态句建在上面): 墙 = 各侧 OI 最大的行权价; 翻转位 = 离现价最近的累计穿零,
    线性插值成价格。晨刊是 signed GEX 的 argmax / argmin 与 ±15% 带内升序第一次穿零(不插值), 页脚写明。
  * 没有 Cloudflare Access 头就 st.stop()(纵深一层, 门在隧道)。

Modified for morning-bites, 2026-10-08. 基于 GammaGrid v0.7.0, AGPL-3.0, 同本仓 LICENSE。
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from matplotlib.colors import LinearSegmentedColormap

from app import config, day_summary, db, freshness, metrics, theme, weather  # noqa: I001 — grouped by what they are
from app.viewtime import (
    format_date,
    format_datetime,
    strikes_around_money,
    timezone_label,
    to_viewer,
    with_viewer_index,
)

FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E"
    "%3Crect width='16' height='16' fill='%230F1114'/%3E"
    "%3Crect x='2' y='9' width='5' height='5' fill='%233DBA7A'/%3E"
    "%3Crect x='9' y='2' width='5' height='5' fill='%23F26B5E'/%3E%3C/svg%3E"
)

st.set_page_config(page_title="晨读 · Gamma", page_icon=FAVICON, layout="wide")
st.markdown(theme.stylesheet(), unsafe_allow_html=True)


# --- 鉴权: 只信 Cloudflare Access ---------------------------------------------
# 隧道的 originRequest.access 已经在 cloudflared 验过 JWT 才会转发到这里; 这一层是纵深: 任何不经隧道、
# 又不是回环地址的请求(Host 不是 127.0.0.1 / localhost)没有那个头就停。bare 模式(tests/render_views.py)
# 与 ssh 端口转发的本机核对都是回环, 照常渲染。

def _headers() -> dict[str, str]:
    try:
        raw = st.context.headers
    except Exception:  # noqa: BLE001 — 无浏览器, 无 context
        return {}
    try:
        return {str(k).lower(): str(v) for k, v in raw.items()} if raw else {}
    except Exception:  # noqa: BLE001
        return {}


_h = _headers()
_host = _h.get("host", "").split(":")[0]
if config.ACCESS_GATE and _host not in ("", "127.0.0.1", "localhost") and not _h.get("cf-access-jwt-assertion"):
    st.error("请经站点入口访问(这一页只在 Cloudflare Access 之后提供)。")
    st.stop()


def _drop_stale_choice(key: str, options) -> None:
    """控件记住的旧值不在新选项里时忘掉它, 否则 Streamlit 直接抛。"""
    if key in st.session_state and st.session_state[key] not in list(options):
        del st.session_state[key]


GEX_UNIT = "每 1% 波动的美元 gamma"


def per_pct(value: float | None, spot: float) -> float | None:
    """gammagrid 的 GEX 是每 $1 的美元 gamma; 本站全站用每 1%(× 现价 × 0.01), 与晨刊 / 静态 Gamma 页同一单位。"""
    return weather.per_pct(value, spot)


# --- 晨刊口径(morning-bites 的 gex_calc)-------------------------------------
_SESSION_ORDER = {"premarket": 0, "intraday": 1, "close": 2}
_SESSION_ZH = {"premarket": "盘前", "intraday": "盘中", "close": "收盘"}


@st.cache_data(ttl=120)
def _mb_latest_read(ticker: str) -> dict | None:
    """out/gex/<latest>.json 里这个标的的四件套(spot / 净 GEX / 双墙 / 翻转位 / 报价时刻)。读不到就 None, 页面不印那一行。"""
    files = [p for p in Path(config.MB_OUT, "gex").glob("????-??-??-*.json") if p.stem[11:] in _SESSION_ORDER]
    for path in sorted(files, key=lambda p: (p.stem[:10], _SESSION_ORDER[p.stem[11:]]), reverse=True):
        try:
            snap = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for read in snap.get("reads") or []:
            if str(read.get("ticker", "")).upper() == ticker.upper():
                return {**read, "date": snap.get("date"), "session": snap.get("session")}
        return None
    return None


def render_mb_strip(read: dict | None) -> None:
    if not read:
        return
    def _n(v, fmt="{:,.2f}"):
        return "—" if v is None else fmt.format(v)
    levels = "".join(
        f"<div><dt>{label}</dt><dd{cls}>{value}</dd></div>"
        for label, value, cls in (
            ("现价", _n(read.get("spot")), ""),
            ("净 GEX · 每 1%", weather.format_gex(read.get("net_gex")),
             ' class="gg-green"' if (read.get("net_gex") or 0) >= 0 else ' class="gg-purple"'),
            ("Call 墙", _n(read.get("call_wall"), "{:g}"), ' class="gg-green"'),
            ("Put 墙", _n(read.get("put_wall"), "{:g}"), ' class="gg-purple"'),
            ("累计穿零档", _n(read.get("flip"), "{:g}"), ""),
        )
    )
    st.markdown(
        '<div class="gg-mb"><div class="gg-mb-words"><div class="gg-mb-label">晨刊口径'
        '<span class="gg-weather-scope"> · morning-bites gex_calc · Cboe 厂商 gamma · 全部未到期到期日</span></div>'
        f'<div class="gg-weather-sentence">{read.get("date")} {_SESSION_ZH.get(read.get("session"), read.get("session"))}'
        f' · Cboe 报价时刻 {read.get("quote_timestamp")} UTC · 墙 = signed GEX 极值档, 穿零 = ±15% 带内升序第一次由负转非负的行权价'
        '(不插值) —— 与下面 gammagrid 的定义不同, 两套各标各的, 不可互换</div></div>'
        f'<dl class="gg-levels">{levels}</dl></div>',
        unsafe_allow_html=True,
    )


# --- 单合约 ---------------------------------------------------------------------

def render_option_detail(
    conn, df: pd.DataFrame, selected_ticker: str, tracked: pd.DataFrame,
    opt_expiry: pd.Timestamp, opt_strike: float, opt_type: str, key_prefix: str,
) -> None:
    """一份合约的价格 / IV / greeks 历史 —— 「单合约」视图与筛选器点开一行共用。"""
    already_tracked = not tracked.empty and (
        (tracked["expiry"] == opt_expiry)
        & (tracked["strike"] == opt_strike)
        & (tracked["option_type"] == opt_type)
    ).any()
    if already_tracked:
        st.caption("📌 已钉住")
    elif st.button("📌 钉住", key=f"{key_prefix}_pin_contract"):
        db.add_tracked_contract(conn, selected_ticker, opt_expiry, opt_strike, opt_type)
        st.rerun()

    greeks_history = metrics.contract_greeks_history(df, opt_strike, opt_expiry, opt_type)
    if greeks_history.empty:
        st.info("这份合约没有历史。")
        return

    price_column, attribution_column = st.columns(2)
    with attribution_column:
        render_greek_attribution(greeks_history)
    with price_column:
        st.subheader("合约价格")
        st.line_chart(with_viewer_index(greeks_history)["last_price"], color=theme.PRIMARY)
    with st.expander("ℹ️ 怎么读"):
        st.write("每班采集时这份合约的最后成交价。盘前 / 冷门档的最后成交价可能是上一场的, 与 IV 对不上时以 IV 为准。")

    st.subheader("合约隐含波动率(Cboe 报价 IV)")
    st.line_chart(with_viewer_index(greeks_history)["implied_volatility"], color=theme.ACCENT)
    latest_iv = greeks_history.iloc[-1]["implied_volatility"]
    st.caption(f"当前合约 IV **{latest_iv:.1%}**。已实现波动率本站不算(没有价格历史源)。")

    st.subheader("Greeks 随时间")
    greek_cols = ["delta", "gamma", "theta", "vega", "rho", "vanna", "charm"]
    left, right = st.columns(2)
    for i, greek in enumerate(greek_cols):
        target = left if i % 2 == 0 else right
        target.caption(greek.capitalize())
        target.line_chart(
            with_viewer_index(greeks_history)[greek],
            color=theme.PRIMARY if i % 2 == 0 else theme.ACCENT,
        )
    with st.expander("📊 当前值与趋势(上游英文原话)"):
        for note in metrics.interpret_greeks(greeks_history):
            st.write(f"- {note}")


def render_greek_attribution(greeks_history: pd.DataFrame) -> None:
    """合约价格变动按 greek 拆分的瀑布图, 单位美分。"""
    attribution = metrics.greek_attribution(greeks_history)
    st.subheader("价格去了哪")
    if attribution.by_day.empty:
        if attribution.dropped_cheap:
            st.info(
                f"这份合约有 {attribution.dropped_cheap} 天成交价低于 {config.ATTRIBUTION_MIN_PRICE * 100:.0f} 美分, "
                "那几天不拆: 几美分的合约上每个 greek 都是四舍五入的算术。"
            )
        else:
            st.info("可用天数不够(至少要两个相隔一天的交易日)。")
        return
    totals = attribution.totals
    labels = ["起点", "Delta", "Gamma", "Vega", "Theta", "残差", "终点"]
    steps = [totals[name] * 100 for name in (*metrics.ATTRIBUTION_TERMS, "residual")]
    figure = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", *["relative"] * 5, "total"],
        x=labels,
        y=[attribution.start_price * 100, *steps, 0],
        text=waterfall_labels(attribution.start_price * 100, steps),
        textposition="outside",
        decreasing={"marker": {"color": theme.PRIMARY}},
        increasing={"marker": {"color": theme.ACCENT}},
        totals={"marker": {"color": theme.MUTED}},
        connector={"line": {"color": theme.BORDER}},
    ))
    figure.update_layout(
        height=300, margin={"l": 8, "r": 8, "t": 8, "b": 8}, paper_bgcolor=theme.SURFACE, plot_bgcolor=theme.SURFACE,
        font={"color": theme.TEXT}, showlegend=False, yaxis={"title": "美分 / 股", "zeroline": True},
    )
    st.plotly_chart(figure, use_container_width=True)

    cumulative = attribution.by_day[["day", *metrics.ATTRIBUTION_TERMS]].copy()
    for name in metrics.ATTRIBUTION_TERMS:
        cumulative[name] = cumulative[name].cumsum() * 100
    st.caption("逐日累计, 美分 —— 每个 greek 在哪天起作用")
    st.line_chart(
        with_viewer_index(cumulative, "day"), height=200,
        color=[theme.ACCENT, "#E8C46A", theme.PRIMARY, "#5FA4E0"],
    )
    spans = attribution.by_day["missing_trading_days"]
    st.caption(f"「一天」= 每个交易日(美东)最后一班采集 —— 本窗口 {len(attribution.by_day)} 个区间。")
    notes = []
    if attribution.dropped_cheap:
        notes.append(f"{attribution.dropped_cheap} 天未计入: 成交价低于 {config.ATTRIBUTION_MIN_PRICE * 100:.0f} 美分。")
    if attribution.dropped_unreliable:
        notes.append(f"{attribution.dropped_unreliable} 天未计入: IV 没过离群守卫。")
    if int(spans.sum()):
        notes.append(f"窗口内 {int(spans.sum())} 个交易日没有采集, 它们的变动并进相邻区间, 落在残差里。")
    residual_share = abs(totals["residual"]) / max(abs(totals["actual"]), 1e-9)
    if residual_share > 0.5:
        notes.append(f"残差占整段变动的 {residual_share:.0%}: 模型解释不了这份合约 —— 价差、陈旧成交或利率的作用大过 greeks。")
    for note in notes:
        st.caption(f"⚠️ {note}")


def waterfall_labels(start: float, steps: list[float]) -> list[str]:
    return [f"{start:.1f}¢", *(f"{value:+.1f}¢" for value in steps), f"{start + sum(steps):.1f}¢"]


def format_compact(value: float) -> str:
    """1234 → 1.2k, 1.5e9 → 1.5b: 热图格子里放得下。"""
    if pd.isna(value) or value == 0:
        return "0"
    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    for limit, suffix in ((1e9, "b"), (1e6, "m"), (1e3, "k")):
        if magnitude >= limit:
            return f"{sign}{magnitude / limit:.1f}{suffix}"
    return f"{sign}{magnitude:.0f}"


GEX_CMAP = LinearSegmentedColormap.from_list("gex_dark", [theme.PRIMARY, theme.BACKGROUND, theme.ACCENT])


def style_gex_matrix(matrix: pd.DataFrame, atm_strike: float | None = None):
    """零居中的双色热图(负 = 放大色, 正 = 抑制色), 色阶取非零 |值| 的 90 分位。"""
    display = matrix.rename(columns=format_date)
    numeric = display.to_numpy(dtype=float)
    nonzero_abs = np.abs(numeric[numeric != 0])
    vmax = np.percentile(nonzero_abs, 90) if nonzero_abs.size else 0
    vmax = vmax if vmax > 0 else 1
    text = display.map(format_compact)
    atm_label = None
    if atm_strike is not None and atm_strike in text.index:
        atm_label = f"➤ {atm_strike:g}"
    text.index = [atm_label if v == atm_strike else f"{v:g}" for v in text.index]
    styler = text.style.background_gradient(
        cmap=GEX_CMAP, vmin=-vmax, vmax=vmax, gmap=numeric, axis=None, text_color_threshold=0.6
    )
    if atm_label is not None:
        def highlight_atm_row(row: pd.Series) -> list[str]:
            style = f"border-top: 2px solid {theme.WARNING}; border-bottom: 2px solid {theme.WARNING}; font-weight: 700;"
            return [style if row.name == atm_label else "" for _ in row]
        styler = styler.apply(highlight_atm_row, axis=1)
    return styler


conn = db.get_connection()

st.markdown(
    f"""
    <div style="display:flex;align-items:baseline;gap:12px;margin-bottom:0.25rem;">
      <span style="font-size:{theme.TEXT_STRONG};font-weight:700;letter-spacing:0.01em;">晨读 · Gamma</span>
      <span style="color:{theme.MUTED};font-size:{theme.TEXT_BASE};">Cboe 期权链 · 回放 morning-bites 的三班归档 · 零外部请求</span>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("标的")
    watchlist = db.get_watchlist(conn)
    current_ticker = st.session_state.get("selected_ticker")
    for ticker in watchlist:
        if st.button(
            ticker, key=f"select_ticker_{ticker}",
            type="primary" if ticker == current_ticker else "secondary", use_container_width=True,
        ):
            st.session_state["selected_ticker"] = ticker
            st.rerun()
    st.divider()
    st.markdown("[← 晨读首页](/)  \n[静态 Gamma · 晨刊口径](/boards/gex.html)  \n[关键位回看](/boards/levels-review.html)")
    st.divider()
    with st.expander("📋 入库记录"):
        st.caption(f"时刻为美东({timezone_label()})。每行一班一标的, started_at 是 Cboe 给那份链盖的报价时刻。")
        runs = db.get_recent_runs(conn, limit=30)
        if runs.empty:
            st.caption("还没有入库记录。")
        else:
            runs_display = runs.copy()
            runs_display["started_at"] = to_viewer(runs_display["started_at"]).dt.strftime("%Y-%m-%d %H:%M:%S")
            runs_display["oi_zero_fraction"] = runs_display["oi_zero_fraction"].map(
                lambda v: f"{v:.0%}" if pd.notna(v) else "—"
            )
            st.dataframe(
                runs_display[["started_at", "ticker", "status", "rows_fetched", "oi_zero_fraction", "error_message"]],
                use_container_width=True, hide_index=True,
            )
    st.divider()
    st.caption(
        f"基于 [GammaGrid]({config.UPSTREAM_URL}) {config.APP_VERSION}(AGPL-3.0)修改 · "
        f"修改版源码 [{config.FORK_URL.split('github.com/')[-1]}@{config.BUILD_COMMIT[:9]}]"
        f"({config.FORK_URL}/tree/{config.BUILD_COMMIT})"
    )

if not watchlist:
    st.info("还没有入库的快照: 等 gg-ingest 回放第一班 out/gex 归档。")
    st.stop()

selected_ticker = st.selectbox("标的", watchlist, key="selected_ticker")

load_full_history = st.checkbox(
    f"加载全部历史(默认最近 {config.SNAPSHOT_HISTORY_DAYS} 天)",
    key="load_full_history", help="SPX 一班 3 万行, 全部历史会慢。",
)
history_days = None if load_full_history else config.SNAPSHOT_HISTORY_DAYS

page_source = db.active_source(conn, selected_ticker)


def with_our_iv(frame):
    """每条链都经这里: morning-bites 版直通 Cboe 报价 IV(app/metrics.py), 只补两个标记列。"""
    return metrics.with_solved_iv(frame, metrics.DEFAULT_PRICING, ticker=selected_ticker)


latest_df = with_our_iv(db.get_latest_snapshot(conn, selected_ticker, source=page_source))

_collector_interval = max(db.get_collector_interval(conn), 15)
_last_success, _failures = db.collection_state(conn, selected_ticker, source=page_source)
_freshness = freshness.assess(_last_success, _failures, _collector_interval)
if _freshness:
    _state, _note = _freshness
    if _state == freshness.RESTING:
        st.caption(_note)
    else:
        st.warning(_note, icon="⚠️")

if latest_df.empty:
    st.info(f"{selected_ticker} 还没有数据(等 gg-ingest)。")
    st.stop()

latest_date = latest_df["collected_at"].max()
spot_latest = float(latest_df["underlying_price"].iloc[0])
expiries = sorted(latest_df["expiry"].unique())

_weather = metrics.gamma_weather(latest_df)
if _weather:
    st.markdown(weather.panel(_weather, latest_moment=latest_date), unsafe_allow_html=True)
render_mb_strip(_mb_latest_read(selected_ticker))

_tracked_cache: dict[str, pd.DataFrame] = {}


def get_tracked() -> pd.DataFrame:
    if "df" not in _tracked_cache:
        _tracked_cache["df"] = db.get_tracked_contracts(conn, selected_ticker)
    return _tracked_cache["df"]


VIEWS = ["概览", "较昨日", "Max Pain / GEX", "GEX 热图", "波动率", "单合约", "筛选器", "异常成交", "OI 变化"]
active_view = st.segmented_control("视图", VIEWS, default=VIEWS[0], key="active_view", label_visibility="collapsed")
active_view = active_view or VIEWS[0]

if active_view == "概览":
    st.subheader("概览")
    st.caption(f"{selected_ticker} 最新一班: Cboe 报价时刻 {format_datetime(latest_date)}")
    st.subheader("Put/Call 比")
    pcr = db.get_put_call_ratio(conn, selected_ticker, days=history_days, source=page_source)
    st.line_chart(with_viewer_index(pcr)[["pcr_volume", "pcr_oi"]], color=[theme.PRIMARY, theme.ACCENT])
    with st.expander("ℹ️ 怎么读"):
        st.write(
            "put 与 call 的成交量比(pcr_volume)与未平仓量比(pcr_oi), 每班一点。绝对水平不如它相对自己历史的偏离有用: "
            "与这张图上过去的值比, 别套通用经验值。"
        )

    st.subheader("波动率曲面(IV surface)")
    iv_surface_points = metrics.iv_surface(latest_df)
    iv_grid = metrics.iv_surface_grid(iv_surface_points)
    if iv_grid is None:
        st.info("最新一班的数据不够画曲面(至少要两个行权价 × 两个到期日有 IV)。")
    else:
        grid_strikes, grid_years, grid_iv = iv_grid
        real_strikes = np.sort(iv_surface_points["strike"].unique())
        nearest_strike_per_col = np.array(
            [f"{real_strikes[np.abs(real_strikes - gx).argmin()]:g}" for gx in grid_strikes]
        )
        dte_per_row = np.round(grid_years * 365).astype(int).astype(str)
        customdata = np.dstack([
            np.tile(nearest_strike_per_col, (len(grid_years), 1)),
            np.tile(dte_per_row.reshape(-1, 1), (1, len(grid_strikes))),
        ])
        fig = go.Figure(data=[go.Surface(
            x=grid_strikes, y=grid_years, z=grid_iv, colorscale="Viridis", customdata=customdata,
            hovertemplate="行权价 ≈ %{customdata[0]}<br>DTE: %{customdata[1]} 天<br>IV: %{z:.2f}<extra></extra>",
        )])
        expiry_ticks = (
            iv_surface_points[["years_to_expiry", "expiry"]].drop_duplicates().sort_values("years_to_expiry")
        )
        fig.update_layout(
            scene={
                "xaxis_title": "行权价",
                "yaxis": {"title": "到期日", "tickmode": "array",
                          "tickvals": expiry_ticks["years_to_expiry"].tolist(),
                          "ticktext": [format_date(d) for d in expiry_ticks["expiry"]]},
                "zaxis_title": "IV",
            },
            margin={"l": 0, "r": 0, "t": 10, "b": 0}, height=500,
            paper_bgcolor=theme.SURFACE, font={"color": theme.TEXT},
        )
        st.plotly_chart(fig, use_container_width=True)
        with st.expander("ℹ️ 怎么读"):
            st.write(
                "最新一班整条链的 IV: 一轴行权价, 一轴到期日, 高度 / 颜色是 IV 本身(每个行权价取 OTM 那一侧: 现价下方取 put, "
                "上方取 call)。真实的行权价与到期日不落在规则网格上, 曲面是在实际点之间线性插值填出来的(边缘取最近邻), "
                "只是显示平滑, 不是新数据 —— 所以光标下的格点几乎不对应真实合约, 悬停读数给的是最近的真实行权价与 DTE。"
                "局部尖刺多半是那一带数据稀, 看整体形状别看单个凸起。IV 是 Cboe 报价 IV(小数, 0.18 = 18%)。"
            )


if active_view == "较昨日":
    _days = db.list_day_summaries(conn, selected_ticker, page_source) if page_source else []
    if len(_days) < 1:
        st.info("还没有日行: 每班入库后写一行, 回放跑完就有。")
    else:
        _default_after = _days[0]
        _default_before = _days[1] if len(_days) > 1 else _days[0]
        left, right = st.columns(2)
        day_before = left.selectbox("从", _days, index=_days.index(_default_before), key="changes_from", format_func=format_date)
        day_after = right.selectbox("到", _days, index=_days.index(_default_after), key="changes_to", format_func=format_date)
        row_after = db.get_day_summary(conn, selected_ticker, page_source, day_after)
        row_before = db.get_day_summary(conn, selected_ticker, page_source, day_before) if day_before != day_after else None
        if row_after is None:
            st.info("那一天没有日行。")
        else:
            def _rollup(row):
                if row is None:
                    return None
                stored = db.get_moment_rollup(conn, selected_ticker, page_source, row["collected_at"]) or {}
                return {
                    "iv_weighted_avg": stored.get("iv_weighted_avg"),
                    "call_volume": row.get("call_volume"), "put_volume": row.get("put_volume"),
                    "call_oi": row.get("call_oi"), "put_oi": row.get("put_oi"),
                }

            rollup_after = _rollup(row_after)
            rollup_before = _rollup(row_before)
            same_expiry_pain = None
            if (row_before and row_after.get("nearest_expiry")
                    and str(row_before.get("nearest_expiry")) != str(row_after.get("nearest_expiry"))):
                earlier = db.get_snapshots_at(conn, selected_ticker, [row_before["collected_at"]], source=page_source)
                if not earlier.empty:
                    wanted = pd.Timestamp(row_after["nearest_expiry"])
                    same_day = earlier[pd.to_datetime(earlier["expiry"], errors="coerce") == wanted]
                    if not same_day.empty:
                        pain = metrics.max_pain(same_day, wanted)
                        same_expiry_pain = None if pain is None or pd.isna(pain) else float(pain)

            ladder = day_summary.changes(row_before, row_after, rollup_before, rollup_after, same_expiry_pain)
            st.subheader(day_summary.headline(ladder))
            st.caption(
                f"{format_date(day_before)} → {format_date(day_after)}"
                + ("" if row_before else "  ·  第一天, 还没有可比的")
                + f"  ·  每天取那天最后一班(美东日期)  ·  净 GEX {GEX_UNIT}, 近月窗口(与上方状态句同一口径)"
            )
            rows_html = []
            for line in ladder:
                tone = ""
                if line["kind"] == day_summary.DAMPING:
                    tone = " gg-green"
                elif line["kind"] == day_summary.AMPLIFYING:
                    tone = " gg-purple"
                note = line.get("note")
                if line["key"] == "expiries":
                    parts = []
                    if line.get("rolled_off"):
                        parts.append("已到期: " + ", ".join(line["rolled_off"]))
                    if line.get("listed"):
                        parts.append("新挂牌: " + ", ".join(line["listed"]))
                    note = note or "; ".join(parts)
                label = line["label"] + (f'<span class="gg-note">{note}</span>' if note else "")
                rows_html.append(
                    f"<tr><td>{label}</td>"
                    f'<td class="gg-num gg-before">{day_summary.format_value(line, "before")}</td>'
                    f'<td class="gg-num">{day_summary.format_value(line, "after")}</td>'
                    f'<td class="gg-num{tone}">{day_summary.format_delta(line)}</td></tr>'
                )
            st.markdown(
                '<table class="gg-ladder"><tr><th></th>'
                f"<th>{format_date(day_before)}</th><th>{format_date(day_after)}</th><th>变化</th></tr>"
                + "".join(rows_html) + "</table>",
                unsafe_allow_html=True,
            )
            profile_after = row_after.get("gex_by_strike") or []
            if profile_after:
                st.subheader(f"两天的 GEX 剖面(近月窗口, {GEX_UNIT})")
                frame = pd.DataFrame({format_date(day_after): {
                    k: per_pct(v, row_after["underlying_price"]) for k, v in dict(profile_after).items()}})
                if row_before and row_before.get("gex_by_strike"):
                    frame[format_date(day_before)] = pd.Series({
                        k: per_pct(v, row_before["underlying_price"]) for k, v in dict(row_before["gex_by_strike"]).items()})
                frame = frame.sort_index()
                frame.index.name = "strike"
                frame = strikes_around_money(frame, row_after["underlying_price"], 20)
                st.bar_chart(frame, stack=False, color=[theme.ACCENT, theme.PRIMARY][: len(frame.columns)])
            with st.expander("ℹ️ 怎么读"):
                st.write(
                    "两个交易日并排。「一天」= 美东日期那天最后一班采集, 与 OI 变化同一规则。颜色只给状态: 绿 = 往「对冲流抑制」"
                    "那边动, 红 = 往「放大」那边动, 其余变动用素色。位置用「几档」说(一档 = 这条链相邻两个行权价的间距); "
                    "Max Pain 只在同一到期日之间比, 最近到期日换了就注明换前是哪个。"
                )


if active_view == "Max Pain / GEX":
    has_time_left = [e for e in expiries if metrics.years_to_expiry(e, latest_date) > 0]
    default_expiry_index = expiries.index(has_time_left[0]) if has_time_left else 0

    def format_gex_expiry(expiry) -> str:
        if metrics.years_to_expiry(expiry, latest_date) > 0:
            return format_date(expiry)
        return f"{format_date(expiry)}  ⚠️ 已无 gamma"

    selected_expiry = st.selectbox(
        "到期日", expiries, index=default_expiry_index, format_func=format_gex_expiry, key=f"expiry_pain_gex_{selected_ticker}",
    )
    years_left = metrics.years_to_expiry(selected_expiry, latest_date)

    st.subheader("Max Pain")
    mp = metrics.max_pain(latest_df, selected_expiry)
    st.metric("Max Pain 行权价", mp if mp is not None else "n/a")
    with st.expander("ℹ️ 怎么读"):
        st.write("期权卖方总赔付最小的行权价。到期前价格有向它靠拢的倾向, 越近到期越明显; 是倾向不是预测, 基本面消息会压过它。")

    st.subheader(f"近似 GEX 剖面(BS 口径, {GEX_UNIT})")
    gex = metrics.gamma_exposure_profile(latest_df, selected_expiry)
    if years_left <= 0:
        st.info(f"这个到期日({format_date(selected_expiry)})在最新一班({format_datetime(latest_date)})已无剩余时间, gamma 按定义为零, 不是缺数据。")
    elif not gex.empty:
        gex = gex.assign(gex=gex["gex"] * spot_latest / 100)
        net_gex = metrics.net_gamma_exposure(gex)
        if net_gex >= 0:
            st.success(f"净 GEX {weather.format_gex(net_gex)}(每 1%) —— 正 gamma: 对冲流倾向抑制波动")
        else:
            st.warning(f"净 GEX {weather.format_gex(net_gex)}(每 1%) —— 负 gamma: 对冲流倾向放大波动")
        gex_chart_data = gex.assign(sign=np.where(gex["gex"] >= 0, "正", "负"))
        st.altair_chart(
            alt.Chart(gex_chart_data).mark_bar().encode(
                x=alt.X("strike:O", title="行权价"),
                y=alt.Y("gex:Q", title=f"GEX({GEX_UNIT})"),
                color=alt.Color("sign:N", scale=alt.Scale(domain=["正", "负"], range=[theme.ACCENT, theme.PRIMARY]), legend=None),
            ),
            use_container_width=True,
        )
    else:
        st.info("这个到期日没有可算 GEX 的数据。")
    st.caption("Black-Scholes 用 Cboe 报价 IV 反算 gamma, 符号用「Call 记正、Put 记负」的朴素假设; 不是做市商真实头寸, 只是近似。")
    with st.expander("ℹ️ 怎么读"):
        st.write("总 gamma 为正 —— 市场偏「粘」, 对冲流抑制大幅波动; 为负 —— 对冲与趋势同向, 波动可能加速。按行权价看, 绝对值最大的几根常成为对冲流造出的支撑 / 阻力, 越近到期越明显。")

if active_view == "GEX 热图":
    st.subheader(f"GEX 热图: 行权价 × 到期日({GEX_UNIT})")
    snapshot_dates = [
        pd.Timestamp(moment)
        for moment in db.get_collection_moments(conn, selected_ticker, days=history_days, source=page_source)
    ] or [pd.Timestamp(latest_date)]
    as_of = st.selectbox("哪一班(回放历史, 不自动刷新)", snapshot_dates, format_func=format_datetime, key="heatmap_as_of")
    is_latest = as_of == snapshot_dates[0]
    st.caption("最新一班(当前状态)" if is_latest else "历史快照 —— 回放")

    snapshot_df = with_our_iv(db.get_snapshots_at(conn, selected_ticker, [as_of], source=page_source))
    if snapshot_df.empty:
        st.info("入库记录里有这一班, 但没有行 —— 换一班。")
        st.stop()
    all_expiries_at_snapshot = [e for e in sorted(snapshot_df["expiry"].unique()) if metrics.years_to_expiry(e, as_of) > 0]
    spot_at_snapshot = float(snapshot_df["underlying_price"].iloc[0])

    if not all_expiries_at_snapshot:
        st.info("这一班的每个到期日都已停止交易, 整张矩阵按定义全零。换一班。")
        matrix_full = pd.DataFrame()
        shown_expiries = []
        strikes_each_side = 10
    else:
        col_n, col_band = st.columns(2)
        if len(all_expiries_at_snapshot) > 1:
            n_expiries = col_n.slider(
                "最近几个到期日", 1, len(all_expiries_at_snapshot), min(10, len(all_expiries_at_snapshot)),
                key=f"heatmap_n_expiries_{selected_ticker}",
            )
        else:
            n_expiries = 1
            col_n.caption("最近到期日: 1(唯一还在交易的)")
        strikes_each_side = col_band.slider(
            "现价上下各几档", 5, 100, 10, key="heatmap_strikes_each_side", help="离现价最近的行权价上下各画几档; 10 = 21 行。",
        )
        shown_expiries = all_expiries_at_snapshot[:n_expiries]
        matrix_full = metrics.gex_matrix(snapshot_df, as_of=as_of, expiries=shown_expiries)

    if matrix_full.empty:
        st.info("这一班没有可画的数据。")
    else:
        matrix_pct = matrix_full * (spot_at_snapshot / 100)
        matrix_band = strikes_around_money(matrix_pct, spot_at_snapshot, strikes_each_side)
        walls = metrics.dealer_walls(snapshot_df, as_of=as_of, expiries=shown_expiries)
        flip = metrics.gamma_flip_from_matrix(matrix_full, spot_at_snapshot)
        net_by_expiry = metrics.net_gex_from_matrix(matrix_pct, expiries=shown_expiries)
        total_net_gex = net_by_expiry["net_gex"].sum()

        col_price, col_call, col_put, col_flip, col_zone = st.columns(5)
        col_price.metric("现价", f"{spot_at_snapshot:,.2f}")
        col_call.metric("Call 墙(OI 最大)", f"{walls['call_wall']:g}" if walls["call_wall"] is not None else "n/a")
        col_put.metric("Put 墙(OI 最大)", f"{walls['put_wall']:g}" if walls["put_wall"] is not None else "n/a")
        col_flip.metric("插值翻转价", f"{flip:,.2f}" if flip is not None else "n/a")
        col_zone.metric("净 GEX · 每 1%", weather.format_gex(total_net_gex))

        if matrix_band.empty:
            st.info("这一班没有可显示的行权价。")
        else:
            strikes = matrix_band.index.to_numpy(dtype=float)
            atm_strike = matrix_band.index[np.abs(strikes - spot_at_snapshot).argmin()]
            matrix = matrix_band
            nonzero_cols = matrix.columns[(matrix != 0).any(axis=0)]
            hidden_count = len(matrix.columns) - len(nonzero_cols)
            matrix = matrix[nonzero_cols]
            net_by_expiry_shown = net_by_expiry[net_by_expiry["expiry"].isin(nonzero_cols)]
            st.caption(
                f"显示 {len(shown_expiries)} 个到期日里的 {len(nonzero_cols)} 个(共 {len(all_expiries_at_snapshot)} 个)的逐到期日净 GEX"
                + (f" —— {hidden_count} 个在此行权价范围内无活动, 已隐藏" if hidden_count else "") + ":"
            )
            net_display = net_by_expiry_shown.assign(
                expiry=net_by_expiry_shown["expiry"].map(format_date),
                net_gex=net_by_expiry_shown["net_gex"].map(format_compact),
            )
            st.dataframe(net_display.set_index("expiry").T, use_container_width=True)
            viewport_rows = 45
            st.caption(
                f"现价附近 {len(matrix)} 档(最近一档 {atm_strike:g}, 标「➤」): 上下各至多 {strikes_each_side} 档"
                + ("(表内滚动)" if len(matrix) > viewport_rows else "")
            )
            row_height = 24
            table_height = (min(len(matrix), viewport_rows) + 1) * row_height + 3
            st.dataframe(style_gex_matrix(matrix, atm_strike=atm_strike), use_container_width=True, height=table_height, row_height=row_height)

        with st.expander("ℹ️ 怎么读"):
            st.write(
                f"每格是单一班里某行权价 × 某到期日的近似 GEX({GEX_UNIT}; Black-Scholes 用 Cboe 报价 IV 反算 gamma, 符号同「Max Pain / GEX」), "
                "数字缩写(1.2k = 1,200, 1.5b = 15 亿)。绿 = 正(倾向抑制), 红 = 负(倾向放大), 近黑 = 接近零; 色阶按 90 分位定, "
                "极值只涂到上限色, 数字仍照印。0 表示该到期日没挂这个行权价, 不是缺数据。\n\n"
                "**Call 墙 / Put 墙** —— 在显示的到期日范围内, call / put 各自未平仓量最大的行权价(gammagrid 定义; 晨刊用的是 signed GEX 的极值档, "
                "两者可能不同, 页头并列的那一行是晨刊的)。\n\n"
                "**插值翻转价** —— 把显示到期日的 GEX 按行权价累加, 找离现价最近的穿零点, 在相邻两档之间线性插值成价格。不是在假设现价上"
                "重算整条链(那是 SpotGamma 的 Zero Gamma), 也不是晨刊的「累计穿零档」(±15% 带内升序第一次穿零的行权价, 不插值)。\n\n"
                "到期日数量决定墙 / 翻转价 / 逐到期日净 GEX 的计算范围; 行权价档数只管显示, 翻转价在全部行权价上找。"
            )

if active_view == "波动率":
    st.subheader("IV: 成交量加权平均(逐班)")
    iv_avg = db.get_iv_weighted_average(conn, selected_ticker, days=history_days, source=page_source)
    st.line_chart(with_viewer_index(iv_avg)["iv_weighted_avg"], color=theme.PRIMARY)
    with st.expander("ℹ️ 怎么读"):
        st.write("整条链按成交量加权的 IV, 每班一点(Cboe 报价 IV)。涨多半是在等一个事件或不确定性抬头, 跌是在平静。与这个标的自己的历史比, 不同标的的「正常」水平差很远。")

    st.subheader("IV: 单一到期日的偏斜(最新一班)")
    selected_expiry_iv = st.selectbox("到期日", expiries, format_func=format_date, key=f"expiry_iv_skew_{selected_ticker}")
    skew_snapshot = latest_df[latest_df["expiry"] == selected_expiry_iv]
    skew_pivot = skew_snapshot.pivot_table(index="strike", columns="option_type", values="implied_volatility")
    if skew_pivot.empty:
        st.info("最新一班没有这个到期日的数据。")
    else:
        option_type_colors = {"call": theme.PRIMARY, "put": theme.ACCENT}
        st.line_chart(skew_pivot, color=[option_type_colors[c] for c in skew_pivot.columns])
    with st.expander("ℹ️ 怎么读"):
        st.write("曲线形状说明市场把哪些行权价定价得更贵(IV 更高)。低行权价一侧的 put 明显更高(put skew)= 下行保护需求高, 这是指数的常态。")
    st.caption("单份合约的 IV 历史与其余 greeks 在「单合约」视图。")

if active_view == "单合约":
    st.subheader("单合约: 价格与 greeks 随时间")
    if not get_tracked().empty:
        st.caption("钉住的合约(点一下显示在下面):")
        for _, trow in get_tracked().iterrows():
            col_a, col_b = st.columns([5, 1])
            label = f"{format_date(trow['expiry'])}  行权价 {trow['strike']:g}  {trow['option_type']}"
            if col_a.button(label, key=f"select_tracked_{trow['id']}", use_container_width=True):
                st.session_state[f"opt_expiry_{selected_ticker}"] = trow["expiry"]
                st.session_state[f"opt_strike_{selected_ticker}"] = trow["strike"]
                st.session_state[f"opt_type_{selected_ticker}"] = trow["option_type"]
                st.rerun()
            if col_b.button("✕", key=f"untrack_{trow['id']}"):
                db.remove_tracked_contract(conn, trow["id"])
                st.rerun()
        st.divider()

    expired = db.get_expired_contracts(conn, selected_ticker, source=page_source)
    expired_expiries = []
    if not expired.empty:
        if st.checkbox(f"包含已到期合约({len(expired)} 份有历史)", key=f"show_expired_{selected_ticker}",
                       help="已到期的合约不再出现在最新一班里, 所以默认不在下拉里; 它们的历史都在。"):
            expired_expiries = sorted(pd.Timestamp(e) for e in expired["expiry"].unique())
    live_expiries = [pd.Timestamp(e) for e in expiries]
    all_expiries = sorted(set(live_expiries) | set(expired_expiries))

    def _format_expiry_option(expiry) -> str:
        label = format_date(expiry)
        return label if expiry in live_expiries else f"{label}  ⏳ 已到期"

    col1, col2, col3 = st.columns(3)
    _drop_stale_choice(f"opt_expiry_{selected_ticker}", all_expiries)
    opt_expiry = col1.selectbox("到期日", all_expiries, format_func=_format_expiry_option, key=f"opt_expiry_{selected_ticker}")
    live_strikes = set(latest_df[latest_df["expiry"] == opt_expiry]["strike"].unique())
    expired_strikes = set()
    if expired_expiries:
        expired_strikes = set(expired[expired["expiry"] == opt_expiry]["strike"].unique())
    opt_strikes = sorted(live_strikes | expired_strikes)
    _drop_stale_choice(f"opt_strike_{selected_ticker}", opt_strikes)
    opt_strike = col2.selectbox("行权价", opt_strikes, key=f"opt_strike_{selected_ticker}")
    available_types = sorted(
        latest_df[(latest_df["expiry"] == opt_expiry) & (latest_df["strike"] == opt_strike)]["option_type"].unique()
    )
    if not available_types and expired_expiries:
        available_types = sorted(expired[(expired["expiry"] == opt_expiry) & (expired["strike"] == opt_strike)]["option_type"].unique())
    available_types = available_types or ["call", "put"]
    _drop_stale_choice(f"opt_type_{selected_ticker}", available_types)
    opt_type = col3.selectbox("类型", available_types, key=f"opt_type_{selected_ticker}")

    is_expired = pd.Timestamp(opt_expiry) < pd.Timestamp(dt.date.today())
    contract_df = with_our_iv(db.get_contract_history(
        conn, selected_ticker, opt_expiry, opt_strike, opt_type, days=None if is_expired else history_days, source=page_source,
    ))
    if is_expired and not contract_df.empty:
        first, last = contract_df["collected_at"].min(), contract_df["collected_at"].max()
        st.caption(f"⏳ **已到期合约** —— {format_date(opt_expiry)} 到期。存下的历史从 {format_date(first)} 到 {format_date(last)}。")
    render_option_detail(conn, contract_df, selected_ticker, get_tracked(), opt_expiry, opt_strike, opt_type, key_prefix="opt")

if active_view == "筛选器":
    st.subheader(f"筛选器: {selected_ticker}")
    st.caption("最新一班的切片(不是历史): 全部合约带 greeks 与 DTE。勾一行打开与「单合约」相同的图。")
    screener = metrics.screener_table(latest_df)
    now = pd.Timestamp.utcnow()
    expired_since = pd.Series(dtype=bool)
    if not screener.empty:
        expired_since = screener["expiry"].map(lambda e: metrics.years_to_expiry(e, now) <= 0)
    show_expired = False
    if expired_since.any():
        stale_days = int(metrics.years_to_expiry(latest_date, now) * -365)
        show_expired = st.checkbox(
            f"包含这一班之后已到期的 {int(expired_since.sum())} 份合约(这一班是 {stale_days} 天前的)",
            key=f"screener_show_expired_{selected_ticker}", help="它们的 greeks 与 DTE 是采集当时的。",
        )
    if not show_expired and not screener.empty:
        screener = screener[~expired_since].reset_index(drop=True)

    if screener.empty:
        st.info("没有可筛的数据。")
    else:
        FILTER_SPECS = [
            ("last_price", "合约价"), ("strike", "行权价"), ("dte", "DTE(天)"), ("open_interest", "未平仓量"),
            ("implied_volatility", "IV"), ("delta", "Delta"), ("gamma", "Gamma"), ("theta", "Theta"),
            ("vega", "Vega"), ("rho", "Rho"), ("vanna", "Vanna"), ("charm", "Charm"),
        ]
        INT_FILTER_COLUMNS = {"dte", "open_interest"}
        with st.expander("🔍 区间筛选", expanded=True):
            filter_cols = st.columns(3)
            mask = pd.Series(True, index=screener.index)
            for i, (col_name, label) in enumerate(FILTER_SPECS):
                series = screener[col_name].dropna()
                if series.empty:
                    continue
                col_min, col_max = float(series.min()), float(series.max())
                target = filter_cols[i % 3]
                if col_min == col_max:
                    target.caption(f"{label}: {col_min:g}(只有一个值)")
                    continue
                target.caption(label)
                sub_left, sub_right = target.columns(2)
                if col_name in INT_FILTER_COLUMNS:
                    col_min, col_max = int(col_min), int(col_max)
                    selected_min = sub_left.number_input("从", min_value=col_min, max_value=col_max, value=col_min, step=1,
                                                         key=f"screener_filter_{selected_ticker}_{col_name}_min")
                    selected_max = sub_right.number_input("到", min_value=col_min, max_value=col_max, value=col_max, step=1,
                                                          key=f"screener_filter_{selected_ticker}_{col_name}_max")
                else:
                    step = max((col_max - col_min) / 100, 1e-6)
                    selected_min = sub_left.number_input("从", min_value=col_min, max_value=col_max, value=col_min, step=step,
                                                         format="%.4f", key=f"screener_filter_{selected_ticker}_{col_name}_min")
                    selected_max = sub_right.number_input("到", min_value=col_min, max_value=col_max, value=col_max, step=step,
                                                          format="%.4f", key=f"screener_filter_{selected_ticker}_{col_name}_max")
                mask &= screener[col_name].between(selected_min, selected_max)
        filtered = screener[mask].reset_index(drop=True)
        st.caption(f"显示 {len(filtered)} / {len(screener)} 份合约")
        selected_contract_key = f"screener_selected_contract_{selected_ticker}"
        scroll_target_key = f"screener_scroll_target_{selected_ticker}"
        selected_contract = st.session_state.get(selected_contract_key)
        if filtered.empty:
            st.info("没有合约落在所选区间内。")
        else:
            display = filtered.copy()
            display["expiry"] = display["expiry"].map(format_date)
            display.insert(0, "详情", pd.array([
                (row.expiry, row.strike, row.option_type) == selected_contract for row in filtered.itertuples()
            ], dtype=bool))
            edited = st.data_editor(
                display, use_container_width=True, hide_index=True,
                disabled=[c for c in display.columns if c != "详情"],
                column_config={"详情": st.column_config.CheckboxColumn("详情")},
                key=f"screener_table_{selected_ticker}",
            )
            checked = filtered[edited["详情"]]
            if checked.empty:
                new_contract = None
            else:
                picked_row = checked.iloc[-1]
                new_contract = (picked_row["expiry"], picked_row["strike"], picked_row["option_type"])
            if new_contract != selected_contract:
                st.session_state[selected_contract_key] = new_contract
                st.rerun()
        if selected_contract is not None:
            picked = filtered[
                (filtered["expiry"] == selected_contract[0]) & (filtered["strike"] == selected_contract[1])
                & (filtered["option_type"] == selected_contract[2])
            ]
            if not picked.empty:
                picked = picked.iloc[0]
                st.divider()
                st.subheader(f"📌 合约详情: {format_date(picked['expiry'])} 行权价 {picked['strike']:g} {picked['option_type']}")
                render_option_detail(
                    conn,
                    with_our_iv(db.get_contract_history(
                        conn, selected_ticker, picked["expiry"], picked["strike"], picked["option_type"],
                        days=history_days, source=page_source,
                    )),
                    selected_ticker, get_tracked(), picked["expiry"], picked["strike"], picked["option_type"], key_prefix="screener",
                )
                is_new_scroll_target = st.session_state.get(scroll_target_key) != selected_contract
                st.session_state[scroll_target_key] = selected_contract
                if is_new_scroll_target:
                    components.html(
                        """<script>
                        const heading = Array.from(window.parent.document.querySelectorAll('h3'))
                            .find(el => el.textContent.includes('合约详情'));
                        if (heading) { heading.scrollIntoView({behavior: 'smooth', block: 'start'}); }
                        </script>""",
                        height=0,
                    )

if active_view == "异常成交":
    st.subheader("异常成交(最新一班)")
    flagged = metrics.unusual_activity(latest_df, stats=db.get_volume_stats(conn, selected_ticker, source=page_source))
    st.caption(f"命中 {len(flagged)} 份合约")
    st.dataframe(flagged, use_container_width=True)
    with st.expander("ℹ️ 怎么读"):
        st.write(
            f"今天的成交量相对这份合约自己的历史显著偏高(z 分数 > {config.UNUSUAL_Z_THRESHOLD})才入榜, 不是统一倍数; "
            f"成交量低于 {config.UNUSUAL_MIN_VOLUME} 的永远不入榜。历史不够的用 成交量 > 2×OI 的粗判。按 z 分数排序。"
            "不是内幕信号 —— 一笔大单可能是别处头寸的对冲。基线每个日历日只取最后一班。"
        )

if active_view == "OI 变化":
    st.subheader("未平仓量变化(最新交易日 vs 上一交易日)")
    delta = metrics.oi_delta(db.get_snapshots_at(
        conn, selected_ticker,
        db.get_collection_moments(conn, selected_ticker, days=history_days, per_day=True, source=page_source)[:2],
        source=page_source,
    ))
    if delta.empty:
        st.info("至少要两个不同日历日的数据才能算 OI 变化。")
    else:
        st.dataframe(delta, use_container_width=True)
        with st.expander("ℹ️ 怎么读"):
            st.write(
                "`open_interest` 是最新一天的值(给个量级); `oi_delta` 是带符号的绝对变化(正 = 新开仓, 负 = 平仓); "
                "`oi_delta_pct` 是相对前值的百分比(前值为 0 则空)。按绝对变化的大小排序, 不分正负 —— 大的变动最常造出新的对冲流位置。"
                "OI 盘中基本不更新, 所以比的是两个不同日历日各自最后一班。"
            )

st.markdown(
    '<div class="gg-foot">'
    "<p>口径: 本页数据来自 Cboe 期权链(延迟 15 分钟, 不是实时报价), 由 morning-bites 每个交易日三班(09:00 / 12:35 / 16:20 美东)归档后回放, "
    "本页自己不向任何上游发请求; 时刻是 Cboe 给那份链盖的报价时刻, 已折成美东。GEX 正负号出自「Call 记正、Put 记负」的朴素做市商符号假设, "
    "未按持仓成本或逐笔成交方向校正, 可能与做市商真实净头寸有出入; 与 SpotGamma 等专业模型相比, 算法与数据源都不同, 量级仅供参考。</p>"
    f"<p>单位与纳入范围: 本页所有 GEX 读数的单位都是<b>{GEX_UNIT}</b>(gamma × 未平仓量 × 100 × 现价² × 0.01), B = 十亿美元、M = 百万美元, "
    "与晨刊「盘前关键位」和静态 Gamma 页同一单位; 与「现价每变动 $1 的美元 gamma」差一个现价因子, 不可互换。gamma 由 Black-Scholes 用 Cboe 报价 IV 反算"
    "(晨刊用 Cboe 厂商 gamma, 两者接近但不相等); 热图 / 状态句只看最近的若干到期日(各处写明), 晨刊纳入全部未到期到期日。"
    "SPX 含 SPXW: 同到期日同行权价的两者在入库时合并(OI、成交量相加)。已到期合约不计。</p>"
    "<p>墙与翻转位: 本页「Call 墙 / Put 墙」= 各侧未平仓量最大的行权价, 「插值翻转价」= 离现价最近的累计 GEX 穿零点在相邻两档间线性插值出的价格; "
    "晨刊「Call 墙 / Put 墙」= signed GEX 的最大 / 最小档, 「累计穿零档」= 现价 ±15% 带内按行权价升序累加第一次由负转非负的<b>行权价</b>(不插值)。"
    "两套都不是 SpotGamma 的 Zero Gamma(那是在一系列假设现价上重算整条链)。四个数各标各的口径, 不可互换, 也别拿一边去对账另一边。</p>"
    "<p>不保证: Call/Put 墙<b>不是自动的顶或底</b>, 价格穿过它们也不保证波动就此扩大; 正 / 负 GEX 说的是对冲流的<b>倾向</b>, 不是必然, 更<b>不预测方向</b>。</p>"
    "</div>",
    unsafe_allow_html=True,
)
