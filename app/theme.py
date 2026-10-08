"""配色与 Streamlit 画不出来的几个组件 —— morning-bites 定制版。

颜色是 morning-bites `templates/_theme_head.html.j2` 的暗色 token(2026-09-08 那组, 实施时现场抄, 不凭记忆):
paper #0F1114 · panel #161A1F · ink #E6E4DC · body #C4C2BA · muted #AAA9A2 · graphite #93938D · faint #5C5D59 ·
rule #2C3138 · wash #272C32 · up #3DBA7A · dn #F26B5E · seal #F0863A。
GEX 正负色按 morning-bites ADR 2026-09-07: 正(抑制)= --up 绿, 负(放大)= --dn 红; 上游的紫 / 绿语义照搬, 只换色值。
类名 gg-green / gg-purple 保留(上游模板与「较昨日」视图都用), 紫现在是红。

Modified for morning-bites, 2026-10-08. AGPL-3.0, 同本仓 LICENSE。
"""

from __future__ import annotations

# --- palette ---------------------------------------------------------------
PRIMARY = "#F26B5E"        # 放大 / 负 GEX(--dn)
PRIMARY_SOFT = "#F26B5E"
ACCENT = "#3DBA7A"         # 抑制 / 正 GEX(--up)
ACCENT_SOFT = "#3DBA7A"

BACKGROUND = "#0F1114"     # --paper
SURFACE = "#161A1F"        # --panel
SURFACE_2 = "#272C32"      # --wash
BORDER = "#2C3138"         # --rule
GRID = "#2C3138"

TEXT = "#E6E4DC"           # --ink
MUTED = "#AAA9A2"          # --muted
FAINT = "#93938D"          # --graphite(--faint #5C5D59 在 10px 小字上过不了 4.5:1, 见 morning-bites 那段注释)

ERROR = "#F26B5E"
WARNING = "#F0863A"        # --seal

# --- shape -----------------------------------------------------------------
RADIUS_PANEL = "4px"
RADIUS_BOX = "4px"
RADIUS_CONTROL = "3px"
SHADOW_PANEL = "none"

# --- type ------------------------------------------------------------------
TEXT_MICRO = "11px"
TEXT_BASE = "13px"
TEXT_LEAD = "16px"
TEXT_STRONG = "18px"
TEXT_HERO = "28px"

# morning-bites 的 --sans / --mono 字体栈, 无 webfont 下载。
FONT_UI = (
    "-apple-system, 'Helvetica Neue', Arial, 'PingFang SC', 'Hiragino Sans GB', "
    "'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif"
)
FONT_MONO = (
    "ui-monospace, 'SF Mono', Menlo, Consolas, 'Liberation Mono', 'PingFang SC', "
    "'Hiragino Sans GB', 'Noto Sans CJK SC', 'Microsoft YaHei', monospace"
)


def stylesheet() -> str:
    return f"""
<style>
  h1, h2, h3, h4, [data-testid="stHeading"] {{
    font-family: {FONT_UI} !important;
    letter-spacing: 0.01em;
  }}
  [data-testid="stSegmentedControl"] button {{
    border-radius: 999px !important;
    padding: 4px 14px !important;
  }}
  [data-testid="stMetricValue"],
  [data-testid="stDataFrame"],
  .gg-mono {{
    font-family: {FONT_MONO};
    font-variant-numeric: tabular-nums;
  }}

  /* 状态句面板与晨刊口径条: 同一形状, 一个带图标一个不带。 */
  .gg-weather, .gg-mb {{
    display: flex;
    align-items: center;
    gap: 18px;
    flex-wrap: wrap;
    border: 1px solid {BORDER};
    border-radius: {RADIUS_PANEL};
    background: {SURFACE};
    padding: 14px 18px;
    margin-bottom: 0.6rem;
  }}
  .gg-mb {{ border-style: dashed; }}
  .gg-weather-words, .gg-mb-words {{ flex: 1 1 260px; min-width: 0; }}
  .gg-weather-label, .gg-mb-label {{
    font-size: {TEXT_LEAD};
    font-weight: 700;
    color: {TEXT};
    letter-spacing: 0.02em;
  }}
  .gg-weather-scope {{
    font-weight: 400;
    color: {FAINT};
    font-size: {TEXT_MICRO};
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }}
  .gg-weather-sentence {{
    color: {MUTED};
    font-size: {TEXT_BASE};
    margin-top: 2px;
  }}
  .gg-levels {{
    display: flex;
    gap: 22px;
    flex-wrap: wrap;
    margin: 0;
    font-variant-numeric: tabular-nums;
  }}
  .gg-levels dt {{
    font-size: {TEXT_MICRO};
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: {FAINT};
  }}
  .gg-levels dd {{
    margin: 0;
    font-family: {FONT_MONO};
    font-size: {TEXT_STRONG};
    font-weight: 700;
    color: {TEXT};
  }}
  .gg-green {{ color: {ACCENT_SOFT}; }}
  .gg-purple {{ color: {PRIMARY_SOFT}; }}

  .gg-ladder {{
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
    font-size: {TEXT_BASE};
  }}
  .gg-ladder th:first-child, .gg-ladder td:first-child {{ width: 34%; }}
  .gg-ladder th:nth-child(2), .gg-ladder td:nth-child(2),
  .gg-ladder th:nth-child(3), .gg-ladder td:nth-child(3) {{ width: 18%; }}
  .gg-ladder th {{
    text-align: left;
    font-size: {TEXT_MICRO};
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: {FAINT};
    font-weight: 600;
    padding: 0 12px 6px 0;
  }}
  .gg-ladder td {{
    padding: 7px 12px 7px 0;
    border-top: 1px solid {GRID};
    vertical-align: baseline;
  }}
  .gg-ladder .gg-num {{
    font-family: {FONT_MONO};
    font-variant-numeric: tabular-nums;
  }}
  .gg-ladder .gg-before {{ color: {MUTED}; }}
  .gg-ladder .gg-note {{
    display: block;
    color: {FAINT};
    font-size: {TEXT_MICRO};
  }}

  /* 页脚口径四段(措辞搬自 morning-bites board_gex.html.j2)。 */
  .gg-foot {{
    margin-top: 2rem;
    padding-top: 0.8rem;
    border-top: 1px solid {BORDER};
    color: {MUTED};
    font-size: {TEXT_MICRO};
    line-height: 1.6;
  }}
  .gg-foot p {{ margin: 0 0 0.5rem; }}
  .gg-foot b {{ color: {TEXT}; font-weight: 600; }}
</style>
"""
