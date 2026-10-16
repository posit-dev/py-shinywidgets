from shiny import App, ui
from shinywidgets import output_widget

app = App(
    ui.page_fluid(output_widget("widget")),
    lambda input, output, session: None,
)
