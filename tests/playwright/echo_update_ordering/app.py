from __future__ import annotations

import traitlets as t
from anywidget import AnyWidget
from shiny import App, render, ui
from shinywidgets import output_widget, reactive_read, render_widget


class BurstWidget(AnyWidget):
    count = t.Int(0).tag(sync=True)

    # Writes the trait several times in a row, like widgets that sync their
    # state on every internal change (e.g. kepler.gl's config), and records
    # every value the browser-side model takes afterwards.
    _esm = """
function render({ model, el }) {
  el.innerHTML = `
    <button type="button" data-testid="burst">Burst</button>
    <div data-testid="history"></div>
  `;
  const history = el.querySelector("[data-testid='history']");
  const seen = [];
  model.on("change:count", () => {
    seen.push(model.get("count"));
    history.textContent = seen.join(",");
  });
  el.querySelector("[data-testid='burst']").addEventListener("click", () => {
    for (let i = 1; i <= 5; i++) {
      model.set("count", i);
      model.save_changes();
    }
  });
}

export default { render };
"""


app_ui = ui.page_fluid(output_widget("burst"), ui.output_text("server_count"))


def server(input, output, session):
    widget = BurstWidget()

    @render_widget
    def burst():
        return widget

    @render.text
    def server_count():
        return f"server: {reactive_read(widget, 'count')}"


app = App(app_ui, server)
