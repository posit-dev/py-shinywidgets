# Shiny Core equivalent of the "Your first widget app" walkthrough
# (../../first-app/article.md): render a plotly scatter, read the user's
# lasso selection with an accessor, and highlight the selection in place.
# Everything about shinywidgets is identical to Express -- only the app's
# own scaffolding (app_ui/server, output_widget() in the UI) changes.
import plotly.express as px
from shiny import App, Inputs, Outputs, Session, reactive, render, ui
from shinywidgets import output_widget, render_plotly

gapminder = px.data.gapminder()
df = gapminder[gapminder.year == 2007].reset_index(drop=True)

app_ui = ui.page_fillable(
    ui.layout_columns(
        ui.card(
            ui.card_header("gdpPercap vs lifeExp, 2007 (drag to lasso-select)"),
            output_widget("plot"),
            full_screen=True,
        ),
        ui.card(
            ui.card_header("Selected countries"),
            ui.output_data_frame("selected_table"),
        ),
        col_widths=[8, 4],
    ),
    title="shinywidgets in Shiny Core",
)


def server(input: Inputs, output: Outputs, session: Session):
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

    # Highlighting in place, not re-rendering: the effect only mutates
    # `plot.widget`'s existing marker-color trait, so the SAME FigureWidget
    # keeps running in the browser. A zoom the user made before lassoing is
    # untouched, because nothing about the figure itself was rebuilt --
    # compare a render function that read `plot.selected_rows(df)` and
    # returned a brand new `px.scatter(...)`, which would reset the zoom on
    # every selection. No `reactive.isolate()` around the write below:
    # restyling `plot.widget` doesn't feed back into `selected_rows()`,
    # which only updates from the browser's own selection events -- see
    # "Writing back" in ../../updating-in-place/article.md#writing-back for
    # the pattern where isolate() IS required (an effect that reads and
    # writes the SAME reactive state).
    @reactive.effect
    def _highlight_selection():
        rows = plot.selected_rows(df)
        selected_idx = set(rows.index)
        colors = ["#e85d04" if i in selected_idx else "#2a6f97" for i in df.index]
        plot.widget.data[0].marker.color = colors


app = App(app_ui, server)
