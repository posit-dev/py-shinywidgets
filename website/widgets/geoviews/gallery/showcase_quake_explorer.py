# Title: Ring of Fire quake explorer
# A dashboard combining every interaction recipe from the guide: a magnitude
# slider drives an in-place Pipe update (preserves zoom), box-select drives
# value boxes and a table via BoundsXY, and a click drives a detail card via
# Tap -- all on the same 6,000-point synthetic earthquake map.
# Bucket: showcase
# Run: cd to the shinywidgets repo root, then
#   uv run --with geoviews --with cartopy shiny run docs/widget-guides/geoviews/gallery/showcase_quake_explorer.py
# Data: synthetic (plausible tectonic-belt point cloud; see the guide's
#   "Performance with large point sets" section for why this is synthetic).
import geoviews as gv
import holoviews as hv
import numpy as np
import pandas as pd
from shiny import reactive
from shiny.express import input, render, ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

rng = np.random.default_rng(1)
BELTS = [
    np.array([(-70, -55), (-71, -33), (-75, -10), (-80, 5), (-90, 15),
               (-100, 20), (-120, 35), (-125, 48), (-150, 60), (-170, 55)]),
    np.array([(170, 52), (150, 45), (140, 35), (130, 30), (125, 10),
               (120, 0), (110, -8), (130, -8), (150, -10), (170, -15), (178, -20)]),
]
lons, lats = [], []
for belt in BELTS:
    for a, b in zip(belt[:-1], belt[1:]):
        t = rng.uniform(0, 1, 320)
        seg = a * (1 - t[:, None]) + b * t[:, None] + rng.normal(0, 1.5, (320, 2))
        lons.append(seg[:, 0])
        lats.append(seg[:, 1])
lons, lats = np.concatenate(lons), np.concatenate(lats)
n = len(lons)
mag = rng.exponential(0.6, n).clip(0, 4) + 4.0
depth = rng.gamma(2.0, 60, n).clip(0, 700)
region = np.where(lons < -50, "Americas", "Asia-Pacific")

ui.page_opts(title="Ring of Fire quake explorer", fillable=True)
ui.input_slider("min_mag", "Minimum magnitude", min=4.0, max=7.5, value=4.0, step=0.5)

pipe = hv.streams.Pipe(data={"lon": lons, "lat": lats, "mag": mag, "depth": depth, "region": region})
bounds_val = reactive.value(None)
tap_xy = reactive.value(None)


def quake_points(data):
    return gv.Points(data, kdims=["lon", "lat"], vdims=["mag", "depth", "region"]).opts(
        color="depth", cmap="fire_r", size=hv.dim("mag") * 1.5, alpha=0.6,
        colorbar=True, tools=["hover", "tap", "box_select"],
        active_tools=["box_select", "tap"],
    )


with ui.layout_columns(fill=False):
    with ui.value_box():
        "Quakes selected"

        @render.text
        def n_selected():
            return str(len(selected()))

    with ui.value_box():
        "Strongest in selection"

        @render.text
        def strongest():
            sel = selected()
            return f"M{sel.mag.max():.1f}" if len(sel) else "-"

    with ui.value_box():
        "Deeper than 70 km"

        @render.text
        def deep_pct():
            sel = selected()
            return f"{(sel.depth > 70).mean():.0%}" if len(sel) else "-"

with ui.card(full_screen=True):
    ui.card_header("6,000 synthetic quakes (box-select or click)")

    # Kept full width as a layout preference, not a workaround -- box-select
    # works the same in a narrower column too (see Gotchas: the earlier
    # "narrow canvas breaks BoundsXY" claim was a test-methodology artifact,
    # retracted).
    @render_holoviews
    def map():
        dmap = hv.DynamicMap(quake_points, streams=[pipe])
        # Attach Tap/BoundsXY to the DynamicMap itself, once, rather than
        # to the element returned from inside its callback: a fresh
        # per-call stream instance never gets wired to the live plot.
        hv.streams.Tap(source=dmap).add_subscriber(lambda x, y: tap_xy.set((x, y)))
        hv.streams.BoundsXY(source=dmap).add_subscriber(
            lambda bounds: bounds_val.set(bounds)
        )
        return (gv.tile_sources.EsriWorldDarkGrayBase * dmap).opts(responsive=True)

with ui.layout_columns():
    with ui.card():
        ui.card_header("Clicked: nearest quake")

        @render.ui
        def detail():
            xy = tap_xy()
            if xy is None:
                return ui.p("Click a point on the map.", class_="text-muted")
            x, y = xy
            visible = selected()
            if not len(visible):
                return ui.p("No quakes in the current filter.", class_="text-muted")
            dist = (visible.lon - x) ** 2 + (visible.lat - y) ** 2
            row = visible.loc[dist.idxmin()]
            return ui.TagList(
                ui.h5(f"M{row.mag:.1f}, {row.depth:.0f} km deep"),
                ui.p(f"{row.region}, {row.lat:.2f}, {row.lon:.2f}"),
            )

    with ui.card():
        ui.card_header("Box-selected quakes, by region")

        @render.data_frame
        def table():
            sel = selected()
            if not len(sel):
                return sel
            summary = (
                sel.groupby("region")
                .agg(n=("mag", "size"), avg_mag=("mag", "mean"), max_mag=("mag", "max"))
                .reset_index()
                .round(2)
            )
            return render.DataGrid(summary)


@reactive.calc
def filtered():
    mask = mag >= input.min_mag()
    return pd.DataFrame(
        {"lon": lons[mask], "lat": lats[mask], "mag": mag[mask],
         "depth": depth[mask], "region": region[mask]}
    )


@reactive.calc
def selected():
    df = filtered()
    b = bounds_val()
    if b is None:
        return df
    x0, y0, x1, y1 = b
    return df[df.lon.between(x0, x1) & df.lat.between(y0, y1)]


@reactive.effect
def _():
    pipe.send(filtered().to_dict("series"))
