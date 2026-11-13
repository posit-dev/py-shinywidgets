import nglview
from shiny.express import render, ui
from shinywidgets import render_nglview

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_nglview
        def structure():
            view = nglview.show_file(nglview.datafiles.PDB)
            view.center()
            return view

    with ui.card():
        ui.card_header("Camera orientation (drag to rotate)")

        @render.code
        def orientation():
            # A 4x4 matrix (16 floats), updated ~100ms after the user stops
            # dragging/scrolling/panning the view
            matrix = structure.read("_camera_orientation")
            return "\n".join(
                " ".join(f"{v: .2f}" for v in matrix[i : i + 4])
                for i in range(0, len(matrix), 4)
            )
