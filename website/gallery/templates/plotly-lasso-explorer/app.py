# Title: Lasso explorer
# Summary: Lasso points in a plotly scatter plot and see the matching rows
#     in a searchable table and a one-line summary, with a click-through detail
#     card for a single point. A clean starting point for "explore my data
#     frame visually" apps -- swap in your own data frame and column names.
# Bucket: template
# Widgets: plotly, itables
# Pattern: selection -> table
# Run: uv run shiny run app.py
# Data: plotly.express.data.gapminder() (ships with plotly)
#
# Source: docs/widget-guides/plotly/gallery/template_lasso_explorer.py
# Note: a module docstring here would be auto-displayed as page text by Shiny
# Express (a bare top-level string is rendered like `ui.markdown`), so this
# header is a comment block instead.

import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_itables, render_plotly

df = px.data.gapminder().query("year == 2007").reset_index(drop=True)

ui.page_opts(title="Lasso explorer", fillable=True)

with ui.layout_columns(col_widths=[7, 5, 12], row_heights=[1, 1]):
    with ui.card(full_screen=True):
        ui.card_header("Drag the lasso tool to select points")

        @render_plotly
        def plot():
            fig = px.scatter(
                df,
                x="gdpPercap",
                y="lifeExp",
                color="continent",
                size="pop",
                size_max=40,
                log_x=True,
                custom_data=[df.index],
            )
            fig.update_layout(dragmode="lasso")
            return fig

    with ui.card():
        ui.card_header("Last click (note: clicking also clears the lasso below)")

        @render.ui
        def detail():
            pts = plot.clicked()
            if pts is None:
                return ui.p("Click a point for details.", class_="text-muted")
            row = df.loc[pts["customdata"].iloc[0][0]]
            return ui.TagList(
                ui.h5(row["country"]),
                f"{row['continent']}, life expectancy {row['lifeExp']:.1f}",
            )

    with ui.card(full_screen=True):
        ui.card_header("Selection")

        @render.text
        def summary():
            rows = plot.selected_rows(df)
            if rows.empty:
                return "Lasso some points to filter the table below."
            return f"{len(rows)} of {len(df)} rows selected"

        @render_itables
        def table():
            cols = ["country", "continent", "lifeExp", "gdpPercap", "pop"]
            return plot.selected_rows(df)[cols]
