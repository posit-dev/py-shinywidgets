# The same two-instance module as 02_module_two_instances.py, but written
# with Shiny Express's module syntax (`@module`, from `shiny.express`)
# instead of the `@module.ui`/`@module.server` pair. Express modules work
# with shinywidgets with no changes: `@render_plotly` and its accessors
# behave identically inside an `@module`-decorated function.
import plotly.express as px
from shiny.express import module, render, ui
from shinywidgets import render_plotly

gapminder = px.data.gapminder()
df = gapminder[gapminder.year == 2007].reset_index(drop=True)


@module
def scatter(input, output, session, label: str):
    with ui.card(full_screen=True):
        ui.card_header(label)

        @render_plotly
        def plot():
            fig = px.scatter(
                df, x="gdpPercap", y="lifeExp", custom_data=[df.index], log_x=True
            )
            fig.update_layout(dragmode="lasso")
            return fig

        @render.data_frame
        def selected_table():
            return plot.selected_rows(df)


ui.page_opts(title="One module, two instances (Express syntax)", fillable=True)

with ui.layout_columns():
    scatter("a", "Instance A")
    scatter("b", "Instance B")
