# Two instances of one Shiny module, each rendering its own plotly scatter
# with its own selection table. The point of this example is namespacing:
# lassoing points in instance A must not affect instance B's accessor, and
# vice versa (see the article's "Modules" section for what was verified).
import plotly.express as px
from shiny import App, Inputs, Outputs, Session, module, render, ui
from shinywidgets import output_widget, render_plotly

gapminder = px.data.gapminder()
df = gapminder[gapminder.year == 2007].reset_index(drop=True)


@module.ui
def scatter_ui(label: str):
    return ui.card(
        ui.card_header(label),
        output_widget("plot"),
        ui.output_data_frame("selected_table"),
        full_screen=True,
    )


@module.server
def scatter_server(input: Inputs, output: Outputs, session: Session):
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


app_ui = ui.page_fillable(
    ui.layout_columns(
        scatter_ui("a", "Instance A"),
        scatter_ui("b", "Instance B"),
    ),
    title="One module, two instances",
)


def server(input: Inputs, output: Outputs, session: Session):
    scatter_server("a")
    scatter_server("b")


app = App(app_ui, server)
