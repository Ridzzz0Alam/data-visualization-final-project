"""Visual design: one dark 'UCL night' palette, CSS, and a chart-style hook.

Colour rules (same in every view):
  ACCENT (cyan)  = the focus team        GOLD = the second team in head-to-head
  GREY (slate)   = every other team      REF  = reference lines / neutral marks
"""

from __future__ import annotations

from bokeh.models import ColorBar

# --- Palette ---------------------------------------------------------------------
PAGE_BG = "#060a18"
CARD_BG = "#0e1530"
CARD_BORDER = "#1d2a52"
TEXT = "#e8ecff"
MUTED = "#8b95ba"
GRIDLINE = "#1f2a4d"
ACCENT = "#22d3ee"      # focus team
GOLD = "#fbbf24"        # second team (head-to-head) / favourite
GREY = "#46527a"        # other teams
REF = "#7c86ad"         # reference lines
HEAT_CMAP = ["#121a3a", "#1e3a8a", "#2563eb", "#22d3ee", "#cffafe"]
FONT = "Outfit, 'Segoe UI', sans-serif"


def dark_style(plot, element) -> None:
    """Bokeh hook applied to every chart: dark card background, light text, soft grid."""
    fig = plot.state
    fig.background_fill_color = CARD_BG
    fig.border_fill_color = CARD_BG
    fig.outline_line_color = None
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
body, #main, .main {{ background: radial-gradient(1200px 600px at 10% -10%, #14204a 0%, {PAGE_BG} 60%) fixed !important; }}
body {{ font-family: {FONT}; color: {TEXT}; }}
#header {{ background: linear-gradient(90deg, #0a1236, #13235e 60%, #0a1236) !important;
          border-bottom: 1px solid {CARD_BORDER}; }}
.app-header .title {{ font-weight: 800 !important; letter-spacing: .5px; }}
"""

TABS_CSS = f"""
:host {{ --surface-color: transparent; }}
.bk-header {{ border-bottom: 1px solid {CARD_BORDER} !important; gap: 6px; }}
.bk-tab {{ font-family: {FONT}; font-size: 15px; font-weight: 600; color: {MUTED} !important;
          padding: 10px 18px !important; border: none !important; border-radius: 10px 10px 0 0;
          background: transparent !important; transition: all .15s; }}
.bk-tab:hover {{ color: {TEXT} !important; background: #121c40 !important; }}
.bk-tab.bk-active {{ color: {TEXT} !important; background: {CARD_BG} !important;
                    box-shadow: inset 0 -3px 0 {ACCENT}; }}
"""

CARD_CSS = f"""
:host {{ background: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: 16px;
        padding: 14px 16px; box-shadow: 0 8px 30px rgba(0,0,0,.35); }}
"""

HTML_CSS = f"""
:host {{ font-family: {FONT}; color: {TEXT}; }}
.hero h1 {{ font-size: 34px; font-weight: 800; margin: 4px 0 2px; letter-spacing: -.5px;
           background: linear-gradient(90deg, #fff, {ACCENT}); -webkit-background-clip: text;
           -webkit-text-fill-color: transparent; }}
.hero p {{ color: {MUTED}; margin: 0; font-size: 15px; }}
.tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }}
.tile {{ background: linear-gradient(160deg, #13204a, {CARD_BG}); border: 1px solid {CARD_BORDER};
        border-radius: 16px; padding: 14px 16px; position: relative; overflow: hidden; }}
.tile::after {{ content: ""; position: absolute; right: -30px; top: -30px; width: 90px; height: 90px;
               border-radius: 50%; background: radial-gradient({ACCENT}33, transparent 70%); }}
.tile .label {{ color: {MUTED}; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }}
.tile .value {{ font-size: 30px; font-weight: 800; color: {TEXT}; line-height: 1.15; margin-top: 4px; }}
.tile .sub {{ color: {ACCENT}; font-weight: 600; font-size: 14px; }}
.takeaway {{ border-left: 4px solid {ACCENT}; background: #0f1a3d; padding: 12px 16px;
            border-radius: 0 12px 12px 0; font-size: 16px; }}
.takeaway b {{ color: {ACCENT}; }}
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
.footer {{ color: {MUTED}; font-size: 12.5px; text-align: center; padding: 8px; }}
.footer a {{ color: {ACCENT}; }}
"""

BUTTON_CSS = f"""
:host(.solid) .bk-btn, .bk-btn {{ font-family: {FONT}; font-weight: 600; border-radius: 12px;
    background: #13204a; color: {TEXT}; border: 1px solid {CARD_BORDER}; padding: 10px 14px; }}
.bk-btn:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
"""
