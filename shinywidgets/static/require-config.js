// First script of the ipywidget-output-binding dependency.
//
// The widget runtime is built from source (js/src/runtime.ts) into
// libembed-amd.js, which executes as a plain script and exposes
// window.shinywidgetsRuntime. runtime-register.js then defines the official
// @jupyter-widgets/* AMD module IDs (and "shinywidgets-internals") as aliases
// of that runtime, so require()-based third-party widgets and output.js share
// the exact same constructors.
//
// The bundles derive their asset URLs (fonts, dynamic chunks) from their own
// script URLs (webpack publicPath "auto"), so -- unlike the previously
// downloaded libembed-amd.js bundle -- no require.config({paths}) seeding is
// needed here. This file remains the documented first script of the
// dependency so the load order stays explicit:
// require-config.js -> libembed-amd.js -> runtime-register.js -> output.js
(function () {
  // Intentionally empty.
})();
