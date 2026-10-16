/******************************************************************************
 * Types for the "shinywidgets-internals" AMD module.
 *
 * The runtime build (js/src/runtime.ts) bundles the official implementations;
 * this declaration lets owned code import them with their official types while
 * webpack treats the module as an AMD external of the output build.
 ******************************************************************************/

declare module "shinywidgets-internals" {
  import { ManagerBase, serialize_state } from "@jupyter-widgets/base-manager";
  import { MessageLoop } from "@lumino/messaging";
  import { Widget as LuminoWidget } from "@lumino/widgets";
  import {
    RenderMimeRegistry,
    standardRendererFactories,
  } from "@jupyterlab/rendermime";
  import { OutputArea, OutputAreaModel } from "@jupyterlab/outputarea";
  import { OutputView as OutputBaseView } from "@jupyter-widgets/output";
  import { OutputModel as HtmlOutputModel } from "@jupyter-widgets/html-manager/lib/output";

  export {
    ManagerBase,
    serialize_state,
    MessageLoop,
    LuminoWidget,
    RenderMimeRegistry,
    standardRendererFactories,
    OutputArea,
    OutputAreaModel,
    OutputBaseView,
    HtmlOutputModel,
  };
}
