/******************************************************************************
 * Owned Output widget MIME presentations.
 *
 * The official HTML OutputModel (public `outputs` model) is rendered by
 * ManagedOutputView, which owns its OutputArea and per-view RenderMimeRegistry
 * (never a manager-global renderMime swapped during rendering). Nested widget
 * MIME renderings get an explicit child MountScope, so mount retirement
 * reaches nested views even though MIME rendering bypasses parent options and
 * the normal display entry point.
 ******************************************************************************/

import { JupyterLuminoPanelWidget } from "@jupyter-widgets/base";
import type { WidgetModel } from "@jupyter-widgets/base";
import type { IRenderMime } from "@jupyterlab/rendermime-interfaces";
import {
  HtmlOutputModel,
  LuminoWidget,
  OutputArea,
  OutputBaseView,
  RenderMimeRegistry,
  standardRendererFactories,
} from "shinywidgets-internals";
import type { MountScope } from "./mount";
import { protocolError } from "./protocol";
import type { ModelId } from "./types";

export const WIDGET_MIMETYPE = "application/vnd.jupyter.widget-view+json";

interface WidgetMimePayload {
  model_id: ModelId;
  version_major: number;
  version_minor: number;
}

function parseWidgetMimePayload(data: unknown): WidgetMimePayload {
  if (typeof data !== "object" || data === null || Array.isArray(data)) {
    throw protocolError("widget-view MIME payload is not an object");
  }
  const payload = data as Record<string, unknown>;
  const model_id = payload["model_id"];
  if (typeof model_id !== "string" || model_id.length === 0) {
    throw protocolError("widget-view MIME payload has no model_id");
  }
  return {
    model_id: model_id as ModelId,
    version_major: Number(payload["version_major"] ?? 0),
    version_minor: Number(payload["version_minor"] ?? 0),
  };
}

/**
 * A widget-view MIME renderer. Each renderer owns a child MountScope;
 * re-rendering retires the old child scope before accepting the next, and
 * disposal invalidates child admission synchronously while the parent scope
 * joins the observable cleanup.
 */
export class ManagedWidgetRenderer
  extends LuminoWidget
  implements IRenderMime.IRenderer
{
  readonly mimeType: string;
  private readonly _scope: MountScope;
  private _childScope: MountScope | null = null;

  constructor(options: IRenderMime.IRendererOptions, scope: MountScope) {
    super();
    this.mimeType = options.mimeType;
    this._scope = scope;
  }

  async renderModel(model: IRenderMime.IMimeModel): Promise<void> {
    const payload = parseWidgetMimePayload(model.data[this.mimeType]);
    // Re-render retires the old child scope before accepting the next.
    const previous = this._childScope;
    this._childScope = null;
    if (previous !== null) {
      await previous.dispose();
    }
    this._scope.checkAdmission("renderModel");
    const child = this._scope.childScope();
    this._childScope = child;
    const manager = this._scope.epoch;
    const task = (async (): Promise<void> => {
      let model: WidgetModel;
      try {
        model = await manager.get_model(payload.model_id);
      } catch (error) {
        console.error("Error displaying widget in Output:", error);
        this.node.textContent = "Error creating widget: could not find model";
        return;
      }
      child.checkAdmission("attach");
      const view = await manager.create_view(model as any, {
        lifecycle_scope: child,
      });
      child.checkAdmission("attach");
      const lumino = (view as any).luminoWidget ?? (view as any).pWidget;
      LuminoWidget.attach(lumino, this.node);
    })();
    // The parent scope joins this task so root disposal covers nested
    // model-loading work; renderer replacement does not create a separate
    // server display lease.
    this._scope.trackTask(task);
    await task;
  }

  dispose(): void {
    if (this.isDisposed) {
      return;
    }
    const child = this._childScope;
    this._childScope = null;
    if (child !== null) {
      // Invalidate child admission synchronously; the parent scope tracks
      // the cached asynchronous disposal.
      this._scope.trackTask(child.dispose());
    }
    super.dispose();
  }
}

/**
 * An Output widget view that owns its OutputArea and a per-view
 * RenderMimeRegistry whose widget factory captures this view's scope.
 */
export class ManagedOutputView extends OutputBaseView {
  private _outputArea: InstanceType<typeof OutputArea> | null = null;
  private _scope: MountScope | null = null;

  _createElement(_tagName: string): HTMLElement {
    (this as any).luminoWidget = new JupyterLuminoPanelWidget({ view: this });
    return (this as any).luminoWidget.node;
  }

  _setElement(el: HTMLElement): void {
    if ((this as any).el || el !== (this as any).luminoWidget.node) {
      throw new Error("Cannot reset the DOM element.");
    }
    (this as any).el = (this as any).luminoWidget.node;
    (this as any).$el = $((this as any).luminoWidget.node);
  }

  render(): void {
    const scope = (this.options as any).lifecycle_scope as MountScope | undefined;
    if (scope === undefined) {
      throw new Error("ManagedOutputView requires an explicit lifecycle_scope");
    }
    this._scope = scope.childScope();
    const rendermime = new RenderMimeRegistry({
      initialFactories: standardRendererFactories,
    });
    const viewScope = this._scope;
    rendermime.addFactory({
      safe: true,
      mimeTypes: [WIDGET_MIMETYPE],
      createRenderer: (options) => new ManagedWidgetRenderer(options, viewScope),
    });
    const model = this.model as HtmlOutputModel;
    this._outputArea = new OutputArea({
      rendermime,
      model: model.outputs,
    });
    const panel = (this as any).luminoWidget as JupyterLuminoPanelWidget;
    panel.insertWidget(0, this._outputArea);
    panel.addClass("jupyter-widgets");
    panel.addClass("widget-output");
  }

  remove(): void {
    const scope = this._scope;
    this._scope = null;
    if (scope !== null) {
      // Invalidate nested admission synchronously; the mount joins the
      // observable cleanup through the scope tree.
      void scope.dispose();
    }
    if (this._outputArea !== null && !this._outputArea.isDisposed) {
      this._outputArea.dispose();
    }
    this._outputArea = null;
    super.remove();
  }
}
