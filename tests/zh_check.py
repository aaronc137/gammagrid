"""morning-bites: 中文界面检查 —— 每个视图中英各渲染一遍, 中文下不许剩英文。

为什么按「渲染出来的字」查而不是按源码里的字符串字面量查: 页面上三分之一的句子是
运行时拼的(f-string、片段拼接、别的模块返回的句子), 字面量扫描看不见它们; 渲染后
从元素树里收字, 看到的就是读者看到的。代价是只覆盖夹具走得到的分支, 夹具走不到的
(冷却横幅、被拒的代码)靠 zh_text 里按源码写的条目, 并在下面 OFFLINE 里单独喂句子。

用法:
  python tests/zh_check.py          检查: 中文残留英文就退出 1(上游合并后必跑)
  python tests/zh_check.py --dump   列出英文模式下见到的所有文字(写译文的底稿)
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_views  # noqa: E402 — 复用它的夹具与清库(它在导入时已指向测试库)
from google.protobuf.json_format import MessageToDict  # noqa: E402

# 中文界面里允许原样出现的拉丁字母词: 术语缩写、希腊字母名、来源与品牌、夹具代码。
ALLOWED = {
    "gex", "iv", "oi", "dte", "rv", "atm", "otm", "itm", "pcr", "call", "calls", "put", "puts",
    "delta", "gamma", "theta", "vega", "rho", "vanna", "charm", "black", "scholes",
    "cboe", "yahoo", "yfinance", "finance", "gammagrid", "tradingview", "github",
    "utc", "edt", "est", "cet", "cest", "new", "york", "nyse", "spx", "spy", "qqq", "xsp",
    "ndx", "rut", "djx", "vix", "rendertest", "en", "etf", "etfs", "adr", "adrs", "occ",
    "max", "pain", "open", "interest", "http", "https", "www", "io", "guide", "com",
    "apple", "aapl", "asml", "sap", "shel", "nvo", "bud", "nvda", "vs", "ok", "b", "m", "k",
    # Streamlit 把多列折线图熔成 (index, color, value) 再画, 这两个是它内部的字段名,
    # 在 Python 侧够不着(列入后续: 改用 Altair 自己画才能换)
    "value", "color",
}
_TEXT_KEYS = {"body", "label", "help", "placeholder", "value", "delta", "text", "caption",
              "title", "name", "options", "captions", "formattedValue"}
_SPEC_KEYS = {"spec", "figure", "columns"}


def _strings(node, out):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in _SPEC_KEYS and isinstance(value, str) and value[:1] in "{[":
                try:
                    spec = json.loads(value)
                except ValueError:
                    continue
                if key == "figure":
                    _plotly_strings(spec, out)
                else:
                    _spec_strings(spec, out)
            elif key in _TEXT_KEYS and isinstance(value, str):
                out.append(value)
            elif key in _TEXT_KEYS and isinstance(value, list):
                out.extend(v for v in value if isinstance(v, str))
            else:
                _strings(value, out)
    elif isinstance(node, list):
        for value in node:
            _strings(value, out)


def _spec_strings(node, out):
    """Vega-Lite 规格与表格列配置里给人读的字段: 标题与表头。name 是内部标识, 不收。"""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("title", "label", "help") and isinstance(value, str):
                out.append(value)
            elif key == "title" and isinstance(value, list):
                out.extend(v for v in value if isinstance(v, str))
            elif key not in ("data", "datasets", "values"):
                _spec_strings(value, out)
    elif isinstance(node, list):
        for value in node:
            _spec_strings(value, out)


def _plotly_strings(figure, out):
    """Plotly 图: 每条轨迹的名字、类目轴文字、悬停模板, 以及版面里所有标题。"""
    for trace in (figure.get("data") or []) if isinstance(figure, dict) else []:
        for key in ("name", "hovertemplate"):
            if isinstance(trace.get(key), str):
                out.append(trace[key])
        x = trace.get("x")
        if isinstance(x, list) and x and all(isinstance(v, str) for v in x):
            out.extend(x)
    layout = figure.get("layout", {}) if isinstance(figure, dict) else {}

    def titles(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "title":
                    text = value.get("text") if isinstance(value, dict) else value
                    if isinstance(text, str):
                        out.append(text)
                elif key != "template":
                    titles(value)
        elif isinstance(node, list):
            for value in node:
                titles(value)

    titles(layout)


def page_texts(app) -> list[str]:
    out = []

    def walk(node):
        proto = getattr(node, "proto", None)
        if proto is not None:
            _strings(MessageToDict(proto), out)
        for child in (getattr(node, "children", None) or {}).values():
            walk(child)

    walk(app._tree)
    return out


def leftover_english(text: str) -> list[str]:
    """一句中文界面文字里没翻的英文词(去掉 HTML、行内代码、网址后)。"""
    if text.lstrip().startswith("<style") or re.fullmatch(r"(data-)?[0-9a-f]{32}", text):
        return []  # 样式表; 图表数据集的内部哈希名
    plain = re.sub(r"<[^>]+>", " ", text)
    plain = re.sub(r"`[^`]*`", " ", plain)
    plain = re.sub(r"https?://\S+|\S+@\S+", " ", plain)
    words = re.findall(r"[A-Za-z][A-Za-z'’]+", plain)
    return [w for w in words if w.lower() not in ALLOWED and not w.isupper()]


def render_all(language: str) -> dict[str, list[str]]:
    from streamlit.testing.v1 import AppTest

    seen = {}
    for view in render_views.VIEWS:
        app = AppTest.from_file(render_views.DASHBOARD, default_timeout=300)
        app.session_state["selected_ticker"] = "RENDERTEST"
        app.session_state["active_view"] = view
        app.session_state["gg_lang"] = language
        app.run()
        if app.exception:
            raise SystemExit(f"{language} {view}: {app.exception[0].value}")
        seen[view] = page_texts(app)
    return seen


def check_plotly_categories():
    """夹具只有一天历史, 画不出合约的瀑布图, 渲染那一遍看不见它的类目轴 —— 这里直接造一张。
    Plotly 把 x 存成 tuple, 只认 list 的话整条轴漏翻(10-13 在线上看到过)。"""
    import plotly.graph_objects as go

    from app import zh

    labels = ["Start", "Delta", "Gamma", "Vega", "Theta", "Residual", "End"]
    figure = go.Figure(go.Waterfall(x=labels, y=[1, 2, 3, 4, 5, 6, 0]))
    original = zh.lang
    zh.lang = lambda: "zh"
    try:
        walked = zh._walk_spec(figure.to_dict(), plotly=True)
    finally:
        zh.lang = original
    shown = list(walked["data"][0]["x"])
    assert "Start" not in shown and "Residual" not in shown, shown
    print("plotly category check passed (waterfall axis translated)")


def main():
    check_plotly_categories()
    dump = "--dump" in sys.argv
    from zoneinfo import ZoneInfo

    import pandas as pd

    from app import collector, db, viewtime

    with render_views.empty_database():
        viewtime.viewer_timezone = lambda: ZoneInfo("Europe/Prague")
        collector.fetch_price_history = lambda ticker, period="6mo": pd.DataFrame(
            {"close": [100.0 + (i % 7) - 3 for i in range(60)]},
            index=pd.date_range("2026-05-01", periods=60, freq="D"),
        )
        render_views.seed(db)
        if dump:
            seen = render_all("en")
            unique = []
            for texts in seen.values():
                for text in texts:
                    if text not in unique and re.search(r"[A-Za-z]{2}", text):
                        unique.append(text)
            print(json.dumps(unique, ensure_ascii=False, indent=1))
            return
        problems = {}
        for view, texts in render_all("zh").items():
            for text in texts:
                words = leftover_english(text)
                if words:
                    problems.setdefault(text, (view, words))
        english = render_all("en")
        cjk = [t for texts in english.values() for t in texts
               if re.search(r"[一-鿿]", t) and "中文" not in t]
    if cjk:
        print("ENGLISH MODE SHOWS CHINESE:")
        for text in cjk[:20]:
            print(f"  - {text[:120]!r}")
    if problems:
        print(f"UNTRANSLATED ({len(problems)}):")
        for text, (view, words) in problems.items():
            print(f"  [{view}] {', '.join(sorted(set(words))[:6])} :: {text[:160]!r}")
    if cjk or problems:
        raise SystemExit(1)
    print("zh check passed (every view, both languages, nothing left untranslated)")


if __name__ == "__main__":
    main()
