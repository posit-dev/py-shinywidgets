# Same lasso-selection task in plotly, altair, and bokeh, side by side.
# Shows how similar the *shape* of the task is across libraries, and the one
# real difference: altair's selection is declared in the chart spec (a
# grammar object you read by name); plotly's and bokeh's are accessors on
# the renderer itself, driven by `dragmode`/`BoxSelectTool`.
# Run: uv run shiny run docs/widget-guides/articles/choosing-a-widget/examples/01_selection_three_libraries.py
import altair as alt
import plotly.express as px
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from shiny.express import render, ui
from shinywidgets import render_altair, render_bokeh, render_plotly

ui.page_opts(title="Lasso/box-select: three libraries", fillable=True)

df = px.data.gapminder().query("year == 2007").reset_index(drop=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("plotly")

        @render_plotly
        def plot_plotly():
            fig = px.scatter(df, x="gdpPercap", y="lifeExp", log_x=True, custom_data=[df.index])
            fig.update_layout(dragmode="select", margin=dict(l=16, r=16, t=16, b=16))
            return fig

        @render.code
        def count_plotly():
            rows = plot_plotly.selected_rows(df)
            return f"{len(rows)} countries selected"

    with ui.card(full_screen=True):
        ui.card_header("altair")

        @render_altair
        def plot_altair():
            brush = alt.selection_interval(name="brush")
            return (
                alt.Chart(df)
                .mark_circle()
                .encode(x=alt.X("gdpPercap", scale=alt.Scale(type="log")), y="lifeExp")
                .add_params(brush)
            )

        @render.code
        def count_altair():
            rows = plot_altair.selected_rows("brush")
            return f"{len(rows)} countries selected"

    with ui.card(full_screen=True):
        ui.card_header("bokeh")

        @render_bokeh
        def plot_bokeh():
            source = ColumnDataSource(df)
            fig = figure(x_axis_type="log", tools="box_select,reset", active_drag="box_select")
            fig.scatter("gdpPercap", "lifeExp", source=source)
            return fig

        @render.code
        def count_bokeh():
            rows = plot_bokeh.selected_rows()
            return f"{len(rows)} countries selected"
