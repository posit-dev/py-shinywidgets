# Shiny Express re-runs 03_lifetimes.py's whole body for every new session
# (that's what lets each session get its own `reactive.value()`s). A
# `shared_lifetime()` widget must be built once for the whole process, so it
# cannot live directly in that file -- it would be rebuilt per session,
# defeating the point. Express imports a sibling `globals.py` before any
# session connects, but NOT necessarily exactly once (it can run at least
# twice: once while Express builds the page's static UI, again per session
# import) -- see "Lifetimes" above for what happens if you skip this file,
# and for why setup here must be idempotent rather than one-shot.
from ipyleaflet import Map
from shinywidgets import shared_lifetime

with shared_lifetime():
    THE_SHARED_MAP = Map(center=(48.85, 2.35), zoom=11)
