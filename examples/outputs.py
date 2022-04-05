import pandas as pd
import qgrid
from vega_datasets import data
from shiny import *
from ipyshiny import *
import numpy as np

app_ui = ui.page_fluid(
    ui.layout_sidebar(
        ui.panel_sidebar(
            ui.input_radio_buttons(
                "framework",
                "Choose an ipywidget package",
                [
                    "qgrid",
                    "ipyleaflet",
                    "pydeck",
                    "altair",
                    "plotly",
                    # TODO: fix me
                    # "bokeh",
                    "bqplot",
                    "ipychart",
                    "ipywebrtc",
                    "ipyvolume",
                ],
                selected="qgrid",
            )
        ),
        ui.panel_main(
            ui.TagList(
                ui.output_ui("figure"),
                ui.output_ui("state"),
            )
        ),
    ),
    title="ipywidgets in Shiny",
)


def server(input: Inputs, output: Outputs, session: Session):
    @output(name="figure")
    @render_ui()
    def _():
        return output_widget(input.framework())

    @output(name="state")
    @render_ui()
    def _():
        f = input.framework()
        return ui.tags.pre(ui.HTML(input[f]()))

    @output(name="ipyleaflet")
    @render_widget()
    def _():
        from ipyleaflet import Map, Marker

        m = Map(center=(52.204793, 360.121558), zoom=4)
        m.add_layer(Marker(location=(52.204793, 360.121558)))
        return m

    @output(name="qgrid")
    @render_widget()
    def _():
        randn = np.random.randn
        df_types = pd.DataFrame(
            {
                "A": pd.Series(
                    [
                        "2013-01-01",
                        "2013-01-02",
                        "2013-01-03",
                        "2013-01-04",
                        "2013-01-05",
                        "2013-01-06",
                        "2013-01-07",
                        "2013-01-08",
                        "2013-01-09",
                    ],
                    index=list(range(9)),
                    dtype="datetime64[ns]",
                ),
                "B": pd.Series(randn(9), index=list(range(9)), dtype="float32"),
                "C": pd.Categorical(
                    [
                        "washington",
                        "adams",
                        "washington",
                        "madison",
                        "lincoln",
                        "jefferson",
                        "hamilton",
                        "roosevelt",
                        "kennedy",
                    ]
                ),
                "D": [
                    "foo",
                    "bar",
                    "buzz",
                    "bippity",
                    "boppity",
                    "foo",
                    "foo",
                    "bar",
                    "zoo",
                ],
            }
        )
        df_types["E"] = df_types["D"] == "foo"
        return qgrid.show_grid(df_types, show_toolbar=True)

    @output(name="altair")
    @render_widget()
    def _():
        import altair as alt

        return (
            alt.Chart(data.cars())
            .mark_point()
            .encode(
                x="Horsepower",
                y="Miles_per_Gallon",
                color="Origin",
            )
        )

    @output(name="plotly")
    @render_widget()
    def _():
        import plotly.graph_objects as go

        return go.FigureWidget(
            data=[go.Bar(y=[2, 1, 3])],
            layout_title_text="A Figure Displayed with fig.show()",
        )

    @output(name="bqplot")
    @render_widget()
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

    @output(name="ipychart")
    @render_widget()
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

    @output(name="ipywebrtc")
    @render_widget()
    def _():
        from ipywebrtc import CameraStream

        return CameraStream(
            constraints={
                "facing_mode": "user",
                "audio": False,
                "video": {"width": 640, "height": 480},
            }
        )

    @output(name="ipyvolume")
    @render_widget()
    def _():
        from ipyvolume import quickquiver

        x, y, z, u, v, w = np.random.random((6, 1000)) * 2 - 1
        return quickquiver(x, y, z, u, v, w, size=5)

    @output(name="pydeck")
    @render_widget()
    def _():
        import pydeck as pdk

        UK_ACCIDENTS_DATA = "https://raw.githubusercontent.com/visgl/deck.gl-data/master/examples/3d-heatmap/heatmap-data.csv"

        layer = pdk.Layer(
            "HexagonLayer",  # `type` positional argument is here
            UK_ACCIDENTS_DATA,
            get_position=["lng", "lat"],
            auto_highlight=True,
            elevation_scale=50,
            pickable=True,
            elevation_range=[0, 3000],
            extruded=True,
            coverage=1,
        )

        # Set the viewport location
        view_state = pdk.ViewState(
            longitude=-1.415,
            latitude=52.2323,
            zoom=6,
            min_zoom=5,
            max_zoom=15,
            pitch=40.5,
            bearing=-27.36,
        )

        # Combined all of it and render a viewport
        return pdk.Deck(layers=[layer], initial_view_state=view_state)

    @output(name="bokeh")
    @render_widget()
    def _():
        from bokeh.plotting import figure
        from jupyter_bokeh import BokehModel

        # TODO: figure out what this does and try to replicate it
        import bokeh.io

        bokeh.io.output_notebook()

        x = [1, 2, 3, 4, 5]
        y = [6, 7, 2, 4, 5]
        p = figure(title="Simple line example", x_axis_label="x", y_axis_label="y")
        p.line(x, y, legend_label="Temp.", line_width=2)
        return BokehModel(p)


app = App(app_ui, server)
