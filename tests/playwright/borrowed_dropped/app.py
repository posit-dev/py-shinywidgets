import ipywidgets as W
from ipywidgets.widgets.widget import _instances
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget

# A session-owned container whose one child is rebuilt on every render. When a
# render is invalidated, the old child is still referenced by the live
# container, so it's kept rather than closed; the render then replaces the
# child right after. The kept widget must be re-examined at the next sweep,
# or one child leaks per re-render.
app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("server_widgets"),
    output_widget("out"),
)


def server(input, output, session):
    container = W.VBox()

    @render_widget
    def out():
        n = input.rerender()
        container.children = (W.Button(description=f"child {n}"),)
        return container

    @render.text
    def server_widgets():
        reactive.invalidate_later(0.25)
        return str(len(_instances))


app = App(app_ui, server)
