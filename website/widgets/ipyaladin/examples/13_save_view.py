# `target()`/`fov()` are seeded at render and re-seeded on every re-render,
# so they're always safe to read on demand -- e.g. behind a button -- with
# no warm-up read beforehand. Pan or zoom, then "Save this view" at any
# later point; the viewport the accessors remember is still there.
from ipyaladin import Aladin
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_ipyaladin

ui.page_opts(title="Save the current view", fillable=True)
ui.input_action_button("save", "Save this view")

views = reactive.Value([])

with ui.card(full_screen=True):

    @render_ipyaladin
    def sky():
        return Aladin(target=(83.822, -5.391), fov=1.2)  # Orion Nebula (M42)


@reactive.effect
@reactive.event(input.save)
def _():
    t, f = sky.target(), sky.fov()
    bookmark = f"ra={t.ra.deg:.2f} dec={t.dec.deg:.2f}  fov={f.deg:.2f} deg"
    views.set([*views(), bookmark])


@render.ui
def saved():
    if not views():
        return ui.p("No saved views yet.")
    return ui.tags.ul(*[ui.tags.li(v) for v in views()])
