# Three lifetimes for a widget:
#
# - Default (render-scoped): a widget built directly in the render function
#   is closed and replaced every time that function runs. "Re-render" here
#   rebuilds the map from scratch, so any zoom/pan the user did is gone.
# - session_lifetime(): build the map ONCE per session (cached in a
#   `@reactive.calc`, which only recomputes if something it reads changes),
#   and keep returning that same instance. "Re-render" redisplays the same
#   Map, so the user's zoom/pan survives.
# - shared_lifetime(): built once, before any session exists, and shown to
#   every session. One user's pan/zoom changes it for everyone -- open this
#   app in two tabs and zoom one to see the other move.
#
# THE_SHARED_MAP lives in the sibling `globals.py`, not here. Express re-runs
# THIS file's body for every session (see globals.py's comment); a
# `shared_lifetime()` widget constructed directly in it would be rebuilt --
# and re-shown as a fresh, independent map -- on every new session, which
# defeats the whole point (each session would silently get its own map,
# never mirroring another session's interaction).
from globals import THE_SHARED_MAP
from ipyleaflet import Map
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_ipyleaflet, session_lifetime

ui.page_opts(title="Lifetimes", fillable=True)
ui.input_action_button("rerender", "Re-render (default + cached)")

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Default lifetime: zoom resets on re-render")

        @render_ipyleaflet
        @reactive.event(input.rerender, ignore_none=False)
        def default_map():
            return Map(center=(45.5, -122.6), zoom=9)

    with ui.card(full_screen=True):
        ui.card_header("session_lifetime(): zoom survives re-render")

        @reactive.calc
        def cached_map_calc():
            with session_lifetime():
                return Map(center=(45.5, -122.6), zoom=9)

        @render_ipyleaflet
        @reactive.event(input.rerender, ignore_none=False)
        def cached_map():
            return cached_map_calc()

    with ui.card(full_screen=True):
        ui.card_header("shared_lifetime(): every session shows (and can move) this map")

        @render_ipyleaflet
        def shared_map():
            return THE_SHARED_MAP
