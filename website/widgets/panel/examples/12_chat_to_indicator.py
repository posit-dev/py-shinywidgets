import panel as pn
from shiny import reactive
from shiny.express import ui
from shinywidgets import render_panel


def canned_reply(contents: str, user: str, instance: pn.chat.ChatInterface):
    return f"Got it: \"{contents}\""


ui.page_opts(title="Chat activity drives an indicator", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Chat")

        @render_panel
        def chat():
            return pn.chat.ChatInterface(
                callback=canned_reply, show_rerun=False, show_undo=False,
                sizing_mode="stretch_both",
            )

    with ui.card():
        ui.card_header("Messages so far (a different Panel widget, updated in place)")

        @render_panel
        def counter():
            return pn.indicators.Number(
                name="Messages", value=0, sizing_mode="stretch_width",
            )


@reactive.effect
def _():
    counter.value.value = len(chat.param("objects"))
