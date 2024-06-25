
static_dir <- file.path(getwd(), "shinywidgets", "static")
if (!dir.exists(static_dir)) dir.create(static_dir)
# From https://github.com/jupyter-widgets/ipywidgets/blob/fbdbd005/python/ipywidgets/ipywidgets/embed.py#L62
# Note that we also grab libembed-amd, not embed-amd, because the Shiny bindings handle the actual rendering aspect
# https://github.com/jupyter-widgets/ipywidgets/blob/fbdbd00/packages/html-manager/scripts/concat-amd-build.js#L6
# TODO: minify the bundle and import the version via `from ipywidgets._version import __html_manager_version__`
download.file(
  "https://unpkg.com/@jupyter-widgets/html-manager@1.0.7/dist/libembed-amd.js",
  file.path(static_dir, "libembed-amd.js")
)
