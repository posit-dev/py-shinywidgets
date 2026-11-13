# Title: Palmer penguins, click explorer
# Bucket: template
# One-line: A scatter plot with per-axis controls where clicking a point
# shows that penguin's measurements, using the clicked() accessor.
# Run: uv run --no-sync shiny run template_click_explorer.py
# Data: plotnine.data.penguins (ships with plotnine)
#
# Note: this header is a comment, not a module docstring -- Shiny Express
# renders a bare top-level string literal as page content.

import numpy as np
from plotnine import aes, geom_point, geom_smooth, ggplot, labs, theme_minimal
from plotnine.data import penguins
from shiny import reactive, req
from shiny.express import input, render, ui
from shinywidgets import render_plotnine

penguins = penguins.dropna().reset_index(drop=True)

numeric_vars = {
    "bill_length_mm": "Bill length (mm)",
    "bill_depth_mm": "Bill depth (mm)",
    "flipper_length_mm": "Flipper length (mm)",
    "body_mass_g": "Body mass (g)",
}
labels = {**numeric_vars, "species": "Species"}

ui.page_opts(title="Palmer penguins, click explorer", fillable=True)
found = reactive.value(None)

with ui.layout_sidebar():
    with ui.sidebar():
        ui.input_select("x", "X", numeric_vars, selected="bill_length_mm")
        ui.input_select("y", "Y", numeric_vars, selected="bill_depth_mm")
        ui.input_switch("smooth", "Linear fit per species", True)

    with ui.layout_columns(col_widths=(8, 4)):
        with ui.card(full_screen=True):

            @render_plotnine
            def plot():
                x, y = input.x(), input.y()
                p = (
                    ggplot(penguins, aes(x, y, color="species"))
                    + geom_point(size=2.5, alpha=0.8)
                    + labs(x=labels[x], y=labels[y], color="Species")
                    + theme_minimal()
                )
                if input.smooth():
                    p += geom_smooth(method="lm")
                return p

        with ui.card():
            ui.card_header("Clicked penguin")

            @render.ui
            def detail():
                # Compare to None explicitly: a row position of 0 is falsy,
                # so req(found()) would wrongly treat it as "no click yet"
                i = found()
                if i is None:
                    return ui.p("Click a point to see that penguin here.")
                row = penguins.iloc[i]
                x, y = input.x(), input.y()
                return ui.p(
                    f"{row.species}, {row.island} Island: "
                    f"{labels[x]} = {row[x]:g}, {labels[y]} = {row[y]:g}"
                )


@reactive.effect
def _mark_nearest():
    event = plot.clicked()
    canvas = plot.widget
    req(event, canvas)
    with reactive.isolate():
        x, y = input.x(), input.y()
    ax = canvas.figure.axes[0]
    xy = ax.transData.transform(penguins[[x, y]].to_numpy())
    i = int(np.hypot(xy[:, 0] - event.x, xy[:, 1] - event.y).argmin())
    found.set(i)

    for artist in list(ax.lines):
        if artist.get_label() == "_clicked":
            artist.remove()
    row = penguins.iloc[i]
    ax.plot(
        [row[x]], [row[y]], "o", ms=14, mfc="none", mec="black", mew=2, label="_clicked"
    )
    canvas.draw_idle()
