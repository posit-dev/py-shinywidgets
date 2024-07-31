from pathlib import Path

import numpy as np
from shiny import *

from shinywidgets import *

app_dir = Path(__file__).parent

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_radio_buttons(
            "framework",
            "Choose a widget",
            [
                "altair",
                "plotly",
                "ipyleaflet",
                "pydeck",
                "quak",
                "mosaic",
                "ipysigma",
                "bokeh",
                "bqplot",
                "ipychart",
                "ipywebrtc",
                # TODO: fix ipyvolume, qgrid
            ],
            selected="altair",
        )
    ),
    bokeh_dependency(),
    ui.output_ui("figure", fill=True, fillable=True),
    title="Hello Jupyter Widgets in Shiny for Python",
    fillable=True,
)


def server(input: Inputs, output: Outputs, session: Session):
    @output(id="figure")
    @render.ui
    def _():
        return ui.card(
            ui.card_header(input.framework()),
            output_widget(input.framework()),
            full_screen=True,
        )

    @output(id="altair")
    @render_widget
    def _():
        import altair as alt
        from vega_datasets import data

        source = data.stocks()

        return (
            alt.Chart(source)
            .transform_filter('datum.symbol==="GOOG"')
            .mark_area(
                tooltip=True,
                line={"color": "#0281CD"},
                color=alt.Gradient(
                    gradient="linear",
                    stops=[
                        alt.GradientStop(color="white", offset=0),
                        alt.GradientStop(color="#0281CD", offset=1),
                    ],
                    x1=1,
                    x2=1,
                    y1=1,
                    y2=0,
                ),
            )
            .encode(alt.X("date:T"), alt.Y("price:Q"))
            .properties(title={"text": ["Google's stock price over time"]})
        )

    @output(id="plotly")
    @render_widget
    def _():
        import plotly.express as px

        return px.density_heatmap(
            px.data.tips(),
            x="total_bill",
            y="tip",
            marginal_x="histogram",
            marginal_y="histogram",
        )

    @output(id="ipyleaflet")
    @render_widget
    def _():
        from ipyleaflet import Map, Marker

        m = Map(center=(52.204793, 360.121558), zoom=4)
        m.add_layer(Marker(location=(52.204793, 360.121558)))
        return m

    @output(id="pydeck")
    @render_widget
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

    @output(id="quak")
    @render_widget
    def _():
        import polars as pl
        import quak

        df = pl.read_parquet(
            "https://github.com/uwdata/mosaic/raw/main/data/athletes.parquet"
        )
        return quak.Widget(df)

    @output(id="mosaic")
    @render_widget
    def _():
        import polars as pl
        import yaml
        from mosaic_widget import MosaicWidget

        flights = pl.read_parquet(
            "https://github.com/uwdata/mosaic/raw/main/data/flights-200k.parquet"
        )

        # Load weather spec, remove data key to ensure load from Pandas
        with open(app_dir / "flights.yaml") as f:
            spec = yaml.safe_load(f)
            _ = spec.pop("data")

        return MosaicWidget(spec, data={"flights": flights})

    @output(id="ipysigma")
    @render_widget
    def _():
        import igraph as ig
        from ipysigma import Sigma

        g = ig.Graph.Famous("Zachary")
        return Sigma(
            g,
            node_size=g.degree,
            node_color=g.betweenness(),
            node_color_gradient="Viridis",
        )

    @output(id="bokeh")
    @render_widget
    def _():
        from bokeh.plotting import figure

        x = [1, 2, 3, 4, 5]
        y = [6, 7, 2, 4, 5]
        p = figure(title="Simple line example", x_axis_label="x", y_axis_label="y")
        p.line(x, y, legend_label="Temp.", line_width=2)
        return p

    @output(id="bqplot")
    @render_widget
    def _():
        from bqplot import Axis, Bars, Figure, LinearScale, Lines, OrdinalScale

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

    @output(id="ipychart")
    @render_widget
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

    @output(id="ipywebrtc")
    @render_widget
    def _():
        from ipywebrtc import CameraStream

        return CameraStream(
            constraints={
                "facing_mode": "user",
                "audio": False,
                "video": {"width": 640, "height": 480},
            }
        )


app = App(app_ui, server)
