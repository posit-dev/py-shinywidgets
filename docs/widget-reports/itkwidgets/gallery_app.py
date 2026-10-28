"""Gallery app: itkwidgets 3D volume rendering in Shiny (experimental).

Run:
    pip install 'itkwidgets>=1.0a55' 'numcodecs<0.13' 'ngff-zarr<0.15' urllib3
    # Serve itk-vtk-viewer@14.51.0 dist/ as static assets (see report.md), then:
    ITK_VIEWER_SRC=/itk-vtk-viewer/index.html shiny run gallery_app.py
"""

import numpy as np
from shiny import App, reactive, render, ui

from shinywidgets.experimental import itkwidgets as sw_itk


def phantom(n=128):
    """A head-like phantom: bright skull shell, mid tissue, dark ventricles."""
    y, x, z = np.mgrid[:n, :n, :n].astype(np.float32)
    c = (n - 1) / 2
    r = np.sqrt(((x - c) * 1.15) ** 2 + ((y - c) * 0.9) ** 2 + (z - c) ** 2) / c
    img = np.zeros_like(r)
    img[r < 0.92] = 500  # tissue
    img[(r >= 0.92) & (r < 1.0)] = 1400  # skull
    # ventricles: two dark blobs
    v1 = ((x - c - 18) ** 2 + (y - c) ** 2 + (z - c) ** 2) < 14**2
    v2 = ((x - c + 18) ** 2 + (y - c) ** 2 + (z - c) ** 2) < 14**2
    img[v1 | v2] = 80
    rng = np.random.default_rng(7)
    img += rng.normal(0, 25, img.shape)
    # tumor label
    lbl = np.zeros(img.shape, dtype=np.uint8)
    t = ((x - c + 28) ** 2 + (y - c - 22) ** 2 + (z - c - 8) ** 2) < 12**2
    lbl[t] = 1
    # landmark points
    pts = (rng.uniform(0.25, 0.75, (12, 3)) * n).astype(np.float32)
    return img.astype(np.float32), lbl, pts


img, lbl, pts = phantom()

app_ui = ui.page_fillable(
    sw_itk.imjoy_head(),
    ui.card(
        ui.card_header(
            "itkwidgets volume viewer ",
            ui.tags.span("EXPERIMENTAL", class_="badge text-bg-warning"),
            class_="d-flex justify-content-between align-items-center",
        ),
        ui.output_ui("viewer", fill=True),
        ui.card_footer(
            ui.layout_columns(
                ui.input_select(
                    "cmap",
                    None,
                    choices=[
                        "Viridis (matplotlib)",
                        "Inferno (matplotlib)",
                        "X Ray",
                        "Cool to Warm",
                        "Grayscale",
                    ],
                    width="100%",
                ),
                ui.input_slider(
                    "blend", "Label blend", min=0, max=1, value=0.5, step=0.05,
                    width="100%",
                ),
                ui.input_switch("rotate", "Rotate", False),
                col_widths=(5, 5, 2),
            )
        ),
        full_screen=True,
        class_="bg-dark text-light border-secondary",
    ),
    ui.tags.style("body { background: #15181d; }"),
    title="itkwidgets gallery",
)


def server(input, output, session):
    sw_itk.register_imjoy_session(session, input)

    @render.ui
    def viewer():
        from itkwidgets import Viewer

        v = Viewer(
            image=img,
            label_image=lbl,
            point_sets=[pts],
            ui_collapsed=True,
            bg_color=[0.09, 0.1, 0.12, 1.0],
        )
        session._v = v
        return sw_itk.render_viewer(session, v)

    @reactive.effect
    def _cmap():
        v = getattr(session, "_v", None)
        if v is not None and v.has_viewer:
            v.set_image_color_map(input.cmap())

    @reactive.effect
    def _blend():
        v = getattr(session, "_v", None)
        if v is not None and v.has_viewer:
            v.set_label_image_blend(input.blend())

    @reactive.effect
    def _rot():
        v = getattr(session, "_v", None)
        if v is not None and v.has_viewer:
            v.set_rotate(input.rotate())


app = App(app_ui, server)
