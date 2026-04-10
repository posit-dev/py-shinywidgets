from __future__ import annotations

import ipywidgets as widgets
from collections.abc import Mapping
from shiny import App, render, ui
from shinywidgets import output_widget, reactive_read, render_widget


app_ui = ui.page_fluid(
    output_widget("uploader"),
    ui.output_text("status"),
    ui.output_text("name"),
    ui.output_text("size"),
    ui.output_text("content"),
)


def server(input, output, session):
    uploader_widget = widgets.FileUpload(multiple=False)

    def _first_upload_entry():
        value = reactive_read(uploader_widget, "value")
        if not value:
            return None
        if isinstance(value, Mapping):
            return next(iter(value.values()), None)
        try:
            return value[0]
        except (TypeError, IndexError, KeyError):
            return None

    @render_widget
    def uploader():
        return uploader_widget

    @render.text
    def status():
        return "uploaded" if _first_upload_entry() else "empty"

    @render.text
    def name():
        entry = _first_upload_entry()
        if not entry:
            return ""
        return entry["name"]

    @render.text
    def size():
        entry = _first_upload_entry()
        if not entry:
            return ""
        return str(entry["size"])

    @render.text
    def content():
        entry = _first_upload_entry()
        if not entry:
            return ""
        return entry["content"].tobytes().decode("utf-8")


app = App(app_ui, server)
