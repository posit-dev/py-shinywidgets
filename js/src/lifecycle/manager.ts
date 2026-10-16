/******************************************************************************
 * Epoch-bound widget manager.
 *
 * One EpochManager per transport epoch. It owns its canonical model registry
 * (never the upstream private `_models`), and every model it creates retains
 * this exact manager instance. Once retired, admission is permanently closed:
 * lookups, registrations, class loading, and construction all reject with
 * EpochRetiredError, so an old connection's work can never corrupt a fresh
 * epoch's models -- even for equal full model IDs or equal local ID suffixes.
 ******************************************************************************/

import * as base from "@jupyter-widgets/base";
import * as controls from "@jupyter-widgets/controls";
import type { IClassicComm, WidgetModel, WidgetView } from "@jupyter-widgets/base";
import { createErrorWidgetModel, createErrorWidgetView } from "@jupyter-widgets/base";
import { ManagerBase, serialize_state, HtmlOutputModel } from "shinywidgets-internals";
import type {
  IManagerState,
  IStateOptions,
} from "@jupyter-widgets/base-manager";
import { ManagedOutputView } from "./mime";
import type { MountScope } from "./mount";
import { protocolError } from "./protocol";
import type { EpochIdentity, LifecycleSnapshot, ModelId } from "./types";
import { EpochRetiredError } from "./types";

export type ModuleLoader = (
  moduleName: string,
  moduleVersion: string
) => Promise<any>;

interface ModelRecord {
  promise: Promise<WidgetModel>;
  model?: WidgetModel;
  closing: boolean;
}

interface ModelWaiter {
  resolve: (promise: Promise<WidgetModel>) => void;
  reject: (error: Error) => void;
  timer: ReturnType<typeof setTimeout>;
}

export interface EpochManagerOptions {
  readonly identity: EpochIdentity;
  readonly loader: ModuleLoader;
  // Look up an already-owned comm (e.g., the controller's comm table) for the
  // set_state() restoration path.
  readonly getComm?: (modelId: ModelId) => IClassicComm | undefined;
}

export class EpochManager extends ManagerBase {
  readonly identity: EpochIdentity;
  private readonly _loader: ModuleLoader;
  private readonly _getComm: ((modelId: ModelId) => IClassicComm | undefined) | undefined;
  private readonly _records = new Map<ModelId, ModelRecord>();
  private readonly _waiters = new Map<ModelId, ModelWaiter[]>();
  private _retired = false;
  private _retireTask: Promise<void> | null = null;

  constructor(options: EpochManagerOptions) {
    super();
    this.identity = options.identity;
    this._loader = options.loader;
    this._getComm = options.getComm;
  }

  get retired(): boolean {
    return this._retired;
  }

  snapshot(): LifecycleSnapshot {
    let waiters = 0;
    for (const entry of this._waiters.values()) {
      waiters += entry.length;
    }
    return {
      models: this._records.size,
      waiters,
      mounts: 0,
      views: 0,
      tasks: this._retireTask !== null && !this._retired ? 1 : 0,
    };
  }

  /**************************************************************************
   * Canonical registry (owned; never touches upstream `_models`)
   **************************************************************************/

  async get_model(model_id: string): Promise<WidgetModel> {
    this._checkAdmission("get_model");
    const id = this.normalizeModelId(model_id);
    const record = this._records.get(id);
    if (record !== undefined) {
      return record.promise;
    }
    // A missing-model waiter owned by this epoch: Shiny delivers comm_open
    // messages one at a time, so a parent's deserialization may reference a
    // child whose comm_open hasn't been processed yet.
    return new Promise<WidgetModel>((resolve, reject) => {
      // Use a generous timeout: heavy sessions (1000s of comm_opens) or slow
      // networks can legitimately delay a child's comm_open well past 10s.
      const waiter: ModelWaiter = {
        resolve: (promise) => resolve(promise),
        reject,
        timer: setTimeout(() => {
          this._dropWaiter(id, waiter);
          reject(new Error(`Timeout waiting for widget model ${id}`));
        }, 30000),
      };
      const waiters = this._waiters.get(id) ?? [];
      waiters.push(waiter);
      this._waiters.set(id, waiters);
    });
  }

  has_model(model_id: string): boolean {
    try {
      return this._records.has(this.normalizeModelId(model_id));
    } catch {
      return false;
    }
  }

