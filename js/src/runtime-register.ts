/******************************************************************************
 * AMD registration for the shinywidgets runtime.
 *
 * This is a plain script (not an AMD module): it runs after libembed-amd.js
 * has assigned `window.shinywidgetsRuntime` and before output.js starts
 * requiring widget modules. It defines the official module IDs as static
 * named aliases of the one coherent runtime, so third-party widget modules
 * and our own output bundle share the exact same base/controls/html
 * constructors (no duplicate Backbone/base/Lumino bundle).
 ******************************************************************************/

export interface RuntimeNamespaces {
  readonly base: unknown;
  readonly controls: unknown;
  readonly html: unknown;
  readonly internals: unknown;
}

declare function define(
  name: string,
  dependencies: readonly string[],
  factory: (runtime: RuntimeNamespaces) => unknown
): void;

const runtime = (window as unknown as { shinywidgetsRuntime: RuntimeNamespaces })
  .shinywidgetsRuntime;

define("shinywidgets-runtime", [], () => runtime);
define("@jupyter-widgets/base", ["shinywidgets-runtime"], (r) => r.base);
define("@jupyter-widgets/controls", ["shinywidgets-runtime"], (r) => r.controls);
define("@jupyter-widgets/html-manager", ["shinywidgets-runtime"], (r) => r.html);
define("shinywidgets-internals", ["shinywidgets-runtime"], (r) => r.internals);

export {};
