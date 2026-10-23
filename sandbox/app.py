import k3d, numpy as np
from shiny import App, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fillable(
    ui.card(ui.card_header("k3d"), output_widget("p"), full_screen=True, style="height:600px"),
)

def server(input, output, session):
    @render_widget
    def p():
        pos = np.random.rand(200, 3).astype("float32")
        plot = k3d.plot()
        plot += k3d.points(pos, point_size=0.05, color=0xff0000)
        return plot

app = App(app_ui, server)