  register_model(model_id: string, modelPromise: Promise<WidgetModel>): void {
    this._checkAdmission("register_model");
    const id = this.normalizeModelId(model_id);
    if (this._records.has(id)) {
      throw new Error(`Model ${model_id} is already registered in this epoch`);
    }
    const record: ModelRecord = { promise: modelPromise, closing: false };
    this._records.set(id, record);
    modelPromise.then(
      (model) => {
        record.model = model;
        model.once("comm:close", () => {
          // An old close listener deletes the record only if the stored
          // record/promise identity still matches -- a stale close can't
          // remove a fresh same-ID registration.
          if (this._records.get(id) === record) {
            this._records.delete(id);
          }
        });
      },
      () => {
        // Construction rejection (e.g., retirement) is reported by the
        // admitted task's terminal handler; nothing to do here.
      }
    );
    const waiters = this._waiters.get(id);
    if (waiters !== undefined) {
      this._waiters.delete(id);
      for (const waiter of waiters) {
        clearTimeout(waiter.timer);
        waiter.resolve(modelPromise);
      }
    }
  }

  async get_state(options?: IStateOptions): Promise<IManagerState> {
    this._checkAdmission("get_state");
    const records = [...this._records.values()].filter((r) => !r.closing);
    const models = await Promise.all(records.map((r) => r.promise));
    // Retirement during export rejects the export; stale state must not leak
    // out as a current-epoch result.
    this._checkAdmission("get_state");
    return serialize_state(models, options);
  }

  /**************************************************************************
   * Guarded model construction
   **************************************************************************/

  async new_model(
    options: Parameters<ManagerBase["new_model"]>[0],
    serialized_state?: any
  ): Promise<WidgetModel> {
    this._checkAdmission("new_model");
    const model_id = options.model_id ?? (options.comm as any)?.comm_id;
    if (!model_id) {
      throw new Error(
        "Neither comm nor model_id provided in options object. At least one must exist."
      );
    }
    const qualified = this.normalizeModelId(model_id);
    const optionsClone = { ...options, model_id: qualified };
    const modelPromise = this._make_model(optionsClone, serialized_state);
    // Registration happens synchronously, before the first await can run.
    this.register_model(qualified, modelPromise);
    return await modelPromise;
  }

  async new_widget(
    options: Parameters<ManagerBase["new_widget"]>[0],
    serialized_state?: any
  ): Promise<WidgetModel> {
    this._checkAdmission("new_widget");
    if (!options.comm) {
      // Measured boundary: the installed HTMLManager answers this with a
      // dummy comm that never reaches a backend (see the lifecycle_epochs
      // ControllerModel probe). Keep it an explicit failure.
      throw new Error(
        "Frontend-initiated widget creation (new_widget without a comm) is " +
          "not supported by shinywidgets; construct widgets on the server."
      );
    }
    return super.new_widget(options, serialized_state);
  }

  async _make_model(
    options: { model_id: string } & Record<string, any>,
    serialized_state: any = {}
  ): Promise<WidgetModel> {
    const model_id = options.model_id;
    this._checkAdmission("new_model");
    let ModelType: typeof WidgetModel;
    try {
      ModelType = await this.loadModelClass(
        options.model_name,
        options.model_module,
        options.model_module_version
      );
    } catch (error) {
      if (error instanceof EpochRetiredError) {
        throw error;
      }
      console.error("Could not instantiate widget");
      return this._makeErrorModel(options, error);
    }
    this._checkAdmission("new_model");
    let widget_model: WidgetModel;
    try {
      const attributes = await ModelType._deserialize_state(
        serialized_state,
        this as any
      );
      this._checkAdmission("new_model");
      widget_model = new ModelType(attributes, {
        widget_manager: this as any,
        model_id: model_id,
        comm: options.comm,
      });
    } catch (error) {
      if (error instanceof EpochRetiredError) {
        throw error;
      }
      console.error(error);
      return this._makeErrorModel(options, error);
    }
    this._checkAdmission("new_model");
    widget_model.name = options.model_name;
    widget_model.module = options.model_module;
    return widget_model;
  }

  private _makeErrorModel(
    options: { model_id: string } & Record<string, any>,
    error: unknown
  ): WidgetModel {
    // Genuine active failures keep the upstream ErrorWidget behavior, with
    // the registered ID/owner/comm supplied to the fallback model.
    const Cls = createErrorWidgetModel(error, "Could not instantiate widget");
    const model = new Cls({}, {
      widget_manager: this as any,
      model_id: options.model_id,
      comm: options.comm,
    } as any);
    model.name = options.model_name;
    model.module = options.model_module;
    return model;
  }

  /**************************************************************************
   * View creation (owned seam, upstream contract)
   **************************************************************************/

  create_view<VT extends base.DOMWidgetView = base.DOMWidgetView>(
    model: base.DOMWidgetModel,
    options?: any
  ): Promise<VT>;
  create_view<VT extends base.WidgetView = base.WidgetView>(
    model: WidgetModel,
    options?: any
  ): Promise<VT>;
  create_view(model: WidgetModel, options: any = {}): Promise<base.WidgetView> {
    // Resolve explicit scope first, then the actual parent view's scope. The
    // parent view object is available synchronously when child rendering
    // begins, even if the parent's render hasn't settled.
    const scope =
      (options.lifecycle_scope as MountScope | undefined) ??
      ((options.parent as base.WidgetView | undefined)?.options as any)
        ?.lifecycle_scope;
    if (scope === undefined) {
      return Promise.reject(
        new Error("create_view requires an explicit lifecycle_scope")
      );
    }
    return this._createScopedView(model, scope, options);
  }

