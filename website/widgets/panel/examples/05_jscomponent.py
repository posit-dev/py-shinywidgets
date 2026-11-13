import panel as pn
import param
from shiny.express import ui
from shinywidgets import render_panel


class Counter(pn.custom.JSComponent):
    count = param.Integer(default=0)

    _esm = """
    export function render({ model, el }) {
      const button = document.createElement("button");
      const render = () => button.innerText = `Count is ${model.count}`;
      render();
      button.onclick = () => model.count += 1;
      model.on("count", render);
      el.append(button);
    }
    """


ui.page_opts(title="Custom JSComponent", fillable=True)

with ui.card():
    ui.card_header("10 lines of ESM, two-way synced with Python")

    @render_panel
    def counter():
        return Counter()
