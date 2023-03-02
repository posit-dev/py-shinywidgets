import os
from typing import List, Optional, Tuple

import ipyleaflet as leaf
import ipywidgets
import matplotlib as mpl
import numpy as np
import pandas as pd
import plotly.figure_factory as ff
import plotly.graph_objs as go
from htmltools import head_content
from ipyleaflet import basemaps
from matplotlib import cm
from shiny import *
from shiny.types import SilentException

from shinywidgets import *

color_palette = cm.get_cmap("viridis", 10)


# TODO: how to handle nas (pd.isna)?
def col_numeric(domain: Tuple[float, float], na_color: str = "#808080"):
    rescale = mpl.colors.Normalize(domain[0], domain[1])

    def _(vals: List[float]) -> List[str]:
        cols = color_palette(rescale(vals))
        return [mpl.colors.to_hex(v) for v in cols]

    return _


# TODO: when this issue is fixed, we won't have to sample anymore
# https://github.com/rstudio/prism/issues/119
app_dir = os.path.dirname(__file__)
allzips = pd.read_csv(os.path.join(app_dir, "superzip.csv")).sample(
    n=10000, random_state=42
)

# ------------------------------------------------------------------------
# Define user interface
# ------------------------------------------------------------------------

vars = {
    "Score": "Overall score",
    "College": "% college educated",
    "Income": "Median income",
    "Population": "Population",
}

css = open(os.path.join(app_dir, "styles.css"), "r").readlines()

