from __future__ import annotations

import traitlets as t
from anywidget import AnyWidget
from ipywidgets.widgets.trait_types import bytes_serialization
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_widget


class BufferTransportWidget(AnyWidget):
    synced_bytes = t.Bytes(default_value=b"").tag(sync=True, **bytes_serialization)

    _esm = """
const encoder = new TextEncoder();
const updateSource = encoder.encode("00000UPDATE000");
const customSource = encoder.encode("zzCUSTOMbuffer");

function render({ model, el }) {
  el.innerHTML = `
    <div class="buffer-transport-widget" style="display:flex; flex-direction:column; gap:0.25rem;">
      <button type="button" data-testid="update-buffer-button">
        Send trait update
      </button>
      <button type="button" data-testid="custom-buffer-button">
        Send sliced custom buffer
      </button>
      <div data-testid="client-payload"></div>
    </div>
  `;

  const updateButton = el.querySelector("[data-testid='update-buffer-button']");
  const customButton = el.querySelector("[data-testid='custom-buffer-button']");
  const payload = el.querySelector("[data-testid='client-payload']");
  const showPayload = () => {
    const bytes = model.get("synced_bytes");
    payload.textContent = bytes?.byteLength ?
      new TextDecoder().decode(bytes) : "none";
  };
  model.on("change:synced_bytes", showPayload);
  showPayload();

  updateButton.addEventListener("click", () => {
    const slice = new DataView(updateSource.buffer, 5, 6);
    model.set("synced_bytes", slice);
    model.save_changes();
  });

  customButton.addEventListener("click", () => {
    const slice = new Uint8Array(customSource.buffer, 2, 6);
    model.send({ type: "custom-buffer" }, undefined, [slice]);
  });

  return () => model.off("change:synced_bytes", showPayload);
}

export default { render };
"""


def _normalize_payload(payload: bytes | memoryview) -> bytes:
    if isinstance(payload, memoryview):
        return payload.tobytes()
    return payload


def _format_status(payload: bytes | memoryview) -> str:
    payload = _normalize_payload(payload)
    return f"{len(payload)} bytes" if payload else "empty"


def _format_payload(payload: bytes | memoryview) -> str:
    payload = _normalize_payload(payload)
    if not payload:
        return "none"
    return payload.decode("utf-8", errors="replace")


app_ui = ui.page_fluid(
    ui.input_action_button("toggle_null", "Toggle null"),
    ui.input_action_button("server_buffer", "Send server buffer"),
    output_widget("buffer_widget"),
    ui.output_text("update_status"),
    ui.output_text("update_payload"),
    ui.output_text("custom_status"),
    ui.output_text("custom_payload"),
)


def server(input, output, session):
    buffer_transport_widget = BufferTransportWidget()

    @reactive.effect
    @reactive.event(input.server_buffer)
    def send_server_buffer():
        buffer_transport_widget.synced_bytes = b"SERVER-REPLY"

    custom_buffer_payload = reactive.Value(b"", name="custom_buffer_payload")
    show_null = reactive.value(False)

    @reactive.effect
    @reactive.event(input.toggle_null)
    def _():
        show_null.set(not show_null.get())

    @buffer_transport_widget.on_msg
    def _handle_custom_buffer(_, content, buffers):
        if content.get("type") != "custom-buffer":
            return
        if not buffers:
            custom_buffer_payload.set(b"")
            return
        custom_buffer_payload.set(bytes(buffers[0]))

    @render_widget
    def buffer_widget():
        if show_null.get():
            return None
        return buffer_transport_widget

    @render.text
    def update_status():
        data = reactive_read(buffer_transport_widget, "synced_bytes")
        return _format_status(data)

    @render.text
    def update_payload():
        data = reactive_read(buffer_transport_widget, "synced_bytes")
        return _format_payload(data)

    @render.text
    def custom_status():
        return _format_status(custom_buffer_payload())

    @render.text
    def custom_payload():
        return _format_payload(custom_buffer_payload())


app = App(app_ui, server)
