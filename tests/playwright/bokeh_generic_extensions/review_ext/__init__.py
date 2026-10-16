from bokeh.models import Div

__version__ = "1.0.0"


class ExtensionDiv(Div):
    __view_module__ = "review_ext"
    __javascript__ = ["static/extensions/review_ext/helper@1.js"]
    __css__ = ["static/extensions/review_ext/style@1.css"]
