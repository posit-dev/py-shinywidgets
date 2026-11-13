import plotly.express as px
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_plotly

df = px.data.gapminder().query("year == 2007").reset_index(drop=True)

ui.page_opts(title="Debounced vs. unlimited selecting()", fillable=True)

count_debounced = reactive.value(0)
count_live = reactive.value(0)

with ui.layout_columns():
    with ui.card(full_screen=True):
        "Default: debounced 250ms"

        @render_plotly
        def debounced():
            fig = px.scatter(df, x="gdpPercap", y="lifeExp", log_x=True)
            fig.update_layout(dragmode="select")
            return fig

        @reactive.effect
        def _count_debounced():
            debounced.selecting()
            with reactive.isolate():
                count_debounced.set(count_debounced() + 1)

        @render.text
        def n_debounced():
            return f"selecting() fired {count_debounced()} times"

    with ui.card(full_screen=True):
        "rate_delay=0: fires on every drag event"

        @render_plotly(rate_delay=0)
        def live():
            fig = px.scatter(df, x="gdpPercap", y="lifeExp", log_x=True)
            fig.update_layout(dragmode="select")
            return fig

        @reactive.effect
        def _count_live():
            live.selecting()
            with reactive.isolate():
                count_live.set(count_live() + 1)

        @render.text
        def n_live():
            return f"selecting() fired {count_live()} times"
