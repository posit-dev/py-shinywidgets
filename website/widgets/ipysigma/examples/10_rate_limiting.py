from __future__ import annotations

import networkx as nx
from ipysigma import Sigma
from shiny import reactive, req
from shiny.express import render, ui
from shinywidgets import render_ipysigma

# rate_policy/rate_delay rate-limit .read() (and reactive_read()) on the
# *widget*: every reader of it shares the limit, so comparing rate-limited
# vs. not needs two widgets. sync_key mirrors camera (and selection) between
# them in the browser, so panning either one pans both.
G = nx.karate_club_graph()

ui.page_opts(title="ipysigma rate limiting", fillable=True)

with ui.layout_columns(col_widths=[6, 6]):
    with ui.card(full_screen=True):
        ui.card_header("Drag me -- not rate-limited")

        @render_ipysigma
        def unthrottled():
            return Sigma(G, sync_key="cam")

    with ui.card(full_screen=True):
        ui.card_header("Same camera, throttled to 1 read per 2 seconds")

        @render_ipysigma(rate_policy="throttle", rate_delay=2)
        def throttled():
            return Sigma(G, sync_key="cam")

with ui.card():
    ui.card_header("camera_state change count, same drag")

    @render.code
    def counts():
        return f"unthrottled reads: {unthrottled_count()}\nthrottled reads:   {throttled_count()}"


unthrottled_count = reactive.value(0)
throttled_count = reactive.value(0)


@reactive.effect
def _count_unthrottled():
    req(unthrottled.widget)
    unthrottled.read("camera_state")
    with reactive.isolate():
        unthrottled_count.set(unthrottled_count() + 1)


@reactive.effect
def _count_throttled():
    req(throttled.widget)
    throttled.read("camera_state")
    with reactive.isolate():
        throttled_count.set(throttled_count() + 1)
