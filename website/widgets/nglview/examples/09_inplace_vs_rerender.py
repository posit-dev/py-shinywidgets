import nglview
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_nglview

ui.page_opts(fillable=True)

ui.input_action_button("restyle", "Restyle in place (keeps camera)")
ui.input_action_button("rerender", "Rerender (resets camera)")

rerender_count = reactive.value(0)

with ui.card(full_screen=True):

    @render_nglview
    def structure():
        rerender_count()  # a dependency here forces a full rebuild on "Rerender"
        view = nglview.show_file(nglview.datafiles.PDB, default_representation=False)
        view.add_representation("cartoon", color="lightgrey")
        view.center()
        return view

    @reactive.effect
    @reactive.event(input.rerender)
    def _force_rerender():
        rerender_count.set(rerender_count.get() + 1)

    # Changes representation without touching the render function, so the
    # camera (position, rotation, zoom) the user set by dragging is untouched
    @reactive.effect
    @reactive.event(input.restyle)
    def _restyle_in_place():
        view = structure.widget
        if view is not None:
            view.clear_representations()
            view.add_representation("surface", color="skyblue", opacity=0.6)
