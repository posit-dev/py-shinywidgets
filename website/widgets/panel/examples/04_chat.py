import panel as pn
from shiny.express import ui
from shinywidgets import render_panel

ui.page_opts(title="Panel chat", fillable=True)


def canned_reply(contents: str, user: str, instance: pn.chat.ChatInterface):
    words = len(contents.split())
    return f"You said {words} word{'s' if words != 1 else ''}: \"{contents}\""


with ui.card(full_screen=True):
    ui.card_header("pn.chat.ChatInterface -- no LLM, no Panel server")

    @render_panel
    def chat():
        return pn.chat.ChatInterface(
            callback=canned_reply,
            show_rerun=False,
            show_undo=False,
            sizing_mode="stretch_both",
        )
