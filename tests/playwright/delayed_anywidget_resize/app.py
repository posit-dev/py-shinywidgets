from __future__ import annotations

import traitlets as t
from anywidget import AnyWidget
from shiny import App, render, ui
from shinywidgets import output_widget, reactive_read, render_widget


class DelayedRenderWidget(AnyWidget):
    ready_count = t.Int(0).tag(sync=True)
    resize_after_ready = t.Int(0).tag(sync=True)

    _esm = """
function render({ model, el }) {
  const root = document.createElement("div");
  root.className = "delayed-render-root";
  el.appendChild(root);

  let ready = false;
  const onResize = () => {
    if (!ready) return;
    model.set("resize_after_ready", model.get("resize_after_ready") + 1);
    model.save_changes();
  };

  window.addEventListener("resize", onResize);

  setTimeout(() => {
    const child = document.createElement("div");
    child.className = "delayed-render-child";
    child.textContent = "ready";
    root.appendChild(child);
    ready = true;
    model.set("ready_count", model.get("ready_count") + 1);
    model.save_changes();
  }, 50);

  return () => window.removeEventListener("resize", onResize);
}

export default { render };
"""


app_ui = ui.page_fluid(
    output_widget("delayed_widget"),
    ui.output_text("ready_count"),
    ui.output_text("resize_after_ready"),
)


def server(input, output, session):
    widget = DelayedRenderWidget()

    @render_widget
    def delayed_widget():
        return widget

    @render.text
    def ready_count():
        return str(reactive_read(widget, "ready_count"))

    @render.text
    def resize_after_ready():
        return str(reactive_read(widget, "resize_after_ready"))


app = App(app_ui, server)
