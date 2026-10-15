// The @jupyter-widgets/* AMD modules are pre-registered inside
// libembed-amd.js (loaded after this script), so require() finds them
// without a network fetch. Those bundles derive their webpack publicPath
// (used for font URLs in their CSS, e.g. FontAwesome woff2/ttf files) from
// the AMD module's `uri`, which require.js computes from the module ID
// (e.g. "/@jupyter-widgets/controls.js") rather than the actual script
// URL -- so font requests would 404 ("/@jupyter-widgets/<hash>.woff2").
// require.js computes module URLs when the named define()s are intaken,
// which happens at the first require() call after libembed-amd.js loads,
// so this mapping must be installed before that (i.e., this script must
// come before libembed-amd.js in output_binding_dependency()).
(function () {
  var script = document.currentScript;
  if (!script || !window.require) {
    return;
  }
  var dir = script.src.slice(0, script.src.lastIndexOf("/"));
  var paths = {};
  [
    "@jupyter-widgets/base",
    "@jupyter-widgets/controls",
    "@jupyter-widgets/base7",
    "@jupyter-widgets/controls7",
    "@jupyter-widgets/html-manager",
  ].forEach(function (id) {
    // The actual file is never fetched (the modules are already defined);
    // this URL only seeds the publicPath derivation (its directory matters,
    // and require.js appends ".js" back on).
    paths[id] = dir + "/libembed-amd";
  });
  window.require.config({ paths: paths });
})();
