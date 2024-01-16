import os

all = (
    "SHINYWIDGETS_CDN",
    "SHINYWIDGETS_CDN_ONLY",
    "SHINYWIDGETS_EXTENSION_WARNING",
)

# Make it easier to customize the CDN fallback (and make it CDN-only)
# https://ipywidgets.readthedocs.io/en/7.6.3/embedding.html#python-interface
# https://github.com/jupyter-widgets/ipywidgets/blob/6f6156c7/packages/html-manager/src/libembed-amd.ts#L6-L14
SHINYWIDGETS_CDN = os.getenv("SHINYWIDGETS_CDN", "https://cdn.jsdelivr.net/npm/")
SHINYWIDGETS_CDN_ONLY = os.getenv("SHINYWIDGETS_CDN_ONLY", "false").lower() == "true"
# Should shinywidgets warn if unable to find a local path to a widget extension?
SHINYWIDGETS_EXTENSION_WARNING = (
    os.getenv("SHINYWIDGETS_EXTENSION_WARNING", "false").lower() == "true"
)
