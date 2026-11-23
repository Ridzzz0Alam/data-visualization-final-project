"""Visual design: one dark 'UCL night' palette, CSS, and a chart-style hook.

Colour rules (same in every view):
  ACCENT (cyan)  = the focus team        GOLD = the second team in head-to-head
  GREY (slate)   = every other team      REF  = reference lines / neutral marks
"""

from __future__ import annotations

from bokeh.models import ColorBar
from bokeh.palettes import interp_palette

# --- Palette ---------------------------------------------------------------------
PAGE_BG = "#04072b"
CARD_BG = "#0a0f42"
CARD_BORDER = "#1b2580"
TEXT = "#e8ecff"
MUTED = "#97a1d6"
GRIDLINE = "#1c2668"
ACCENT = "#22d3ee"      # focus team
ACCENT_DIM = "#0e7490"  # focus team, older/background marks (3D skyline)
HEADER_GRADIENT = "linear-gradient(90deg, #1b30ff 0%, #0d1cb0 45%, #070c5c 100%)"
GOLD = "#fbbf24"        # second team (head-to-head) / favourite
GREY = "#475093"        # other teams
REF = "#7f8ac4"         # reference lines
# Smooth 256-step scale (5 colours alone give hard blocks). It stops at mid-blue, so
# white numbers stay readable on every cell.
HEAT_CMAP = list(interp_palette(["#0d1450", "#1e3a8a", "#2563eb", "#3b9be8"], 256))
FONT = "Outfit, 'Segoe UI', sans-serif"


def dark_style(plot, element) -> None:
    """Bokeh hook applied to every chart: dark card background, light text, soft grid."""
    fig = plot.state
    fig.background_fill_color = CARD_BG
    fig.border_fill_color = CARD_BG
    fig.outline_line_color = None
    fig.toolbar.autohide = True      # tools appear only when the mouse is over the chart
    fig.title.text_color = TEXT
    fig.title.text_font = FONT
    fig.title.text_font_size = "14px"
    fig.title.text_font_style = "bold"
    for ax in fig.axis:
        ax.axis_label_text_color = MUTED
        ax.axis_label_text_font = FONT
        ax.axis_label_text_font_style = "normal"
        ax.major_label_text_color = MUTED
        ax.major_label_text_font = FONT
        ax.axis_line_color = GRIDLINE
        ax.major_tick_line_color = None
        ax.minor_tick_line_color = None
    for grid in fig.grid:
        grid.grid_line_color = GRIDLINE
        grid.grid_line_alpha = 0.7
    for legend in fig.legend:
        legend.background_fill_alpha = 0
        legend.border_line_color = None
        legend.label_text_color = MUTED
        legend.label_text_font = FONT
    for obj in fig.right:            # heatmap colour bar
        if isinstance(obj, ColorBar):
            obj.background_fill_color = CARD_BG
            obj.major_label_text_color = MUTED
            obj.title_text_color = MUTED


CHART_OPTS = dict(hooks=[dark_style], toolbar="above", responsive=True)

# --- CSS -------------------------------------------------------------------------------
# Page-level CSS (template, fonts). Component internals use the stylesheets below,
# because Panel renders each component inside its own shadow DOM.
PAGE_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
body, #main, .main {{ background: {PAGE_BG} !important; }}
body {{ font-family: {FONT}; color: {TEXT}; }}
/* Royal-blue to navy header, in the spirit of the competition's look (colours only:
   no UEFA logo, wordmark, typeface or artwork, which are UEFA's trademarks). */
#header {{ background: {HEADER_GRADIENT} !important; border-bottom: 1px solid #2a3bd6; }}
.app-header .title {{ font-weight: 600 !important; letter-spacing: .2px; }}
"""

TABS_CSS = f"""
:host {{ --surface-color: transparent; }}
.bk-header {{ border-bottom: 1px solid {CARD_BORDER} !important; gap: 6px; }}
.bk-tab {{ font-family: {FONT}; font-size: 15px; font-weight: 600; color: {MUTED} !important;
          padding: 10px 18px !important; border: none !important; border-radius: 10px 10px 0 0;
          background: transparent !important; transition: all .15s; }}
