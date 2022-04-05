import os

from htmltools import head_content
from shiny import *
from ipyshiny import *
import ipywidgets
import ipyleaflet as leaf
from ipyleaflet import basemaps
import plotly.graph_objs as go
import plotly.figure_factory as ff
import pandas as pd

app_dir = os.path.dirname(__file__)
allzips = pd.read_csv(os.path.join(app_dir, "superzip.csv")).sample(
    n=10000, random_state=42
)

# ------------------------------------------------------------------------
# Define user interface
# ------------------------------------------------------------------------

vars = {
    "Score": "Centile score",
    "College": "College education",
    "Income": "Median income",
    "Population": "Population",
}

css = open(os.path.join(app_dir, "styles.css"), "r").readlines()

ui_map = ui.TagList(
    ui.div(
        output_widget("map", width="100%", height="100%"),
        head_content(ui.tags.style(css)),
        ui.panel_fixed(
            # TODO: how to handle HTML inside the JSX Tag?!?!?
            # ui.h2(ui.HTML("ZIP explorer<br/>(no tiles)")),
            ui.h2("SuperZIP explorer"),
            ui.input_select("variable", "Heatmap variable", vars),
            output_widget("density_score", height="200px"),
            output_widget("density_college", height="200px"),
            output_widget("density_income", height="200px"),
            id="controls",
            class_="panel panel-default",
            width="330px",
            height="auto",
            # TODO: requirejs + jqueryui issues?
            # draggable=True,
            top="60px",
            left="auto",
            right="20px",
            bottom="auto",
        ),
        ui.div(
            "Data compiled for ",
            ui.tags.em("Coming Apart: The State of White America, 1960-2010"),
            " by Charles Murray (Crown Forum, 2012).",
            id="cite",
        ),
        class_="outer",
    ),
)

app_ui = ui.page_navbar(
    ui.nav(
        "Interactive map",
        ui.div(head_content(ui.tags.style(css)), ui_map, class_="outer"),
    ),
    ui.nav(
        "Data explorer",
        output_widget("data"),
    ),
    title="Superzip",
)

# ------------------------------------------------------------------------
# non-reactive helper functions
# ------------------------------------------------------------------------


def create_marker(row):
    return leaf.CircleMarker(
        location=(row.Lat, row.Long),
        popup=ipywidgets.HTML(
            f"""
        {row.City}, {row.State} ({row.Zipcode})<br/>
        {row.Score:.1f} overall score<br/>
        {row.College:.1f} college education<br/>
        ${row.Income:.0f}k median income<br/>
        {row.Population} people<br/>
        """
        ),
        fill_opacity=1,
        name=f"marker-{row.Zipcode}",
    )


def server(input: Inputs, output: Outputs, session: Session):

    # ------------------------------------------------------------------------
    # Main map logic
    # ------------------------------------------------------------------------

    map = leaf.Map(
        center=(37.45, -88.85),
        zoom=4,
        scroll_wheel_zoom=True,
        attribution_control=False,
        layout=ipywidgets.Layout(width="100%", height="100%"),
    )
    map.add_layer(leaf.basemap_to_tiles(basemaps.CartoDB.DarkMatter))

    # TODO: use display_widget()
    @output(name="map")
    @render_widget()
    def _():
        return map

    # Update heatmap when variable changes
    @reactive.Effect()
    def _():
        remove_heatmap()
        map.add_layer(layer_heatmap())

    @reactive.Calc()
    def zips_in_bounds():
        bb = reactive_read(map, "bounds")
        if not bb:
            return pd.DataFrame()

        lats = (bb[0][0], bb[1][0])
        lons = (bb[0][1], bb[1][1])
        return allzips[
            (allzips.Lat >= lats[0])
            & (allzips.Lat <= lats[1])
            & (allzips.Long >= lons[0])
            & (allzips.Long <= lons[1])
        ]

    # Only show markers if there are less than 500 zips in the bounds
    show_markers = reactive.Value(False)

    @reactive.Effect()
    def _():
        nzips = zips_in_bounds().shape[0]
        show_markers.set(nzips < 500)

    # When bounds change, potentially add new markers
    @reactive.Effect()
    @event(zips_in_bounds)  # TODO: reactive_read() isn't very convenient for @event()
    def _():
        if not show_markers():
            return

        # Be careful not to create markers until we know we need to add it
        zips = zips_in_bounds()
        current_markers = set(
            [m.name for m in map.layers if m.name.startswith("marker-")]
        )
        for _, row in zips.iterrows():
            if ("marker-" + str(row.Zipcode)) not in current_markers:
                map.add_layer(create_marker(row))

    # Change from heatmap to markers: remove the heatmap and show markers
    # Change from markers to heatmap: hide the markers and add the heatmap
    @reactive.Effect()
    @event(show_markers)
    def _():
        if show_markers():
            map.remove_layer(layer_heatmap())
        else:
            map.add_layer(layer_heatmap())

        opacity = 0.6 if show_markers() else 0.0

        for x in map.layers:
            if x.name.startswith("marker-"):
                x.fill_opacity = opacity
                x.opacity = opacity

    @reactive.Calc()
    def layer_heatmap():
        locs = allzips[["Lat", "Long", input.variable()]].to_numpy()
        return leaf.Heatmap(locations=locs.tolist(), name="heatmap")

    def remove_heatmap():
        for x in map.layers:
            if x.name == "heatmap":
                map.remove_layer(x)

    @output(name="density_score")
    @render_widget()
    def _():
        if zips_in_bounds().empty:
            return None
        var = "Score"
        return density_plot(allzips[var], zips_in_bounds()[var], title=var)

    @output(name="density_income")
    @render_widget()
    def _():
        if zips_in_bounds().empty:
            return None
        var = "Income"
        return density_plot(allzips[var], zips_in_bounds()[var], title=var)

    @output(name="density_college")
    @render_widget()
    def _():
        if zips_in_bounds().empty:
            return None
        var = "College"
        return density_plot(allzips[var], zips_in_bounds()[var], title=var)

    def density_plot(overall, in_bounds, title: str):
        # Create distplot with curve_type set to 'normal'
        fig = ff.create_distplot(
            [overall, in_bounds],
            ["Overall", "In bounds"],
            show_rug=False,
            show_hist=False,
        )
        # Remove tick labels
        fig.update_layout(
            hovermode="x",
            height=200,
            margin=dict(l=0, r=0, t=0, b=0),
            legend=dict(
                x=0.5, y=1, orientation="h", xanchor="center", yanchor="bottom"
            ),
            xaxis=dict(
                title=title,
                showgrid=False,
                showline=False,
                zeroline=False,
            ),
            yaxis=dict(
                showgrid=False,
                showline=False,
                showticklabels=False,
                zeroline=False,
            ),
        )

        return go.FigureWidget(data=fig.data, layout=fig.layout)

    @output(name="data")
    @render_widget()
    def _():
        return None


app = App(app_ui, server)
