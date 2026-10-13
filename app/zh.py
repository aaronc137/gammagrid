"""morning-bites: 中文界面 — 在显示那一刻翻译, 上游文件里的英文一字不动.

为什么是一层而不是逐句改: 这个 fork 要一直合并上游(10-12 一次进来 25 个提交,
大半是在改 dashboard.py 的说明文字)。把三百多句英文改成 `t("...")`, 以后每次合并
都是几百处手工解冲突; 挂在 Streamlit 的组件类上翻, dashboard.py 只多四行。

怎么翻(`tr`): 整句查表 → 句型模板(正则, 捕获的片段递归再翻) → 原样返回。
HTML 只翻标签之间的文字与 title 提示, 样式与标签不碰。查不到就原样显示英文,
所以上游新加一句不会把页面弄坏, 只会漏翻 —— tests/zh_check.py 负责把漏翻找出来。

不翻的东西, 有意的: 下拉框/切换钮的「值」(视图名、采集间隔、call/put 都是逻辑键,
只翻 format_func 的显示); 数据库里存的英文(采集日志的 status/error_message);
表格列的真名(改用列配置的显示标签, 读回 data_editor 的代码照旧按英文列名取)。

默认中文; 右上角「中文 / EN」切换, 写进网址 ?lang=en, 刷新与分享都保留。
"""

from __future__ import annotations

import functools
import re

import streamlit as st
import streamlit.components.v1 as components
from streamlit.delta_generator import DeltaGenerator

from app import zh_notes, zh_text

LANG_KEY = "gg_lang"
_LAST_KEY = "_gg_lang_last"


# --- 当前语言 ------------------------------------------------------------------


def lang() -> str:
    """"zh" 或 "en"。不在页面渲染里(单元测试、worker)一律 "en": 那些地方的字符串
    是逻辑与日志, 不是给人读的界面。"""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx() is None:
            return "en"
        value = st.session_state.get(LANG_KEY, "zh")
    except Exception:  # noqa: BLE001 — 拿不到会话就是不在页面里
        return "en"
    return "en" if value == "en" else "zh"


# --- 翻译 ----------------------------------------------------------------------

_TEMPLATES = [(re.compile(pattern, re.S), zh) for pattern, zh in zh_text.TEMPLATES]
_HTML_TEXT = re.compile(r">([^<>]+)<")
_HTML_TITLE = re.compile(r'title="([^"]*)"')


@functools.lru_cache(maxsize=8192)
def translate(text: str) -> str:
    """英文 → 中文, 与语言无关(调用方先看 lang)。查不到返回原文。"""
    stripped = text.strip()
    if not stripped or stripped.startswith("<style") or not re.search(r"[A-Za-z]", stripped):
        return text
    head, tail = text[: len(text) - len(text.lstrip())], text[len(text.rstrip()):]
    hit = zh_text.CATALOG.get(stripped)
    if hit is None:
        for pattern, zh in _TEMPLATES:
            match = pattern.fullmatch(stripped)
            if match:
                hit = zh.format(*(translate(g) if g else "" for g in match.groups()))
                break
    if hit is not None:
        hit = _tidy(hit)
    elif "<" in stripped and ">" in stripped:
        hit = _HTML_TEXT.sub(lambda m: ">" + translate(m.group(1)) + "<", stripped)
        hit = _HTML_TITLE.sub(lambda m: f'title="{translate(m.group(1))}"', hit)
    return text if hit is None else head + hit + tail


_CJK = "一-鿿「」『』）"
_HALF = r"[,;:?!()]"
_FULLWIDTH = str.maketrans(",;:?!()", "，；：？！（）")


def _tidy(text: str) -> str:
    """译文排版统一(三个译者的半角 / 全角习惯不同): 挨着汉字的半角标点换全角并吃掉
    其后的空格, 一对括号有一边成了全角另一边跟着换。数字、时间、网址、代码两边都
    不是汉字, 不受影响。"""
    text = re.sub(rf"(?<=[{_CJK}])({_HALF}) ?", lambda m: m.group(1).translate(_FULLWIDTH), text)
    text = re.sub(rf"({_HALF}) ?(?=[{_CJK}])", lambda m: m.group(1).translate(_FULLWIDTH), text)
    text = re.sub(r"(?<=[，；：。、！？]) +", "", text)
    text = re.sub(rf"(?<=[{_CJK}，。；：）])\n[ \t]*(?=[{_CJK}（])", "", text)  # 源码里折行, 渲染成空格
    text = re.sub(r" *—— *", "——", text)
    text = re.sub(rf"(?<=[。，；：！？]\*\*) +(?=[{_CJK}])", "", text)
    chars, stack = list(text), []
    for i, ch in enumerate(chars):
        if ch in "(（":
            stack.append(i)
        elif ch in ")）" and stack:
            j = stack.pop()
            if "（" in (chars[j], ch) or ch == "）":
                chars[j], chars[i] = "（", "）"
    return "".join(chars)


