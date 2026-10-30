"""itkwidgets (experimental): 3D volume rendering in Shiny.

Requires:
    pip install 'itkwidgets>=1.0a55' 'numcodecs<0.13' 'ngff-zarr<0.15' urllib3

The default viewer frontend URL (itkwidgets.viewer_config.ITK_VIEWER_SRC) is
an IPFS public gateway that is currently unreliable. For reliable rendering,
serve itk-vtk-viewer@14.51.0's dist/ yourself and point ITK_VIEWER_SRC at it:

    npm pack itk-vtk-viewer@14.51.0 && tar xzf itk-vtk-viewer-14.51.0.tgz
    ITK_VIEWER_SRC=/itk-vtk-viewer/index.html shiny run app.py \
        --static-assets /itk-vtk-viewer=package/dist
"""

import asyncio

import numpy as np
from shiny import App, reactive, render, ui

from shinywidgets.experimental import itkwidgets as sw_itk


def make_volume(seed=0):
    rng = np.random.default_rng(seed)
    y, x, z = np.mgrid[:64, :64, :64]
    img = np.zeros((64, 64, 64), dtype=np.float32)
    img[16:48, 16:48, 16:48] = 1000.0
    img[24:40, 24:40, 24:40] = 200.0
    cx, cy, cz = rng.integers(10, 54, 3)
    ball = ((x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2 < 100).astype(np.float32) * 700
    return np.maximum(img, ball).astype(np.float32)


def make_label_image():
    lbl = np.zeros((64, 64, 64), dtype=np.uint8)
    lbl[20:44, 20:44, 20:44] = 1
    lbl[28:36, 28:36, 28:36] = 2
    return lbl


def make_point_set():
    rng = np.random.default_rng(1)
    return rng.uniform(8, 56, size=(30, 3)).astype(np.float32)


app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_select(
            "cmap",
            "Colormap",
            choices=[
                "Viridis (matplotlib)",
                "Inferno (matplotlib)",
                "Grayscale",
                "X Ray",
                "jet",
                "Cool to Warm",
            ],
        ),
        ui.input_select(
            "view_mode", "View mode", choices=["Volume", "XPlane", "YPlane", "ZPlane"]
        ),
        ui.input_slider("zslice", "Z slice", min=0, max=63, value=32),
        ui.input_switch("rotate", "Rotate", False),
        ui.input_action_button("replace", "Replace image (set_image)"),
        ui.input_action_button("label", "Toggle label image"),
        ui.input_action_button("points", "Toggle point set"),
        ui.hr(),
        ui.output_text_verbatim("events"),
    ),
    sw_itk.imjoy_head(),
    ui.card(
        ui.card_header("itkwidgets Viewer (imjoy-rpc over Shiny)"),
        ui.output_ui("viewer"),
        height="600px",
        full_screen=True,
    ),
    title="itkwidgets + Shiny (experimental)",
)


def server(input, output, session):
    sw_itk.register_imjoy_session(session, input)
    events_log = reactive.Value([])

    def log_event(msg):
        # isolate(): this is called from asyncio tasks that captured the
        # render's reactive context via contextvars; an un-isolated read here
        # silently registers a dependency and causes a re-render loop.
        with reactive.isolate():
            events_log.set((events_log() + [msg])[-10:])

    @render.ui
    def viewer():
        from itkwidgets import Viewer

        v = Viewer(image=make_volume())
        session._itk_viewer = v  # keep alive

        # Register browser->Python event listeners once the plugin API is up.
        async def register_events():
            for _ in range(200):
                if v.has_viewer:
                    break
                await asyncio.sleep(0.1)
            if not v.has_viewer:
                log_event("viewer never became ready")
                return
            itk_viewer = v.viewer_rpc.itk_viewer

            # imjoy-rpc encodes function arguments as single-use callbacks,
            # so each handler re-registers itself after firing.
            def on_zslice(data):
                log_event(f"zSliceChanged: {data}")
                itk_viewer.registerEventListener("zSliceChanged", on_zslice)

            def on_cmap(data):
                log_event(f"imageColorMapChanged: {data}")
                itk_viewer.registerEventListener("imageColorMapChanged", on_cmap)

            itk_viewer.registerEventListener("zSliceChanged", on_zslice)
            itk_viewer.registerEventListener("imageColorMapChanged", on_cmap)
            log_event("event listeners registered")

        asyncio.get_running_loop().create_task(register_events())
        return sw_itk.render_viewer(session, v)

    @reactive.effect
    @reactive.event(input.cmap)
    def _cmap():
        v = getattr(session, "_itk_viewer", None)
        if v is not None:
            v.set_image_color_map(input.cmap())

    @reactive.effect
    @reactive.event(input.view_mode)
    def _vm():
        v = getattr(session, "_itk_viewer", None)
        if v is not None:
            v.set_view_mode(input.view_mode())

    @reactive.effect
    @reactive.event(input.zslice)
    def _zs():
        v = getattr(session, "_itk_viewer", None)
        if v is not None:
            v.set_z_slice(input.zslice())

    @reactive.effect
    @reactive.event(input.rotate)
    def _rot():
        v = getattr(session, "_itk_viewer", None)
        if v is not None:
            v.set_rotate(input.rotate())

    @reactive.effect
    @reactive.event(input.replace)
    def _replace():
        v = getattr(session, "_itk_viewer", None)
        if v is not None:
            v.set_image(make_volume(seed=input.replace()))
            log_event(f"set_image (n={input.replace()})")

    @reactive.effect
    @reactive.event(input.label)
    def _label():
        v = getattr(session, "_itk_viewer", None)
        if v is not None:
            if input.label() % 2 == 1:
                v.set_label_image(make_label_image())
                v.set_label_image_blend(0.7)
                log_event("label image set")
            else:
                v.set_label_image(np.zeros((2, 2, 2), dtype=np.uint8))
                log_event("label image cleared")

    @reactive.effect
    @reactive.event(input.points)
    def _points():
        v = getattr(session, "_itk_viewer", None)
        if v is not None:
            if input.points() % 2 == 1:
                v.set_point_set(make_point_set())
                log_event("point set added")
            else:
                v.set_point_set(np.zeros((1, 3), dtype=np.float32))
                log_event("point set cleared")

    @render.text
    def events():
        return "\n".join(events_log()) or "(no events yet)"


app = App(app_ui, server)
