"""Gamma 数字旁边的那几句话 —— morning-bites 中文版。

`metrics.gamma_weather` 回答「状态是什么」, 这里回答「怎么说」。两处要说(状态句面板与「较昨日」), 一处措辞。

措辞规矩(morning-bites ADR 2026-09-10 DIX 第三节): 正 / 负 GEX 只说对冲流「倾向抑制 / 放大」, **不写「负了波动会高」**。

Modified for morning-bites, 2026-10-08. AGPL-3.0, 同本仓 LICENSE。
"""

from __future__ import annotations

import pandas as pd

from app import metrics, theme

WEATHER_WORDS = {
    metrics.WEATHER_CLEAR: ("晴", "正 gamma, 翻转位离得远 —— 对冲流倾向抑制波动。"),
    metrics.WEATHER_FAIR: ("多云", "正 gamma, 但翻转位在一天的波幅之内 —— 抑制未必站得住。"),
    metrics.WEATHER_UNSETTLED: ("不定", "现价贴着翻转位 —— 状态随时可能翻面。"),
    metrics.WEATHER_RAIN: ("阵雨", "负 gamma, 但翻转位不远 —— 眼下对冲流倾向放大波动。"),
    metrics.WEATHER_STORM: ("风暴", "负 gamma 且附近没有边界 —— 对冲流倾向放大波动。"),
}


def per_pct(value: float | None, spot: float | None) -> float | None:
    """gammagrid 的 GEX 是每 $1 的美元 gamma; 本站全站用每 1%(× 现价 × 0.01)。只在显示处换, 库里不动。"""
    if value is None or spot is None:
        return None
    return float(value) * float(spot) / 100


def format_gex(value: float | None, signed: bool = True) -> str:
    """按量级自选单位: B / M / K。"""
    if value is None:
        return "—"
    magnitude = abs(value)
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if magnitude >= limit:
            return f"{value / limit:{'+' if signed else ''}.2f}{suffix}"
    return f"{value:{'+' if signed else ''}.0f}"


def describe(weather: dict, latest_moment=None) -> dict:
    label, sentence = WEATHER_WORDS[weather["state"]]
    scope = ""
    if weather.get("expiry_count") and weather.get("horizon_dte") is not None:
        scope = f"未来 {int(weather['horizon_dte'])} 天 · {int(weather['expiry_count'])} 个到期日"
    if weather["gamma_flip"] is None:
        sentence = "这条链在行权价范围内没有翻转位, 只知道 gamma 的符号 —— " + (
            "正, 对冲流倾向抑制波动。" if weather["net_gex"] >= 0 else "负, 对冲流倾向放大波动。"
        )
    earlier = latest_moment is not None and pd.Timestamp(weather["collected_at"]) != pd.Timestamp(latest_moment)
    return {"label": label, "sentence": sentence, "scope": scope, "from_earlier_moment": bool(earlier)}