  private _createScopedView(
    model: WidgetModel,
    scope: MountScope,
    options: any = {}
  ): Promise<base.WidgetView> {
    scope.checkAdmission("create_view");
    const id = `view-${Date.now().toString(36)}-${Math.random()
      .toString(36)
      .slice(2, 10)}`;
    let viewPromise: Promise<base.WidgetView>;
    const untrack = (view: base.WidgetView) => {
      scope.untrackView(view);
      const views = model.views as Record<string, Promise<base.WidgetView>> | undefined;
      if (views !== undefined && views[id] === viewPromise) {
        delete views[id];
      }
    };
    viewPromise = (model.state_change = model.state_change.then(
      async (): Promise<base.WidgetView> => {
        scope.checkAdmission("create_view");
        const _view_name = model.get("_view_name");
        const _view_module = model.get("_view_module");
        try {
          const ViewType = await this.loadViewClass(
            _view_name,
            _view_module,
            model.get("_view_module_version")
          );
          scope.checkAdmission("create_view");
          const view = new ViewType({
            model: model,
            options: this.setViewOptions({ ...options, lifecycle_scope: scope }),
          });
          view.listenTo(model, "destroy", view.remove);
          scope.trackView(view);
          // Install the removal bookkeeping before awaiting render.
          view.once("remove", () => untrack(view));
          await view.render();
          // A view that completed late (after its mount retired) is removed,
          // never attached.
          if (!scope.accepting) {
            view.remove();
            throw new EpochRetiredError(
              "widget view completed after its mount retired"
            );
          }
          return view;
        } catch (error) {
          if (error instanceof EpochRetiredError) {
            throw error;
          }
          console.error(
            `Could not create a view for model id ${model.model_id}`
          );
          const msg = `Failed to create view for '${_view_name}' from module '${_view_module}' with model '${model.name}' from module '${model.module}'`;
          const ModelCls = createErrorWidgetModel(error, msg);
          const errorModel = new ModelCls();
          const view = new base.ErrorWidgetView({
            model: errorModel,
            options: this.setViewOptions({ ...options, lifecycle_scope: scope }),
          });
          scope.trackView(view);
          view.once("remove", () => untrack(view));
          await view.render();
          return view;
        }
      }
    ));
    if (model.views !== undefined) {
      (model.views as Record<string, Promise<base.WidgetView>>)[id] = viewPromise;
    }
    return viewPromise;
  }

  /**************************************************************************
   * Class loading
   **************************************************************************/

  protected async loadClass(
    className: string,
    moduleName: string,
    moduleVersion: string
  ): Promise<typeof WidgetModel | typeof WidgetView> {
    this._checkAdmission("loadClass");
    if (moduleName === "@jupyter-widgets/controls") {
      // The lab-variables guard from the upstream loadClass: apply only when
      // the host page doesn't already define JupyterLab theme variables.
      if (
        getComputedStyle(document.documentElement).getPropertyValue(
          "--jp-layout-color0"
        ) === ""
      ) {
        // Bundled from node_modules (the AMD external only covers the bare
        // package ID); injected by style-loader at require time.
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        require("@jupyter-widgets/controls/css/labvariables.css");
      }
      return classOf(controls, className, moduleName, moduleVersion);
    }
    if (moduleName === "@jupyter-widgets/base") {
      return classOf(base, className, moduleName, moduleVersion);
    }
    if (moduleName === "@jupyter-widgets/output") {
      return classOf(
        { OutputModel: HtmlOutputModel, OutputView: ManagedOutputView },
        className,
        moduleName,
        moduleVersion
      );
    }
    const module = await this._loader(moduleName, moduleVersion);
    return classOf(module, className, moduleName, moduleVersion);
  }

  protected async loadModelClass(
    className: string,
    moduleName: string,
    moduleVersion: string
  ): Promise<typeof WidgetModel> {
    try {
      return (await this.loadClass(
        className,
        moduleName,
        moduleVersion
      )) as typeof WidgetModel;
    } catch (error) {
      if (error instanceof EpochRetiredError) {
        throw error;
      }
      console.error(error);
      return createErrorWidgetModel(
        error,
        `Failed to load model class '${className}' from module '${moduleName}'`
      );
    }
  }

