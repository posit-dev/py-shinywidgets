from pathlib import Path

import ipyleaflet as leaf
import ipywidgets
import pandas as pd
from faicons import icon_svg
from ratelimit import debounce
from shiny import App, Inputs, Outputs, Session, reactive, render, req, ui
from utils import col_numeric, create_map, density_plot, heatmap_gradient

from shinywidgets import output_widget, reactive_read, render_plotly, render_widget

# Load data
app_dir = Path(__file__).parent
allzips = pd.read_csv(app_dir / "superzip.csv").sample(
    n=10000, random_state=42
)

# ------------------------------------------------------------------------
# Define user interface
# ------------------------------------------------------------------------

vars = {
    "Score": "overall superzip score",
    "College": "% college educated",
    "Income": "median income",
    "Population": "population",
}

app_ui = ui.page_navbar(
    ui.nav_spacer(),
    ui.nav_panel(
        "Interactive map",
        ui.layout_sidebar(
            ui.sidebar(
                output_widget("density_score"),
                output_widget("density_college"),
                output_widget("density_income"),
                output_widget("density_pop"),
                position="right",
                width=300,
                title=ui.tooltip(
                    ui.span(
                        "Overall density vs in bounds",
                        icon_svg("circle-info").add_class("ms-2"),
                    ),
                    "The density plots show how various metrics behave overall (black) in comparison to within view (green)."
                )
            ),
            ui.card(
                ui.card_header(
                    "Heatmap showing ",
                    ui.input_select("variable", None, vars, width="auto"),
                    class_="d-flex align-items-center gap-3"
                ),
                output_widget("map"),
                ui.card_footer(
                    ui.markdown("Data compiled for _Coming Apart: The State of White America, 1960-2010_ by Charles Murray (Crown Forum, 2012).")
                ),
                full_screen=True
            )
        )
    ),
    ui.nav_panel(
        "Data explorer",
        ui.layout_columns(
            ui.output_ui("data_intro"),
            ui.output_data_frame("zips_data"),
            col_widths=[3, 9]
        ),
        ui.layout_columns(
            output_widget("table_map"),
            col_widths=[-2, 8, -2]
        )
    ),
    fillable="Interactive map",
    id="navbar",
    header=ui.include_css(app_dir / "styles.css"),
    title=ui.popover(
        [
            "Superzip explorer",
            icon_svg("circle-info").add_class("ms-2"),
        ],
        ui.markdown("'Super Zips' is a term [coined by Charles Murray](https://www.amazon.com/Coming-Apart-State-America-1960-2010/dp/030745343X) to describe the most prosperous, highly educated demographic clusters"),
        placement="right",
    ),
    window_title="Superzip explorer"
)


# ------------------------------------------------------------------------
# Server logic
# ------------------------------------------------------------------------


