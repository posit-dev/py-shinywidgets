from shiny import *
from ipyshiny import *
import numpy as np

#import ipywidgets as ipy
#input_ipywidget("IntSlider", ipy.IntSlider(value=4))

ui = page_fluid(
    panel_title("A demo of ipywidgets in prism"),
    layout_sidebar(
        panel_sidebar(
            input_radio_buttons(
                "framework",
                "Choose an ipywidget package",
                [
                    "ipyleaflet",
                    "plotly",
                    "bqplot",
                    "ipychart",
                    "ipywebrtc",
                    "ipyvolume",
                ],
            )
        ),
        panel_main(
            TagList(
                output_ui("figure"),
                output_ui("state"),
            )
        ),
    ),
)

def server(ss: ShinySession):
    @ss.output("figure")
    @render_ui()
    def _():
        return output_ipywidget(ss.input["framework"])

    @ss.output("state")
    @render_ui()
    def _():
        #breakpoint()
        return tags.pre(HTML(ss.input[ss.input["framework"]]))

    @ss.output("ipyleaflet")
    @render_ui()
    def _():
        from ipyleaflet import Map, Marker

        m = Map(center=(52.204793, 360.121558), zoom=4)
        m.add_layer(Marker(location=(52.204793, 360.121558)))
        return m

    @ss.output("plotly")
    @render_ipywidget()
    def _():
        import plotly.graph_objects as go

        return go.FigureWidget(
            data=[go.Bar(y=[2, 1, 3])],
            layout_title_text="A Figure Displayed with fig.show()",
        )

    @ss.output("bqplot")
    @render_ipywidget()
    def _():
        from bqplot import OrdinalScale, LinearScale, Bars, Lines, Axis, Figure

        size = 20
        x_data = np.arange(size)
        scales = {"x": OrdinalScale(), "y": LinearScale()}

        return Figure(
            title="API Example",
            legend_location="bottom-right",
            marks=[
                Bars(
                    x=x_data,
                    y=np.random.randn(2, size),
                    scales=scales,
                    type="stacked",
                ),
                Lines(
                    x=x_data,
                    y=np.random.randn(size),
                    scales=scales,
                    stroke_width=3,
                    colors=["red"],
                    display_legend=True,
                    labels=["Line chart"],
                ),
            ],
            axes=[
                Axis(scale=scales["x"], grid_lines="solid", label="X"),
                Axis(
                    scale=scales["y"],
                    orientation="vertical",
                    tick_format="0.2f",
                    grid_lines="solid",
                    label="Y",
                ),
            ],
        )

    @ss.output("ipychart")
    @render_ipywidget()
    def _():
        from ipychart import Chart

        dataset = {
            "labels": [
                "Data 1",
                "Data 2",
                "Data 3",
                "Data 4",
                "Data 5",
                "Data 6",
                "Data 7",
                "Data 8",
            ],
            "datasets": [{"data": [14, 22, 36, 48, 60, 90, 28, 12]}],
        }

        return Chart(data=dataset, kind="bar")

    @ss.output("ipywebrtc")
    @render_ipywidget()
    def _():
        from ipywebrtc import CameraStream

        return CameraStream(
            constraints={
                "facing_mode": "user",
                "audio": False,
                "video": {"width": 640, "height": 480},
            }
        )

    @ss.output("ipyvolume")
    @render_ipywidget()
    def _():
        from ipyvolume import quickquiver

        x, y, z, u, v, w = np.random.random((6, 1000)) * 2 - 1
        return quickquiver(x, y, z, u, v, w, size=5)

    # @ss.output("bokeh")
    # @render_ipywidget()
    # def _():
    #    from bokeh.plotting import figure
    #    from jupyter_bokeh import BokehModel
    #
    #    x = [1, 2, 3, 4, 5]
    #    y = [6, 7, 2, 4, 5]
    #    p = figure(title="Simple line example", x_axis_label="x", y_axis_label="y")
    #    p.line(x, y, legend_label="Temp.", line_width=2)
    #    return BokehModel(p)


app = ShinyApp(ui, server)
if __name__ == "__main__":
    app.run()
