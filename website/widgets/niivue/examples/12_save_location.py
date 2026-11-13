# `location()` is live from the moment the viewer renders, so it's safe to
# read on demand -- e.g. behind a button -- with no warm-up read beforehand.
# Click the brain, then "Bookmark this spot" at any later point; the
# crosshair position the accessor remembers is still there.
from ipyniivue import NiiVue, Volume
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_niivue

ui.page_opts(title="Bookmark the crosshair", fillable=True)
ui.input_action_button("bookmark", "Bookmark this spot")

bookmarks = reactive.Value([])


@render_niivue
def brain():
    nv = NiiVue()
    nv.load_volumes([Volume(url="https://niivue.com/demos/images/mni152.nii.gz")])
    return nv


@reactive.effect
@reactive.event(input.bookmark)
def _():
    loc = brain.location()
    if loc.get("seeded"):
        return  # nothing clicked yet -- don't bookmark the volume center
    mm = loc["mm"][:3]
    bookmarks.set([*bookmarks(), f"({mm[0]:.0f}, {mm[1]:.0f}, {mm[2]:.0f}) mm"])


@render.ui
def saved():
    if not bookmarks():
        return ui.p("No bookmarks yet.")
    return ui.tags.ul(*[ui.tags.li(b) for b in bookmarks()])
