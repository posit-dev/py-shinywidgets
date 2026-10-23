import holoviews as hv
from bokeh.plotting import figure
from shiny import App, ui
from shinywidgets import output_widget, render_bokeh, render_holoviews

hv.extension("bokeh")


def line(**kwargs):
    p = figure(**kwargs)
    p.line([1, 2, 3], [1, 3, 2])
    return p


app_ui = ui.page_fluid(
    ui.card(output_widget("stretched"), height="300px"),
    ui.card(output_widget("fixed"), height="300px"),
    output_widget("explicit_height", height="250px"),
    output_widget("hv_explicit_height", height="250px"),
)


def server(input, output, session):
    @render_bokeh
    def stretched():
        return line()

    @render_bokeh
    def fixed():
        return line(width=250, height=150)

    @render_bokeh
    def explicit_height():
        return line()

    @render_holoviews
    def hv_explicit_height():
        return hv.Curve([1, 3, 2]).opts(responsive=True)


app = App(app_ui, server)