ui_map = ui.TagList(
    output_widget("map", width="100%", height="100%"),
    ui.panel_fixed(
        ui.h2("SuperZIP explorer"),
        ui.input_select("variable", "Heatmap variable", vars),
        output_widget("density_score", height="200px"),
        output_widget("density_college", height="200px"),
        output_widget("density_income", height="200px"),
        output_widget("density_pop", height="200px"),
        id="controls",
        class_="panel panel-default",
        width="330px",
        height="auto",
        draggable=True,
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
)

app_ui = ui.page_navbar(
    ui.nav(
        "Interactive map",
        ui.div(head_content(ui.tags.style(css)), ui_map, class_="outer"),
    ),
    ui.nav(
        "Data explorer",
        ui.row(
            ui.column(3, ui.output_ui("data_intro")),
            ui.column(9, output_widget("data", height="100%")),
        ),
        ui.row(
            ui.column(2),
            ui.column(8, output_widget("table_map")),
            ui.column(2),
        ),
    ),
    title="Superzip",
)

# ------------------------------------------------------------------------
# non-reactive helper functions
# ------------------------------------------------------------------------


def density_plot(
    overall: pd.DataFrame,
    in_bounds: pd.DataFrame,
    var: str,
    selected: Optional[pd.DataFrame] = None,
    title: Optional[str] = None,
    showlegend: bool = False,
):
    dat = [overall[var], in_bounds[var]]
    if var == "Population":
        dat = [np.log10(x) for x in dat]

    # Create distplot with curve_type set to 'normal'
    fig = ff.create_distplot(
        dat,
        ["Overall", "In bounds"],
        colors=["black", "#6DCD59"],
        show_rug=False,
        show_hist=False,
    )
    # Remove tick labels
    fig.update_layout(
        # hovermode="x",
        height=200,
        showlegend=showlegend,
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(x=0.5, y=1, orientation="h", xanchor="center", yanchor="bottom"),
        xaxis=dict(
            title=title if title is not None else var,
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
    # hovermode itsn't working properly when dynamically, absolutely positioned
    for _, trace in enumerate(fig.data):
        trace.update(hoverinfo="none")

    if selected is not None:
        x = selected[var].tolist()[0]
        if var == "Population":
            x = np.log10(x)
        fig.add_shape(
            type="line",
            x0=x,
            x1=x,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(width=1, dash="dashdot", color="gray"),
        )

    return go.FigureWidget(data=fig.data, layout=fig.layout)


def create_map(**kwargs):
    map = leaf.Map(
        center=(37.45, -88.85),
        zoom=4,
        scroll_wheel_zoom=True,
        attribution_control=False,
        **kwargs,
    )
    map.add_layer(leaf.basemap_to_tiles(basemaps.CartoDB.DarkMatter))
    return map


# ------------------------------------------------------------------------
# Server logic
# ------------------------------------------------------------------------


def server(input: Inputs, output: Outputs, session: Session):
    # ------------------------------------------------------------------------
    # Main map logic
    # ------------------------------------------------------------------------
    map = create_map(layout=ipywidgets.Layout(width="100%", height="100%"))
    register_widget("map", map)

    # Keeps track of whether we're showing markers (zoomed in) or heatmap (zoomed out)
    show_markers = reactive.Value(False)

    @reactive.Effect
    def _():
        nzips = zips_in_bounds().shape[0]
        show_markers.set(nzips < 200)

    # When the variable changes, either update marker colors or redraw the heatmap
    @reactive.Effect
    @reactive.event(input.variable)
    def _():
        zips = zips_in_bounds()
        if not show_markers():
            remove_heatmap()
            map.add_layer(layer_heatmap())
        else:
            zip_colors = dict(zip(zips.Zipcode, zips_marker_color()))
            for x in map.layers:
                if x.name.startswith("marker-"):
                    zipcode = int(x.name.split("-")[1])
                    if zipcode in zip_colors:
                        x.color = zip_colors[zipcode]

    # When bounds change, maybe add new markers
    @reactive.Effect
    @reactive.event(lambda: zips_in_bounds())
    def _():
        if not show_markers():
            return
        zips = zips_in_bounds()
        if zips.empty:
            return

        # Be careful not to create markers until we know we need to add it
        current_markers = set(
            [m.name for m in map.layers if m.name.startswith("marker-")]
        )
        zips["Color"] = zips_marker_color()
        for _, row in zips.iterrows():
            if ("marker-" + str(row.Zipcode)) not in current_markers:
                map.add_layer(create_marker(row, color=row.Color))

    # Change from heatmap to markers: remove the heatmap and show markers
    # Change from markers to heatmap: hide the markers and add the heatmap
    @reactive.Effect
    @reactive.event(show_markers)
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

    @reactive.Calc
    def zips_in_bounds():
        bb = reactive_read(map, "bounds")
        if not bb:
            # TODO: this should really be `raise SilentException`...why doesn't it work?
            # return pd.DataFrame()
            raise SilentException

        lats = (bb[0][0], bb[1][0])
        lons = (bb[0][1], bb[1][1])
        return allzips[
            (allzips.Lat >= lats[0])
            & (allzips.Lat <= lats[1])
            & (allzips.Long >= lons[0])
            & (allzips.Long <= lons[1])
        ]

    @reactive.Calc
    def zips_marker_color():
        vals = allzips[input.variable()]
        domain = (vals.min(), vals.max())
        vals_in_bb = zips_in_bounds()[input.variable()]
        return col_numeric(domain)(vals_in_bb)

    @reactive.Calc
    def layer_heatmap():
        locs = allzips[["Lat", "Long", input.variable()]].to_numpy()
        return leaf.Heatmap(
            locations=locs.tolist(),
            name="heatmap",
            # R> cat(paste0(round(scales::rescale(log10(1:10), to = c(0.05, 1)), 2), ": '", viridis::viridis(10), "'"), sep = "\n")
            gradient={
                0.05: "#440154",
                0.34: "#482878",
                0.5: "#3E4A89",
                0.62: "#31688E",
                0.71: "#26828E",
                0.79: "#1F9E89",
                0.85: "#35B779",
                0.91: "#6DCD59",
                0.96: "#B4DE2C",
                1: "#FDE725",
            },
        )

    def remove_heatmap():
        for x in map.layers:
            if x.name == "heatmap":
                map.remove_layer(x)

    zip_selected = reactive.Value(None)

    @output(id="density_score")
    @render_widget
    def _():
        return density_plot(
            allzips,
            zips_in_bounds(),
            selected=zip_selected(),
            var="Score",
            title="Overall Score",
            showlegend=True,
        )

    @output(id="density_income")
    @render_widget
    def _():
        return density_plot(
            allzips, zips_in_bounds(), selected=zip_selected(), var="Income"
        )

    @output(id="density_college")
    @render_widget
    def _():
        return density_plot(
            allzips, zips_in_bounds(), selected=zip_selected(), var="College"
        )

    @output(id="density_pop")
    @render_widget
    def _():
        return density_plot(
            allzips,
            zips_in_bounds(),
            selected=zip_selected(),
            var="Population",
            title="log10(Population)",
        )

    def create_marker(row, **kwargs):
        m = leaf.CircleMarker(
            location=(row.Lat, row.Long),
            popup=ipywidgets.HTML(
                f"""
            {row.City}, {row.State} ({row.Zipcode})<br/>
            {row.Score:.1f} overall score<br/>
            {row.College:.1f}% college educated<br/>
            ${row.Income:.0f}k median income<br/>
            {row.Population} people<br/>
            """
            ),
            name=f"marker-{row.Zipcode}",
            **kwargs,
        )

        def _on_click(**kwargs):
            coords = kwargs["coordinates"]
            idx = (allzips.Lat == coords[0]) & (allzips.Long == coords[1])
            zip_selected.set(allzips[idx])

        m.on_click(_on_click)

        return m

    @output(id="data_intro")
    @render.ui
    def _():
        zips = zips_in_bounds()

        md = ui.markdown(
            f"""
            {zips.shape[0]} zip codes are currently within the map's viewport, and amongst them:

              * {100*zips.Superzip.mean():.1f}% are superzips
              * Mean income is ${zips.Income.mean():.0f}k  💰
              * Mean population is {zips.Population.mean():.0f} 👨🏽👩🏽👦🏽
              * Mean college educated is {zips.College.mean():.1f}% 🎓

            Use the filter controls on the table's columns to drill down further or
            click on a row to
            """,
        )

        return ui.div(md, class_="my-3 lead")

    selected_table_row = reactive.Value(pd.DataFrame())

    @output(id="data")
    @render_widget
    def _():
        import qgrid

        dat = zips_in_bounds().drop(["Lat", "Long", "Color"], axis=1, errors="ignore")

        w = qgrid.show_grid(
            dat,
            grid_options={"editable": False},
            column_definitions={"index": {"maxWidth": 0, "minWidth": 0, "width": 0}},
        )

        def _on_change(event, widget):
            idx = event["new"][0]
            selected_table_row.set(zips_in_bounds().iloc[[idx]])

        w.on("selection_changed", _on_change)

        return w

    table_map = create_map()

    @output(id="table_map")
    @render_widget
    def _():
        if selected_table_row().empty:
            return None
        else:
            return table_map

    # TODO: currently there is a bug where clicking the popup causes an error,
    # but I _think_ this'll get fixed in the next release of ipywidgets/ipyleaflet
    # https://github.com/jupyter-widgets/ipywidgets/issues/3384
    @reactive.Effect
    @reactive.event(selected_table_row)
    def _():
        for x in table_map.layers:
            if x.name.startswith("marker"):
                table_map.remove_layer(x)
        for _, row in selected_table_row().iterrows():
            table_map.add_layer(create_marker(row))


app = App(app_ui, server)