# 五种状态的线描图标: 绿 = 抑制, 红 = 放大(本站 --up / --dn, ADR 2026-09-07 gex 正负色)。
_ART = {
    metrics.WEATHER_CLEAR: (
        f'<circle cx="22" cy="22" r="9" fill="{theme.ACCENT}"/>'
        f'<g stroke="{theme.ACCENT}" stroke-width="2.6" stroke-linecap="round">'
        '<line x1="22" y1="3" x2="22" y2="8"/><line x1="22" y1="36" x2="22" y2="41"/>'
        '<line x1="3" y1="22" x2="8" y2="22"/><line x1="36" y1="22" x2="41" y2="22"/>'
        '<line x1="8.5" y1="8.5" x2="12" y2="12"/><line x1="32" y1="32" x2="35.5" y2="35.5"/>'
        '<line x1="8.5" y1="35.5" x2="12" y2="32"/><line x1="32" y1="12" x2="35.5" y2="8.5"/>'
        "</g>"
    ),
    metrics.WEATHER_FAIR: (
        f'<circle cx="15" cy="13" r="7" fill="{theme.ACCENT}"/>'
        f'<g stroke="{theme.ACCENT}" stroke-width="2.2" stroke-linecap="round">'
        '<line x1="15" y1="1" x2="15" y2="4"/><line x1="3" y1="13" x2="6" y2="13"/>'
        '<line x1="6" y1="4" x2="8" y2="6"/></g>'
        f'<rect x="12" y="25" width="28" height="12" rx="6" fill="{theme.FAINT}"/>'
        f'<rect x="17" y="18" width="15" height="15" rx="7.5" fill="{theme.FAINT}"/>'
        f'<rect x="28" y="21" width="12" height="12" rx="6" fill="{theme.FAINT}"/>'
    ),
    metrics.WEATHER_UNSETTLED: (
        f'<circle cx="11" cy="10" r="6" fill="{theme.ACCENT}"/>'
        f'<rect x="7" y="17" width="30" height="12" rx="6" fill="{theme.FAINT}"/>'
        f'<rect x="13" y="10" width="16" height="16" rx="8" fill="{theme.FAINT}"/>'
        f'<rect x="25" y="13" width="12" height="12" rx="6" fill="{theme.FAINT}"/>'
        f'<polygon points="28,30 21,30 25,36 21,36 31,44 27,37 32,37" fill="{theme.PRIMARY}"/>'
    ),
    metrics.WEATHER_RAIN: (
        f'<rect x="7" y="15" width="30" height="12" rx="6" fill="{theme.FAINT}"/>'
        f'<rect x="13" y="8" width="16" height="16" rx="8" fill="{theme.FAINT}"/>'
        f'<rect x="25" y="11" width="12" height="12" rx="6" fill="{theme.FAINT}"/>'
        f'<g stroke="{theme.PRIMARY}" stroke-width="3.4" stroke-linecap="round">'
        '<line x1="16" y1="31" x2="13" y2="40"/><line x1="24" y1="31" x2="21" y2="40"/>'
        '<line x1="32" y1="31" x2="29" y2="40"/></g>'
    ),
    metrics.WEATHER_STORM: (
        f'<rect x="7" y="13" width="30" height="12" rx="6" fill="{theme.FAINT}"/>'
        f'<rect x="13" y="6" width="16" height="16" rx="8" fill="{theme.FAINT}"/>'
        f'<rect x="25" y="9" width="12" height="12" rx="6" fill="{theme.FAINT}"/>'
        f'<polygon points="25,27 14,27 21,35 15,35 29,44 24,36 30,36" fill="{theme.PRIMARY}"/>'
    ),
}


def _level(label: str, value: str, tone: str = "") -> str:
    classes = f' class="{tone}"' if tone else ""
    return f"<div><dt>{label}</dt><dd{classes}>{value}</dd></div>"


def panel(reading: dict, latest_moment=None) -> str:
    """视图切换上方的状态句面板。净 GEX 换成每 1% 再印, 逐处标口径。"""
    words = describe(reading, latest_moment=latest_moment)
    flip = reading.get("gamma_flip")
    spot = reading["underlying_price"]
    net = per_pct(reading["net_gex"], spot)
    levels = [
        _level("现价", f"{spot:,.2f}"),
        _level("净 GEX · 每 1%", format_gex(net), "gg-green" if reading["net_gex"] >= 0 else "gg-purple"),
    ]
    if reading.get("call_wall") is not None:
        levels.append(_level("Call 墙 · OI", f"{reading['call_wall']:,.2f}", "gg-green"))
    if reading.get("put_wall") is not None:
        levels.append(_level("Put 墙 · OI", f"{reading['put_wall']:,.2f}", "gg-purple"))
    levels.append(_level("插值翻转价", "—" if flip is None else f"{flip:,.2f}", ""))
    if flip is not None:
        levels.append(_level("距离", f"{reading['flip_distance_pct']:.1f}%"))
    art = _ART.get(reading["state"], "")
    scope = f" · {words['scope']}" if words["scope"] else ""
    stale = " · 来自比本页其余部分更早的一班" if words["from_earlier_moment"] else ""
    return (
        '<div class="gg-weather">'
        f'<svg width="44" height="44" viewBox="0 0 44 44" aria-hidden="true">{art}</svg>'
        '<div class="gg-weather-words">'
        f'<div class="gg-weather-label">{words["label"]}'
        f'<span class="gg-weather-scope"> · gammagrid 口径 · BS gamma{scope}{stale}</span></div>'
        f'<div class="gg-weather-sentence">{words["sentence"]}</div>'
        "</div>"
        f'<dl class="gg-levels">{"".join(levels)}</dl>'
        "</div>"
    )
