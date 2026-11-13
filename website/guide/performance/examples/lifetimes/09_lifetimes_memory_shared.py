from globals import SHARED_MAP
from shiny.express import ui
from shinywidgets import render_lonboard

ui.page_opts(title="memory: shared_lifetime widget", fillable=True)


@render_lonboard
def map():
    # Every session is shown the SAME Map instance (built once, at import
    # time, in globals.py -- see the "Lifetimes" article's shared_lifetime()
    # + Express gotcha for why it can't be built directly in this file).
    # Memory for this widget does not scale with the number of concurrent
    # sessions.
    return SHARED_MAP