  protected async loadViewClass(
    className: string,
    moduleName: string,
    moduleVersion: string
  ): Promise<typeof WidgetView> {
    try {
      return (await this.loadClass(
        className,
        moduleName,
        moduleVersion
      )) as typeof WidgetView;
    } catch (error) {
      if (error instanceof EpochRetiredError) {
        throw error;
      }
      console.error(error);
      return createErrorWidgetView(
        error,
        `Failed to load view class '${className}' from module '${moduleName}'`
      );
    }
  }

  /**************************************************************************
   * Comm boundary
   **************************************************************************/

  protected async _create_comm(
    comm_target_name: string,
    model_id?: string,
    data?: any,
    metadata?: any,
    _buffers?: ArrayBuffer[] | ArrayBufferView[]
  ): Promise<IClassicComm> {
    this._checkAdmission("_create_comm");
    if (data === undefined && metadata === undefined) {
      // Reconstruct an already-owned comm (the inherited set_state()
      // restoration path); never mint a new backend comm.
      if (model_id !== undefined) {
        const comm = this._getComm?.(this.normalizeModelId(model_id));
        if (comm !== undefined) {
          return comm;
        }
      }
      throw new Error(
        `Cannot reconstruct a comm for unknown model '${model_id}' in this epoch`
      );
    }
    throw new Error(
      "Creating a new backend comm from the browser is not supported by " +
        "shinywidgets; construct widgets on the server."
    );
  }

  protected async _get_comm_info(): Promise<{}> {
    const info: Record<string, {}> = {};
    for (const [id, record] of this._records) {
      if (record.model?.comm_live) {
        info[id] = {};
      }
    }
    return info;
  }

  /**************************************************************************
   * Retirement
   **************************************************************************/

  /**
   * Permanently retire this epoch. Admission closes synchronously; the
   * returned close task is cached so repeated retirement joins the same work.
   */
  retire(): Promise<void> {
    if (this._retireTask !== null) {
      return this._retireTask;
    }
    this._retired = true;
    this._retireTask = this._doRetire();
    return this._retireTask;
  }

  clear_state(): Promise<void> {
    return this.retire();
  }

  disconnect(): void {
    // Synchronous retirement; the cached cleanup task is tracked separately
    // (never awaited from a jQuery callback).
    for (const record of this._records.values()) {
      if (record.model !== undefined) {
        record.model.comm_live = false;
      }
    }
    void this.retire();
  }

  private async _doRetire(): Promise<void> {
    for (const [id, waiters] of this._waiters) {
      for (const waiter of waiters) {
        clearTimeout(waiter.timer);
        waiter.reject(
          new EpochRetiredError(
            `Widget transport epoch retired while waiting for model ${id}`
          )
        );
      }
    }
    this._waiters.clear();

    const errors: unknown[] = [];
    await Promise.all(
      [...this._records.entries()].map(async ([id, record]) => {
        record.closing = true;
        try {
          const model = await record.promise;
          model.comm_live = false;
          await model.close(true);
        } catch (error) {
          if (error instanceof EpochRetiredError) {
            // Expected cancellation of pending construction.
            return;
          }
          errors.push(error);
        } finally {
          if (this._records.get(id) === record) {
            this._records.delete(id);
          }
        }
      })
    );
    if (errors.length > 0) {
      throw new Error(
        `Errors while retiring widget epoch: ${errors
          .map((e) => String(e))
          .join("; ")}`
      );
    }
  }

  /**************************************************************************
   * Helpers
   **************************************************************************/

  /**
   * Normalize a (possibly local) model ID into this manager's bound session
   * namespace. Wire packets must already carry qualified IDs.
   */
  normalizeModelId(modelId: string): ModelId {
    const prefix = `sw-${this.identity.model_namespace}-`;
    if (modelId.startsWith("sw-")) {
      if (!modelId.startsWith(prefix)) {
        throw protocolError(
          `model ID '${modelId}' belongs to a foreign session namespace`
        );
      }
      return modelId as ModelId;
    }
    return `${prefix}${modelId}` as ModelId;
  }

  private _checkAdmission(operation: string): void {
    if (this._retired) {
      throw new EpochRetiredError(
        `Widget transport epoch is retired; ${operation} is no longer allowed`
      );
    }
  }

  private _dropWaiter(model_id: ModelId, waiter: ModelWaiter): void {
    const waiters = this._waiters.get(model_id);
    if (!waiters) {
      return;
    }
    const remaining = waiters.filter((w) => w !== waiter);
    if (remaining.length > 0) {
      this._waiters.set(model_id, remaining);
    } else {
      this._waiters.delete(model_id);
    }
  }
}

function classOf(
  module: Record<string, any>,
  className: string,
  moduleName: string,
  moduleVersion: string
): any {
  const cls = module[className];
  if (cls === undefined) {
    throw new Error(
      `Class ${className} not found in module ${moduleName}@${moduleVersion}`
    );
  }
  return cls;
}
