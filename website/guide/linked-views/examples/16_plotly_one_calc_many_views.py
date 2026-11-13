import matplotlib.pyplot as plt
import plotly.express as px
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_itables, render_plotly

tips = px.data.tips().reset_index(drop=True)

ui.page_opts(title="One selection, many views", fillable=True)

with ui.layout_columns(col_widths=[6, 6]):
    with ui.card(full_screen=True):
        ui.card_header("Lasso some visits")

        @render_plotly
        def plot():
            fig = px.scatter(tips, x="total_bill", y="tip", color="time", custom_data=[tips.index])
            fig.update_layout(dragmode="lasso")
            return fig

    with ui.card(full_screen=True):
        ui.card_header("Selected visits")

        @reactive.calc
        def selected():
            # Computed once per selection change, however many outputs read
            # it below -- without this, each output would re-run plot's
            # selected_rows() (a customdata join against `tips`) on its own.
            return plot.selected_rows(tips)

        @render.text
        def summary():
            rows = selected()
            if rows.empty:
                return "Lasso some points to select visits."
            pct = rows["tip"] / rows["total_bill"] * 100
            return f"{len(rows)} visits, average tip {pct.mean():.1f}%"

        @render_itables
        def table():
            return selected()[["total_bill", "tip", "time", "size"]]

        @render.plot
        def hist():
            rows = selected()
            fig, ax = plt.subplots(figsize=(4, 2.2))
            if not rows.empty:
                ax.hist(rows["tip"] / rows["total_bill"] * 100, bins=10)
            ax.set_xlabel("Tip %")
            return fig