def server(input: Inputs, output: Outputs, session: Session):
    # ------------------------------------------------------------------------
    # Main map logic
    # ------------------------------------------------------------------------
    @render_widget
    def map():
        return create_map()

    # Keeps track of whether we're showing markers (zoomed in) or heatmap (zoomed out)
    show_markers = reactive.value(False)

    # Switch from heatmap to markers when zoomed into 200 or fewer zips
    @reactive.effect
    def _():
        nzips = zips_in_bounds().shape[0]
        show_markers.set(nzips < 200)

    # When the variable changes, either update marker colors or redraw the heatmap
    @reactive.effect
    @reactive.event(input.variable)
    def _():
        zips = zips_in_bounds()
        if not show_markers():
            remove_heatmap()
            map.widget.add_layer(layer_heatmap())
        else:
            zip_colors = dict(zip(zips.Zipcode, zips_marker_color()))
            for x in map.widget.layers:
                if x.name.startswith("marker-"):
                    zipcode = int(x.name.split("-")[1])
                    if zipcode in zip_colors:
                        x.color = zip_colors[zipcode]

    # When bounds change, maybe add new markers
    @reactive.effect
    @reactive.event(lambda: zips_in_bounds())
    def _():
        if not show_markers():
            return
        zips = zips_in_bounds()
        if zips.empty:
            return

        # Be careful not to create markers until we know we need to add it
        current_markers = set(
            [m.name for m in map.widget.layers if m.name.startswith("marker-")]
        )
        zips["Color"] = zips_marker_color()
        for _, row in zips.iterrows():
            if ("marker-" + str(row.Zipcode)) not in current_markers:
                map.widget.add_layer(create_marker(row, color=row.Color))

    # Change from heatmap to markers: remove the heatmap and show markers
    # Change from markers to heatmap: hide the markers and add the heatmap
    @reactive.effect
    @reactive.event(show_markers)
    def _():
        if show_markers():
            map.widget.remove_layer(layer_heatmap())
        else:
            map.widget.add_layer(layer_heatmap())

        opacity = 0.6 if show_markers() else 0.0

        for x in map.widget.layers:
            if x.name.startswith("marker-"):
                x.fill_opacity = opacity
                x.opacity = opacity

    # For some reason, ipyleaflet updates bounds to an incorrect value
    # when the map is hidden, so only update the bounds when the map is visible
    current_bounds = reactive.value()

    @reactive.effect
    def _():
        bb = reactive_read(map.widget, "bounds")
        if input.navbar() != "Interactive map":
            return
        with reactive.isolate():
            current_bounds.set(bb)

    @debounce(0.3)
    @reactive.calc
    def zips_in_bounds():
        bb = req(current_bounds())

        lats = (bb[0][0], bb[1][0])
        lons = (bb[0][1], bb[1][1])
        return allzips[
            (allzips.Lat >= lats[0])
            & (allzips.Lat <= lats[1])
            & (allzips.Long >= lons[0])
            & (allzips.Long <= lons[1])
        ]

    @reactive.calc
    def zips_marker_color():
        vals = allzips[input.variable()]
        domain = (vals.min(), vals.max())
        vals_in_bb = zips_in_bounds()[input.variable()]
        return col_numeric(domain)(vals_in_bb)

    @reactive.calc
    def layer_heatmap():
        locs = allzips[["Lat", "Long", input.variable()]].to_numpy()
        return leaf.Heatmap(
            locations=locs.tolist(),
            name="heatmap",
            gradient=heatmap_gradient,
        )

    def remove_heatmap():
        for x in map.widget.layers:
            if x.name == "heatmap":
                map.widget.remove_layer(x)

    zip_selected = reactive.value(None)

    @render_plotly
    def density_score():
        return density_plot(
            allzips,
            zips_in_bounds(),
            selected=zip_selected(),
            var="Score",
            title="Overall Score",
            showlegend=True,
        )

    @render_plotly
    def density_income():
        return density_plot(
            allzips,
            zips_in_bounds(),
            selected=zip_selected(),
            var="Income"
        )

    @render_plotly
    def density_college():
        return density_plot(
            allzips,
            zips_in_bounds(),
            selected=zip_selected(),
            var="College"
        )

    @render_plotly
    def density_pop():
        return density_plot(
            allzips,
            zips_in_bounds(),
            selected=zip_selected(),
            var="Population",
            title="log10(Population)",
        )

    @render.ui
    def data_intro():
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

    @render.data_frame
    def zips_data():
        return render.DataGrid(zips_in_bounds(), selection_mode="row")

    @reactive.calc
    def selected_row():
        sel = zips_data.input_cell_selection()
        print(sel)
        if not sel["rows"]:
            return pd.DataFrame()
        return zips_data.data().iloc[sel["rows"][0]]

    @render_widget
    def table_map():
        #req(not selected_row().empty)

        return create_map()

    @reactive.effect
    @reactive.event(selected_row)
    def _():
        if selected_row().empty:
            return
        for x in table_map.widget.layers:
            if x.name.startswith("marker"):
                table_map.widget.remove_layer(x)
        m = create_marker(selected_row())
        table_map.widget.add_layer(m)

    # Utility function to create a marker
    def create_marker(row, **kwargs):
        m = leaf.CircleMarker(
            location=(row.Lat, row.Long),
            # Currently doesn't work with ipywidgets >8.0
            # https://github.com/posit-dev/py-shinywidgets/issues/101
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


app = App(app_ui, server, static_assets=app_dir / "www")
