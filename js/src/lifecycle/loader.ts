import { requireLoader } from "@jupyter-widgets/html-manager";

/******************************************************************************
 * Third-party widget module loading for Shiny.
 *
 * shiny provides a shim of require.js which allows <script>s with anonymous
 * define()s to be loaded without error. When an anonymous define() occurs,
 * the shim uses the data-requiremodule attribute (set by require.js) on the
 * script to determine the module name.
 * https://github.com/posit-dev/py-shiny/blob/230940c/scripts/define-shims.js#L10-L16
 *
 * In the context of shinywidgets, when a widget gets rendered, it comes with
 * another <script> tag that does `require.config({paths: {...}})` mapping the
 * module name to a URL of the widget's JS file.
 *
 * Concurrency: module loads overlap (e.g., two widgets of different packages
 * initializing at once, or a new epoch loading while an old load is still
 * unresolved). The shared `define.amd` flag is reference-counted so an older
 * load finishing late can't clobber the flag while another load is active,
 * and loads are never serialized behind a hung request.
 ******************************************************************************/

let activeLoads = 0;
let savedAmd: unknown;

export const shinyRequireLoader = async function (
  moduleName: string,
  moduleVersion: string
): Promise<any> {
  const define = (window as any).define;

  if (activeLoads === 0) {
    savedAmd = define.amd;
  }
  activeLoads++;

  // This is probably not necessary, but just in case -- especially now in an
  // anywidget/ES6 world, we probably don't want to load AMD modules
  // (plotly is one example of a widget that will fail to load if AMD is enabled)
  define.amd = false;

  // Store jQuery global since loading a module may overwrite it
  // (qgrid is one good example)
  const old$ = (window as any).$;
  const oldJQ = (window as any).jQuery;

  if (moduleName === "qgrid") {
    // qgrid wants to use base/js/dialog (if it's available) for full-screen tables
    // https://github.com/quantopian/qgrid/blob/877b420/js/src/qgrid.widget.js#L11-L16
    // Maybe that's worth supporting someday, but for now, we define it to be nothing
    // to avoid require('qgrid') from producing an error
    define("base/js/dialog", [], function () {
      return null;
    });
  }

  try {
    return await requireLoader(moduleName, moduleVersion);
  } finally {
    activeLoads--;
    if (activeLoads === 0) {
      define.amd = savedAmd;
    }
    (window as any).$ = old$;
    (window as any).jQuery = oldJQ;
  }
};
