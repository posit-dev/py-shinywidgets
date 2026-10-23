from mosaic_widget import MosaicWidget
from shinywidgets import render_mosaic_widget

@render_mosaic_widget
def ok():
    return MosaicWidget({})

reveal_type(ok.widget)
reveal_type(ok.value)

@render_mosaic_widget
def bad():
    return {"plot": []}

@render_mosaic_widget(height="300px")
def ok2() -> MosaicWidget:
    return MosaicWidget({})
reveal_type(ok2.widget)