def tr(value):
    """页面上要显示的一个值: 字符串且当前是中文才翻, 其余原样。"""
    if isinstance(value, str) and lang() == "zh":
        return translate(value)
    return value


# --- 挂到 Streamlit 上 -----------------------------------------------------------

# 第一个位置参数是给人读的文字的方法(标签或正文)。
_FIRST_ARG = {
    "markdown", "caption", "subheader", "header", "title", "text", "info", "warning",
    "error", "success", "toast", "expander", "popover", "button", "link_button",
    "download_button", "checkbox", "toggle", "selectbox", "radio", "multiselect",
    "select_slider", "segmented_control", "pills", "slider", "number_input",
    "text_input", "text_area", "date_input", "time_input", "metric", "form_submit_button",
}
_TEXT_KWARGS = ("label", "body", "help", "placeholder", "format")
_CHOICE = {"selectbox", "radio", "multiselect", "select_slider", "segmented_control", "pills"}
_TABLES = {"dataframe", "data_editor", "table"}
_SIMPLE_CHARTS = {"line_chart", "bar_chart", "area_chart", "scatter_chart"}


def _label_choices(kwargs: dict) -> None:
    shown = kwargs.get("format_func") or str
    kwargs["format_func"] = lambda option, shown=shown: tr(str(shown(option)))


def _column_labels(args: tuple, kwargs: dict) -> None:
    """表头换成中文, 列的真名不动: 写进列配置的显示标签。"""
    data = kwargs.get("data", args[0] if args else None)
    frame = getattr(data, "data", data)  # pandas Styler 的底表
    columns = list(getattr(frame, "columns", []))
    config = dict(kwargs.get("column_config") or {})
    for name in columns:
        if not isinstance(name, str):
            continue
        entry = config.get(name)
        if entry is None:
            if tr(name) != name:
                config[name] = st.column_config.Column(label=tr(name))
        elif isinstance(entry, dict):
            entry = dict(entry)
            entry["label"] = tr(entry.get("label") or name)
            if entry.get("help"):
                entry["help"] = tr(entry["help"])
            config[name] = entry
        elif isinstance(entry, str):
            config[name] = tr(entry)
    index_name = getattr(getattr(frame, "index", None), "name", None)
    if isinstance(index_name, str) and "_index" not in config and tr(index_name) != index_name:
        config["_index"] = st.column_config.Column(label=tr(index_name))
    if config:
        kwargs["column_config"] = config


def _chart_frame(args: tuple, kwargs: dict) -> tuple:
    """简单图表的图例、轴题都取自列名与索引名: 画之前换一份改了名的副本。"""
    data = kwargs.pop("data", args[0] if args else None)
    rest = args[1:] if args else ()
    if hasattr(data, "rename_axis"):
        if hasattr(data, "columns"):
            data = data.rename(columns=lambda c: tr(c) if isinstance(c, str) else c)
        elif isinstance(getattr(data, "name", None), str):
            data = data.rename(tr(data.name))
        if isinstance(data.index.name, str):
            data = data.rename_axis(tr(data.index.name))
    for axis in ("x", "y"):
        value = kwargs.get(axis)
        if isinstance(value, str):
            kwargs[axis] = tr(value)
        elif isinstance(value, (list, tuple)):
            kwargs[axis] = [tr(v) for v in value]
    for axis in ("x_label", "y_label"):
        if isinstance(kwargs.get(axis), str):
            kwargs[axis] = tr(kwargs[axis])
    return (data, *rest)


def _walk_spec(node, plotly: bool):
    """图表规格(Vega-Lite / Plotly 的 dict)里给人读的字段翻掉, 数据不碰。"""
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if key in ("title", "text", "name", "hovertemplate") and isinstance(value, str):
                out[key] = tr(value)
            elif key in ("title", "text", "ticktext") and isinstance(value, list):
                out[key] = [tr(v) for v in value]
            elif plotly and key == "x" and isinstance(value, list) and all(
                isinstance(v, str) and v in zh_text.CATALOG for v in value
            ):
                out[key] = [tr(v) for v in value]  # 瀑布图的类目轴
            elif key in ("data", "datasets", "values", "z", "y", "customdata"):
                out[key] = value
            else:
                out[key] = _walk_spec(value, plotly)
        return out
    if isinstance(node, list):
        return [_walk_spec(v, plotly) for v in node]
    return node