.bk-tab:hover {{ color: {TEXT} !important; background: #0f1656 !important; }}
.bk-tab.bk-active {{ color: {TEXT} !important; background: {CARD_BG} !important;
                    box-shadow: inset 0 -3px 0 {ACCENT}; }}
"""

# Cards: rounder corners and a faint lighter top edge (like light catching the edge).
CARD_CSS = f"""
:host {{ background: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: 12px;
        padding: 14px 16px; box-shadow: inset 0 1px 0 rgba(120, 140, 255, .18); }}
"""

HTML_CSS = f"""
:host {{ font-family: {FONT}; color: {TEXT}; }}
.hero h1 {{ font-size: 30px; font-weight: 700; margin: 4px 0 2px; letter-spacing: -.3px;
           color: {TEXT}; }}
.hero p {{ color: {MUTED}; margin: 0; font-size: 15px; }}
.tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }}
.tile {{ background: {CARD_BG}; border: 1px solid {CARD_BORDER};
        border-radius: 12px; padding: 12px 14px; box-shadow: inset 0 1px 0 rgba(120, 140, 255, .18); }}
.tile .label {{ color: {MUTED}; font-size: 12px; letter-spacing: .3px; }}
.tile .value {{ font-size: 26px; font-weight: 600; color: {TEXT}; line-height: 1.2; margin-top: 4px; }}
.tile .sub {{ color: {TEXT}; opacity: .75; font-weight: 400; font-size: 13px; }}
.takeaway {{ border-left: 3px solid {ACCENT}; background: transparent; padding: 6px 14px;
            font-size: 15px; }}
