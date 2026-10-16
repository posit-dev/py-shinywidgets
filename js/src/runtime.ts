/******************************************************************************
 * The shinywidgets widget runtime.
 *
 * One coherent compilation of the official Jupyter widget packages (and their
 * single Backbone/Lumino base) that the output binding and third-party widget
 * modules share. This replaces the downloaded @jupyter-widgets/html-manager
 * libembed-amd.js bundle: the same official packages, built from source with
 * the packages our lifecycle code imports directly.
 *
 * The build exposes these exports as `window.shinywidgetsRuntime` (see
 * js/webpack.config.js); runtime-register.js then aliases the official AMD
 * module IDs (@jupyter-widgets/base, etc.) onto these namespaces so
 * require()-based third-party widgets resolve the exact same constructors.
 ******************************************************************************/

import "@jupyter-widgets/controls/css/widgets-base.css";
import "@lumino/widgets/style/index.css";
import "@fortawesome/fontawesome-free/css/all.min.css";
import "@fortawesome/fontawesome-free/css/v4-shims.min.css";
import * as base from "@jupyter-widgets/base";
import * as controls from "@jupyter-widgets/controls";
import * as html from "@jupyter-widgets/html-manager";
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

export { base, controls, html };
export const internals = {
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
