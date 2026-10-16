# Regenerate the served runtime/output bundles from source.
#
# The widget runtime (shinywidgets/static/libembed-amd.js) is built from
# js/src/runtime.ts -- one coherent compilation of the official
# @jupyter-widgets packages plus the internals our lifecycle code imports.
# It must NOT be refreshed by downloading the upstream
# @jupyter-widgets/html-manager libembed-amd.js bundle: that bundle lacks the
# "shinywidgets-runtime" module exports and would silently break the AMD
# aliases defined by runtime-register.js.

static_dir <- file.path(getwd(), "shinywidgets", "static")
if (!dir.exists(static_dir)) dir.create(static_dir)

run <- function(args) {
  status <- system2("yarn", args)
  if (!identical(status, 0L)) {
    stop("Command failed: yarn ", paste(args, collapse = " "))
  }
}

# The webpack build copies js/dist/* into shinywidgets/static/.
run(c("--cwd", "js", "install", "--frozen-lockfile"))
run(c("--cwd", "js", "build"))
