from __future__ import annotations

from astropy.table import Table
from ipyaladin import Aladin
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_ipyaladin

# clicked_object() is read only behind an action button, so nothing reads the
# accessor before the test clicks a catalog source. That exercises the
# render-time attach: ipyaladin's frontend retains the last clicked
# source in the synced `clicked_object` trait, so a click made before the
# first read must be reflected in that read (see test_ipyaladin_clicked_seed).

# One catalog source, exactly at each viewer's target (so a center-canvas
# click hits it); the two viewers use different coordinates so a leak across
# instances would show up as the wrong coordinates
CATALOG1 = Table({"ra": [83.63], "dec": [22.01], "name": ["one"]})
CATALOG2 = Table({"ra": [10.0], "dec": [40.0], "name": ["two"]})

app_ui = ui.page_fluid(
    ui.input_action_button("read_clicks", "Read clicks"),
    ui.output_text("gated1"),
    ui.output_text("gated2"),
    ui.output_text("synced1"),
    output_widget("sky1", height="300px"),
    output_widget("sky2", height="300px"),
)


def fmt(d: object) -> str:
    if not d:
        return "None"
    return f"{d['ra']:.2f},{d['dec']:.2f}"  # pyright: ignore[reportIndexIssue]


def server(input, output, session):
    @render_ipyaladin
    def sky1():
        aladin = Aladin(target=(83.63, 22.01), fov=2)
        aladin.add_table(CATALOG1)
        return aladin

    @render_ipyaladin
    def sky2():
        aladin = Aladin(target=(10.0, 40.0), fov=2)
        aladin.add_table(CATALOG2)
        return aladin

    # Sentinel: reads the synced trait directly, NOT the clicked_object()
    # accessor, so the test can wait until the click has synced from browser
    # to server while the accessor itself stays unread until the gated read
    @render.text
    def synced1():
        return fmt(reactive_read(sky1.widget, "clicked_object"))

    @render.text
    @reactive.event(input.read_clicks)
    def gated1():
        return fmt(sky1.clicked_object())

    @render.text
    @reactive.event(input.read_clicks)
    def gated2():
        return fmt(sky2.clicked_object())


app = App(app_ui, server)