def _wrap(name: str, original):
    def wrapper(self, *args, **kwargs):
        if lang() != "zh":
            return original(self, *args, **kwargs)
        if name in _FIRST_ARG and args:
            args = (tr(args[0]), *args[1:])
        if name == "write":
            args = tuple(tr(a) for a in args)
        if name == "metric":
            args = tuple(tr(a) for a in args)
            for key in ("value", "delta"):
                if key in kwargs:
                    kwargs[key] = tr(kwargs[key])
        for key in _TEXT_KWARGS:
            if key in kwargs:
                kwargs[key] = tr(kwargs[key])
        if name == "radio" and kwargs.get("captions"):
            kwargs["captions"] = [tr(c) for c in kwargs["captions"]]
        if name in _CHOICE:
            _label_choices(kwargs)
        if name in _TABLES:
            _column_labels(args, kwargs)
        if name == "dataframe" and args and hasattr(args[0], "index") and hasattr(args[0], "rename"):
            # 只读表的行标签(如热力图上方转置出来的 net_gex 行)也译; data_editor 不碰,
            # 那里的行要原样读回。
            args = (args[0].rename(index=lambda v: tr(v) if isinstance(v, str) else v), *args[1:])
        if name in _SIMPLE_CHARTS:
            args = _chart_frame(args, kwargs)
        if name == "plotly_chart" and args:
            import plotly.graph_objects as go

            args = (go.Figure(_walk_spec(args[0].to_dict(), plotly=True)), *args[1:])
        if name == "altair_chart" and args:
            chart = args[0]
            args = (type(chart).from_dict(_walk_spec(chart.to_dict(), plotly=False)), *args[1:])
        return original(self, *args, **kwargs)

    wrapper.__wrapped__ = original
    return wrapper


def _html(original):
    def wrapper(html, *args, **kwargs):
        if lang() == "zh" and isinstance(html, str):
            for english, chinese in zh_text.EMBEDDED:
                html = html.replace(english, chinese)
        return original(html, *args, **kwargs)

    wrapper.__wrapped__ = original
    return wrapper


def _spinner(original):
    def wrapper(text="In progress...", *args, **kwargs):
        return original(tr(text), *args, **kwargs)

    wrapper.__wrapped__ = original
    return wrapper


def install() -> None:
    """挂一次, 进程内有效; 英文时每个包装直接转给原方法。"""
    if getattr(DeltaGenerator, "_gg_zh_installed", False):
        return
    names = _FIRST_ARG | _TABLES | _SIMPLE_CHARTS | {"write", "plotly_chart", "altair_chart"}
    for name in sorted(names):
        original = getattr(DeltaGenerator, name, None)
        if original is not None:
            setattr(DeltaGenerator, name, _wrap(name, original))
    main = st.markdown.__self__
    for name in sorted(names):
        if isinstance(getattr(st, name, None), type(st.markdown)):
            setattr(st, name, getattr(main, name))  # st.xxx 是导入时绑好的方法, 要重绑
    st.spinner = _spinner(st.spinner)
    components.html = _html(components.html)
    DeltaGenerator._gg_zh_installed = True


# --- 右上角切换 --------------------------------------------------------------------


def toggle() -> None:
    """「中文 / EN」, 钉在页面右上角; 选择写进 ?lang=, 默认中文时网址不带参数。"""
    state = st.session_state
    if LANG_KEY not in state:
        state[LANG_KEY] = "en" if st.query_params.get("lang") == "en" else "zh"
    elif state[LANG_KEY] is None:  # 分段控件再点一次会取消选中, 那不是「换语言」
        state[LANG_KEY] = state.get(_LAST_KEY, "zh")
    state[_LAST_KEY] = state[LANG_KEY]
    with st.container(key="gg-lang"):
        st.segmented_control(
            "Language", ["zh", "en"], key=LANG_KEY,
            format_func={"zh": "中文", "en": "EN"}.get, label_visibility="collapsed",
        )
    if state[LANG_KEY] == "en":
        st.query_params["lang"] = "en"
    elif "lang" in st.query_params:
        del st.query_params["lang"]
    st.markdown(zh_text.CSS_TOGGLE + (zh_text.CSS_ZH if lang() == "zh" else ""),
                unsafe_allow_html=True)


# --- 指南补充说明 --------------------------------------------------------------------


def note(key: str) -> None:
    """中文时在这里放一块补充说明(app/zh_notes.py); 英文时什么也不画。"""
    if lang() != "zh" or key not in zh_notes.NOTES:
        return
    title, body = (_tidy(part) for part in zh_notes.NOTES[key])
    # 天气卡片下用弹出框而不是展开块: 卡片在每个视图上方, 多一个展开块会让
    # tests/render_views.py 以为「有说明却没挂 Guide 链接」。
    container = st.popover(title) if key == "weather" else st.expander(title)
    with container:
        st.markdown(body, unsafe_allow_html=True)


class _AfterBlock:
    """`with howto(view):` 的说明块关上之后, 紧跟着放这个视图的补充说明。
    放在说明块之后而不是之前: 渲染检查要求 Guide 链接紧贴在说明块前面。"""

    def __init__(self, block, key: str):
        self._block, self._key = block, key

    def __enter__(self):
        return self._block.__enter__()

    def __exit__(self, *exc):
        result = self._block.__exit__(*exc)
        if exc[0] is None:
            note(self._key)
        return result


def after(block, key: str):
    return _AfterBlock(block, key)