.takeaway b {{ color: {TEXT}; font-weight: 600; }}
.muted {{ color: {MUTED}; font-size: 13px; }}
.focus h2 {{ margin: 0; font-size: 28px; font-weight: 800; }}
.focus .country {{ color: {MUTED}; }}
.chips {{ display: flex; gap: 6px; margin-top: 8px; }}
.chip {{ width: 28px; height: 28px; border-radius: 8px; display: grid; place-items: center;
        font-weight: 800; font-size: 13px; color: #06101f; }}
.chip.W {{ background: #34d399; }} .chip.D {{ background: #94a3b8; }} .chip.L {{ background: #f87171; }}
.stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; margin-top: 12px; }}
.stats div span {{ display: block; color: {MUTED}; font-size: 12px; text-transform: uppercase; letter-spacing: .8px; }}
.stats div b {{ font-size: 22px; }}
.vs {{ width: 100%; border-collapse: collapse; font-size: 15px; }}
.vs td {{ padding: 8px 6px; border-bottom: 1px solid {CARD_BORDER}; }}
.vs td.a {{ text-align: right; color: {ACCENT}; width: 35%; }}
.vs td.b {{ text-align: left; color: {GOLD}; width: 35%; }}
.vs td.k {{ text-align: center; color: {MUTED}; font-size: 12px; text-transform: uppercase; letter-spacing: .8px; }}
.vs td.win {{ font-weight: 800; font-size: 17px; }}
.vs th {{ font-size: 22px; font-weight: 800; padding-bottom: 8px; }}
.vs th.a {{ text-align: right; color: {ACCENT}; }} .vs th.b {{ text-align: left; color: {GOLD}; }}
.oddsbar {{ display: flex; height: 38px; border-radius: 10px; overflow: hidden; font-weight: 800;
           font-size: 14px; margin: 8px 0 4px; }}
.oddsbar div {{ display: grid; place-items: center; color: #06101f; }}
.scards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; }}
.scard {{ border: 1px solid {CARD_BORDER}; border-radius: 8px; padding: 10px 12px; }}
.scard.focus-team {{ border-color: {ACCENT}; }}
.scard h4 {{ margin: 0; font-size: 16px; display: flex; justify-content: space-between; }}
.scard h4 span {{ color: {MUTED}; font-weight: 400; font-size: 13px; }}
.srow {{ display: grid; grid-template-columns: 1fr auto; font-size: 13px; margin-top: 7px; }}
.srow .bar {{ grid-column: 1 / 3; height: 4px; background: {GRIDLINE}; border-radius: 2px; margin-top: 3px; }}
.srow .bar div {{ height: 4px; background: {REF}; border-radius: 2px; }}
.scard.focus-team .srow .bar div {{ background: {ACCENT}; }}
.story .step {{ color: {MUTED}; font-size: 12px; letter-spacing: .8px; display: flex;
                justify-content: space-between; }}
.story .tag {{ color: {ACCENT}; border: 1px solid {ACCENT}; border-radius: 4px; padding: 1px 6px;
               font-size: 11px; }}
.story h3 {{ font-size: 22px; margin: 10px 0 8px; }}
.story p {{ font-size: 14.5px; line-height: 1.5; color: {TEXT}; opacity: .9; }}
.story .notice {{ border: 1px solid {CARD_BORDER}; border-left: 3px solid {ACCENT}; border-radius: 6px;
                  padding: 10px 12px; font-size: 13.5px; color: {TEXT}; opacity: .9; }}
.story .notice b {{ color: {ACCENT}; font-size: 11px; letter-spacing: .8px; }}
.footer {{ color: {MUTED}; font-size: 12.5px; text-align: center; padding: 8px; }}
.footer a {{ color: {ACCENT}; }}
/* Fixtures strip (next matchday, our own data + Elo odds) */
.fx {{ background: {HEADER_GRADIENT}; border-radius: 12px; padding: 10px 14px 12px;
       border: 1px solid #2a3bd6; }}
.fx-head {{ font-size: 12px; letter-spacing: .8px; color: #c9d1ff; margin-bottom: 8px; }}
.fx-head b {{ color: #fff; }}
.fx-row {{ display: flex; gap: 10px; overflow-x: auto; padding-bottom: 4px;
           scrollbar-width: thin; scrollbar-color: #2a3bd6 transparent; }}
.fx-card {{ flex: 0 0 172px; background: rgba(4, 7, 43, .55); border: 1px solid rgba(255,255,255,.08);
            border-radius: 10px; padding: 8px 10px; font-size: 13px; }}
.fx-card.focus-team {{ border-color: {ACCENT}; box-shadow: 0 0 0 1px {ACCENT} inset; }}
.fx-date {{ color: #b8c1f5; font-size: 11.5px; margin-bottom: 4px; }}
.fx-team {{ display: flex; justify-content: space-between; gap: 6px; line-height: 1.55; }}
.fx-team span {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.fx-team b {{ font-weight: 600; color: #dfe4ff; }}
.fx-team.focus span, .fx-team.focus b {{ color: {ACCENT}; font-weight: 700; }}
.fx-draw {{ color: #8f9ad6; font-size: 11px; text-align: right; }}
"""

# Cyan outline buttons that fill on hover.
BUTTON_CSS = f"""
:host(.solid) .bk-btn, .bk-btn {{ font-family: {FONT}; font-weight: 600; border-radius: 8px;
    background: transparent !important; color: {ACCENT} !important; border: 1px solid {ACCENT};
    padding: 10px 14px; }}
.bk-btn:hover {{ background: {ACCENT} !important; color: #04072b !important; }}
.bk-btn:disabled {{ border-color: {CARD_BORDER}; color: {MUTED} !important; background: transparent !important; }}
"""

# Dark text input (the header's focus-team search box defaults to white-on-white).
SEARCH_CSS = f"""
input.bk-input {{ background: {CARD_BG}; color: {TEXT}; border: 1px solid {CARD_BORDER};
                  border-radius: 6px; font-family: {FONT}; font-size: 14px; }}
input.bk-input:focus {{ border-color: {ACCENT}; }}
/* !important: Panel's own select stylesheet otherwise wins (white text on white). */
select.bk-input {{ background-color: {CARD_BG} !important; color: {TEXT} !important;
                   border: 1px solid {CARD_BORDER}; border-radius: 6px; font-family: {FONT};
                   font-size: 14px; cursor: pointer; }}
select.bk-input:focus {{ border-color: {ACCENT}; }}
select.bk-input option, select.bk-input optgroup {{ background: {CARD_BG}; color: {TEXT}; }}
select.bk-input optgroup {{ color: {MUTED}; font-style: normal; }}
.bk-menu {{ background: {CARD_BG}; color: {TEXT}; border: 1px solid {CARD_BORDER}; }}
.bk-menu > .bk-active, .bk-menu > *:hover {{ background: #162070; }}
"""
