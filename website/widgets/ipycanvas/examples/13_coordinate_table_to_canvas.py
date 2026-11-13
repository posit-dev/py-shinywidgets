import pandas as pd
from ipycanvas import Canvas
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_ipycanvas

ui.page_opts(title="Table selection highlights canvas", fillable=True)

# The Big Dipper's 7 stars, with illustrative (not-to-scale) chart positions
STARS = pd.DataFrame(
    [
        ("Dubhe", 70, 40),
        ("Merak", 80, 90),
        ("Phecda", 150, 110),
        ("Megrez", 170, 70),
        ("Alioth", 230, 60),
        ("Mizar", 290, 45),
        ("Alkaid", 350, 30),
    ],
    columns=["star", "x", "y"],
)

with ui.layout_columns(col_widths=(5, 7)):
    with ui.card():
        ui.card_header("Select a star")

        @render.data_frame
        def table():
            return render.DataGrid(STARS[["star"]], selection_mode="row")

    with ui.card(full_screen=True):

        @render_ipycanvas
        def canvas():
            c = Canvas(width=400, height=160)
            c.fill_style = "#0b1026"
            c.fill_rect(0, 0, 400, 160)
            return c


def redraw(selected_row: int | None):
    c = canvas.widget
    if c is None:
        return
    c.clear()
    c.fill_style = "#0b1026"
    c.fill_rect(0, 0, 400, 160)
    c.fill_style = "#f5f3ce"
    for _, row in STARS.iterrows():
        c.fill_circle(row.x, row.y, 4)
    if selected_row is not None:
        star = STARS.iloc[selected_row]
        c.stroke_style = "#e67e22"
        c.line_width = 2
        c.stroke_circle(star.x, star.y, 12)
        c.fill_style = "#e67e22"
        c.fill_text(star.star, star.x + 14, star.y + 4)


@reactive.effect
def _highlight_selected():
    rows = table.cell_selection()["rows"]
    redraw(rows[0] if rows else None)
