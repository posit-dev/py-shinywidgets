import { HTMLManager, requireLoader } from '@jupyter-widgets/html-manager';
import { setConnected, ShinyComm } from './comm';
import { ipyleafletBehavior, WIDGET_BEHAVIORS, type PostDisplayContext } from './fill';
import { isJQuery, jsonParse, lendDataTables, protectPageJQuery } from './utils';
import { disposeNative, finishDetach, hasAncestor, patchMplCanvasRemove, patchSigmaView, viewParent } from './views';
import { uuid } from '@jupyter-widgets/base';
import type { DOMWidgetModel, DOMWidgetView, WidgetModel, WidgetView } from '@jupyter-widgets/base';
import type { HtmlDep } from 'rstudio-shiny/srcts/types/src/shiny/render';
import type { ErrorsMessageValue } from 'rstudio-shiny/srcts/types/src/shiny/shinyapp';


/******************************************************************************
 * Define a custom HTMLManager for use with Shiny
 ******************************************************************************/

interface ModelWaiter {
  resolve: (p: Promise<WidgetModel>) => void;
  reject: (e: Error) => void;
  timer: ReturnType<typeof setTimeout>;
}

class OutputManager extends HTMLManager {
  // Shiny delivers comm_open messages one at a time with microtask breaks
  // between them. A parent model's deserialization may reference a child model
  // whose comm_open hasn't been processed yet. The base get_model rejects
  // missing models, so we override it to wait for late
  // arrivals (with a timeout to avoid silent hangs).
  private _modelWaiters = new Map<string, ModelWaiter[]>();
  private _activeClears = 0;

  // Every view the manager has created, including child views created via
  // `create_child_view` (views of a *different* model, not tracked anywhere
  // else). Lets `removeViewTree` remove a view's descendants, not just itself.
  private _liveViews = new Set<WidgetView>();

  // Views removed by removeViewTree(), so a view whose create_view() promise
  // resolves after its ancestor was removed can tear itself down. Weak so
  // removed views can still be garbage collected.
  private _removedViews = new WeakSet<WidgetView>();

  // new_widget() calls this for a model the widget's own JS creates (bqplot's
  // toolbar PanZoom, pythreejs light targets); HTMLManager's placeholder comm
  // would leave it without a Python counterpart.
  _create_comm(
    comm_target_name: string,
    model_id?: string,
    data?: any,
    metadata?: any,
    buffers?: ArrayBuffer[] | ArrayBufferView[]
  ): Promise<ShinyComm> {
    const comm = new ShinyComm(model_id ?? uuid());
    comm.open(data, undefined, metadata, buffers);
    return Promise.resolve(comm);
  }

  create_view<VT extends DOMWidgetView = DOMWidgetView>(model: DOMWidgetModel, options?: any): Promise<VT>;
  create_view<VT extends WidgetView = WidgetView>(model: WidgetModel, options?: any): Promise<VT>;
  create_view(model: WidgetModel, options?: any): Promise<WidgetView> {
    const viewPromise = super.create_view(model, options);
    viewPromise.then(
      (view) => {
        patchMplCanvasRemove(view);
        // An ancestor may have been removed while this view was still being
        // created (e.g. dynamic UI removed the output mid-render).
        // removeViewTree() only sweeps views live at the time, so tear the
        // late view down here.
        if (this._hasRemovedAncestor(view)) {
          try {
            this._teardownView(view);
          } catch (err) {
            console.error('Error removing orphaned widget view:', err);
          }
          return;
        }
        this._liveViews.add(view);
        view.once('remove', () => this._liveViews.delete(view));
      },
      () => {
        // View creation failed; create_view's own promise chain already logs it.
      }
    );
    return viewPromise;
  }

  // Remove `root` and every live view whose `options.parent` chain leads back
  // to it (e.g. ipyleaflet's layer/control views, or a container's children);
  // plain `view.remove()` would leave those descendants alive and listening.
  removeViewTree(root: WidgetView): void {
    const errors: unknown[] = [];
    const teardown = (view: WidgetView) => {
      try {
        this._teardownView(view);
      } catch (err) {
        errors.push(err);
      }
    };
    for (const view of [...this._liveViews].reverse()) {
      if (view !== root && hasAncestor(view, root)) {
        teardown(view);
      }
    }
    teardown(root);
    if (errors.length) {
      console.error('Errors while removing widget view tree:', errors);
    }
  }

  private _teardownView(view: WidgetView): void {
    // Mark before remove() so any descendants that resolve later (from this
    // view's own pending create_child_view calls) also tear themselves down.
    this._removedViews.add(view);
    disposeNative(view);
    finishDetach(view);
    view.remove();
  }

  private _hasRemovedAncestor(view: WidgetView): boolean {
    for (let parent = viewParent(view); parent; parent = viewParent(parent)) {
      if (this._removedViews.has(parent)) {
        return true;
      }
    }
    return false;
  }

  async get_model(model_id: string): Promise<WidgetModel> {
    if (this.has_model(model_id)) {
      return super.get_model(model_id);
    }
    if (this._activeClears > 0) {
      throw new Error(`Widget state cleared while waiting for model ${model_id}`);
    }
    return new Promise<WidgetModel>((resolve, reject) => {
      // Use a generous timeout: heavy sessions (1000s of comm_opens) or slow
      // networks can legitimately delay a child's comm_open well past 10s.
      const waiter: ModelWaiter = {
        resolve,
        reject,
        timer: setTimeout(() => {
          this._dropWaiter(model_id, waiter);
          reject(new Error(`Timeout waiting for widget model ${model_id}`));
        }, 30000),
      };
      const waiters = this._modelWaiters.get(model_id) || [];
      waiters.push(waiter);
      this._modelWaiters.set(model_id, waiters);
    });
  }

  register_model(model_id: string, modelPromise: Promise<WidgetModel>): void {
    super.register_model(model_id, modelPromise);
    const waiters = this._modelWaiters.get(model_id);
    if (waiters) {
      this._modelWaiters.delete(model_id);
      for (const waiter of waiters) {
        clearTimeout(waiter.timer);
        waiter.resolve(modelPromise);
      }
    }
  }

  async clear_state(): Promise<void> {
    // Model deserialization can reach get_model() after the waiter sweep.
    this._activeClears++;
    try {
      for (const [model_id, waiters] of this._modelWaiters) {
        for (const waiter of waiters) {
          clearTimeout(waiter.timer);
          waiter.reject(
            new Error(`Widget state cleared while waiting for model ${model_id}`)
          );
        }
      }
      this._modelWaiters.clear();
      await super.clear_state();
    } finally {
      this._activeClears--;
    }
  }

  private _dropWaiter(model_id: string, waiter: ModelWaiter): void {
    const waiters = this._modelWaiters.get(model_id);
    if (!waiters) {
      return;
    }
    const remaining = waiters.filter((w) => w !== waiter);
    if (remaining.length > 0) {
      this._modelWaiters.set(model_id, remaining);
    } else {
      this._modelWaiters.delete(model_id);
    }
  }
}

// Define our own custom module loader for Shiny
const shinyRequireLoader = async function(moduleName: string, moduleVersion: string): Promise<any> {

  // shiny provides a shim of require.js which allows <script>s with anonymous
  // define()s to be loaded without error. When an anonymous define() occurs,
  // the shim uses the data-requiremodule attribute (set by require.js) on the script
  // to determine the module name.
  // https://github.com/posit-dev/py-shiny/blob/230940c/scripts/define-shims.js#L10-L16
  // In the context of shinywidgets, when a widget gets rendered, it should
  // come with another <script> tag that does `require.config({paths: {...}})`
  // which maps the module name to a URL of the widget's JS file.
  const oldAmd = (window as any).define.amd;

  // This is probably not necessary, but just in case -- especially now in a
  // anywidget/ES6 world, we probably don't want to load AMD modules
  // (plotly is one example of a widget that will fail to load if AMD is enabled)
  (window as any).define.amd = false;

  // Store jQuery global since loading we load a module, it may overwrite it
  // (qgrid is one good example)
  const old$ = (window as any).$;
  const oldJQ = (window as any).jQuery;

  if (moduleName === 'qgrid') {
    // qgrid wants to use base/js/dialog (if it's available) for full-screen tables
    // https://github.com/quantopian/qgrid/blob/877b420/js/src/qgrid.widget.js#L11-L16
    // Maybe that's worth supporting someday, but for now, we define it to be nothing
    // to avoid require('qgrid') from producing an error
    (window as any).define("base/js/dialog", [], function() { return null });
  }

  return requireLoader(moduleName, moduleVersion).then((widgetModule) => {
    if (moduleName === 'ipysigma') {
      patchSigmaView(widgetModule);
    }
    return widgetModule;
  }).finally(() => {
    (window as any).define.amd = oldAmd;
    const new$ = (window as any).$;
    if (new$ !== old$ && isJQuery(new$)) {
      // A module that put its own jQuery on `$` (e.g., itables' bundle) may have
      // escaped protectPageJQuery()'s guard when `$` is non-configurable; lend its
      // DataTables plugin to the page jQuery before restoring, like the guard's
      // refused-write path does
      lendDataTables(new$, old$);
    }
    (window as any).$ = old$;
    (window as any).jQuery = oldJQ;
  });
}

const manager = new OutputManager({ loader: shinyRequireLoader });

// Models this session has closed. Shiny replays an output's last rendered
// value when the output is re-bound (render.ui show/hide, remove_ui then
// insert_ui of the same id); if that value names a closed model, no
// comm_open is coming for it, so renderValue() must not wait on it.
const closedModels = new Set<string>();


/******************************************************************************
* Define the Shiny binding
******************************************************************************/

interface WidgetOutputValue {
  model_id: string;
  fill: boolean;
  widget_pkg: string;
}

// Elements that render meaningful content without element children or text
// (e.g. an Image widget's <img>, a direct <canvas>, an empty <button>).
const RENDERABLE_LEAF_TAGS = new Set([
  'AUDIO', 'BUTTON', 'CANVAS', 'EMBED', 'IFRAME', 'IMG', 'INPUT', 'OBJECT',
  'PICTURE', 'SELECT', 'SVG', 'TEXTAREA', 'VIDEO',
]);

// Ideally we'd extend Shiny's HTMLOutputBinding, but the implementation isn't exported
class IPyWidgetOutput extends Shiny.OutputBinding {
  private _views = new WeakMap<HTMLElement, DOMWidgetView>();

  find(scope: HTMLElement): JQuery<HTMLElement> {
    return $(scope).find(".shiny-ipywidget-output");
  }
  onValueError(el: HTMLElement, err: ErrorsMessageValue): void {
    this._removeView(el);
    Shiny.unbindAll(el);
    el.style.visibility = "inherit";
    this.renderError(el, err);
  }
  async renderValue(el: HTMLElement, data: WidgetOutputValue | null): Promise<void> {
    const hiddenVisibility = "hidden";
    const revealVisibility = "inherit";
    const renderToken = this._nextRenderToken(el);

    // Allow for a None/null value to hide the widget (css inspired by htmlwidgets)
    if (!data) {
      this._removeView(el);
      el.style.visibility = hiddenVisibility;
      return;
    }

    if (closedModels.has(data.model_id)) {
      // Render nothing; the server re-renders this output (with a fresh
      // model) once bind completes and reports the output visible again.
      this._removeView(el);
      el.replaceChildren();
      el.style.visibility = revealVisibility;
      return;
    }

    // Package-specific fill/resize behavior (see js/src/fill.ts)
    const behavior = WIDGET_BEHAVIORS[data.widget_pkg];

    // Shiny removes the output's `.recalculating` class (which is what hides
    // stale content via CSS, see shinywidgets.css) synchronously, before this
    // function runs -- i.e. before `create_view()`/`display_view()` below have
    // produced anything to show. Hide here too, so the previous render's
    // content never becomes visible again in that gap; `reveal()` undoes this
    // once the new view has actually rendered (see `_onImplementation` below).
    el.style.visibility = hiddenVisibility;

    // Only forward the potential to fill if `output_widget(fillable=True)`
    // _and_ the widget instance wants to fill
    const fill = data.fill && el.classList.contains("html-fill-container");
    el.classList.toggle("forward-fill-potential", fill);

    // At this time point, we should've already handled an 'open' message, and so
    // the model should be ready to use
    const model = await manager.get_model(data.model_id);

    // N.B. no `{ el }` option: base-manager just passes options through to
    // `view.options`, which nothing reads; attachment happens in display_view
    const view = await manager.create_view(model);
    this._removeView(el);
    el.replaceChildren();
    await manager.display_view(view, el);
    this._views.set(el, view);
    view.once("remove", () => {
      if (this._views.get(el) === view) {
        this._views.delete(el);
      }
    });

    // The ipywidgets container (.lmWidget)
    const lmWidget = el.children[0] as HTMLElement;

    const setupHook = fill ? "setupFill" : "setupFixedSize";
    // A Map subclass defined outside ipyleaflet (e.g. in app code) gets its
    // own widget_pkg, so fall back to ipyleaflet's behavior for anything that
    // renders as a leaflet map (the class is added when the view renders,
    // hence the check inside the callback)
    const maybeLeaflet = !fill && behavior?.setupFixedSize === undefined;
    if (behavior?.[setupHook] !== undefined || maybeLeaflet) {
      // No timeout fallback here: running size setup before the
      // implementation exists is worse than waiting -- e.g. quak's setupFill
      // early-returns when its .quak element is absent, and (with the
      // observer already disconnected) a late implementation would never
      // get its fill setup. The reveal wait below gets the fallback instead.
      this._onImplementation(lmWidget, () => {
        // Don't set up fill/size behavior if this view has since been replaced
        if (this._views.get(el) !== view) return;
        const resolved =
          maybeLeaflet && lmWidget.classList.contains("leaflet-widgets")
            ? ipyleafletBehavior
            : behavior;
        const setupSize = resolved?.[setupHook];
        if (!setupSize) return;
        const cleanup = setupSize({ el, lmWidget, view, model, widgetWantsFill: data.fill });
        if (cleanup) view.once("remove", cleanup);
      });
    }
    this._onImplementation(lmWidget, () => {
      const ctx: PostDisplayContext = {
        el,
        lmWidget,
        view,
        model,
        widgetWantsFill: data.fill,
        isStale: () => !this._isCurrentRenderToken(el, renderToken),
        dispatchResize: () => this._doResize(),
        reveal: () => {
          if (this._isCurrentRenderToken(el, renderToken)) {
            el.style.visibility = revealVisibility;
          }
        },
      };
      if (behavior?.onDisplayed) {
        behavior.onDisplayed(ctx);
      } else {
        ctx.dispatchResize();
        ctx.reveal();
      }
    }, 1000);
  }
  _nextRenderToken(el: HTMLElement): number {
    const trackedEl = el as HTMLElement & { __shinywidgetsRenderToken?: number };
    const nextToken = (trackedEl.__shinywidgetsRenderToken ?? 0) + 1;
    trackedEl.__shinywidgetsRenderToken = nextToken;
    return nextToken;
  }
  _isCurrentRenderToken(el: HTMLElement, token: number): boolean {
    return (el as HTMLElement & { __shinywidgetsRenderToken?: number }).__shinywidgetsRenderToken === token;
  }
  // timeoutMs: when given, run the callback anyway after that long even if
  // the implementation never renders -- appropriate only for callbacks whose
  // work is harmless when the implementation is still absent (i.e., resize
  // and reveal, which keep the output from staying hidden forever when a
  // widget renders nothing at all, such as an empty HTML value).
  _onImplementation(lmWidget: HTMLElement, callback: () => void, timeoutMs?: number): void {
    if (this._hasImplementation(lmWidget)) {
      callback();
      return;
    }

    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      mo.disconnect();
      clearTimeout(timer);
      callback();
    };

    // Some widget implementation (e.g., ipyleaflet, pydeck) won't actually
    // have rendered to the DOM at this point, so wait until they do
    const mo = new MutationObserver((_mutations) => {
      if (this._hasImplementation(lmWidget)) finish();
    });
    // Watch the whole subtree, including text changes: an already-attached
    // but empty container can receive its content later without any mutation
    // to lmWidget's direct child list, and that content is what the
    // readiness predicate checks.
    mo.observe(lmWidget, {childList: true, subtree: true, characterData: true});

    const timer = timeoutMs === undefined ? undefined : setTimeout(finish, timeoutMs);
  }
  _doResize(): void {
    // Trigger resize event to force layout (setTimeout() is needed for altair)
    // TODO: debounce this call?
    setTimeout(() => {
      window.dispatchEvent(new Event('resize'))
    }, 0);
  }
  _hasImplementation(lmWidget: HTMLElement): boolean {
    // The view's root can itself be the implementation: an ipywidgets
    // Button's root IS a <button> (holding its description as text) and an
    // Image widget's root is an <img>. Deliberately not
    // lmWidget.children.length > 0: a pending container child (attached
    // before its real content, e.g. quak's wrapper ahead of .quak) must not
    // count as rendered.
    if (
      RENDERABLE_LEAF_TAGS.has(lmWidget.tagName) ||
      (lmWidget.shadowRoot?.children.length ?? 0) > 0 ||
      this._hasDirectText(lmWidget)
    ) {
      return true;
    }
    // Not just lmWidget.children[0]: DescriptionView (the base of most
    // ipywidgets controls, e.g. HTML, sliders) always inserts a <label> --
    // empty and display:none if the widget has no description -- as the
    // first child, ahead of the widget's actual implementation.
    for (const impl of Array.from(lmWidget.children)) {
      const implEl = impl as HTMLElement;
      if (impl.children.length > 0 || implEl.shadowRoot?.children.length) {
        return true;
      }
      if (RENDERABLE_LEAF_TAGS.has(implEl.tagName)) {
        return true;
      }
      // A rendered implementation can also be a bare text node (e.g.,
      // HTML("foo") sets text inside .widget-html-content) or a leaf control
      // (e.g., a <button> holding only text). The description <label> is
      // excluded: it isn't the implementation, and it can carry text while
      // the actual content is still pending.
      if (!implEl.classList.contains('widget-label') && (implEl.textContent?.trim() ?? '') !== '') {
        return true;
      }
    }
    return false;
  }
  // Direct text nodes only: textContent would also pick up a description
  // <label> descendant whose content is still pending.
  private _hasDirectText(el: HTMLElement): boolean {
    for (const node of Array.from(el.childNodes)) {
      if (node.nodeType === Node.TEXT_NODE && (node.textContent?.trim() ?? '') !== '') {
        return true;
      }
    }
    return false;
  }
  _removeView(el: HTMLElement): void {
    const view = this._views.get(el);
    this._views.delete(el);
    if (view) {
      manager.removeViewTree(view);
    }
  }
}

const widgetOutputBinding = new IPyWidgetOutput();
Shiny.outputBindings.register(widgetOutputBinding, "shiny.IPyWidgetOutput");

// Dynamic UI (render.ui swapping content, remove_ui/insert_ui) can unbind an
// output without going through onValueError or renderValue(null); without
// this the view stays alive, keeps receiving model updates, and is never released.
$(document).on("shiny:unbound", (event) => {
  const el = event.target as unknown as HTMLElement;
  const bindingType = (event as unknown as { bindingType?: string }).bindingType;
  if (bindingType === "output" && el.classList.contains("shiny-ipywidget-output")) {
    widgetOutputBinding._removeView(el);
  }
});


// Due to the way HTMLManager (and widget implementations) get loaded (via
// require.js), the binding registration above can happen _after_ Shiny has
// already bound the DOM, especially in the dynamic UI case (i.e., output_binding()'s
// dependencies don't come in until after initial page load). And, in the dynamic UI
// case, UI is rendered asychronously via Shiny.shinyapp.taskQueue, so if it exists,
// we probably need to re-bind the DOM after the taskQueue is done.
const taskQueue = Shiny?.shinyapp?.taskQueue;
if (taskQueue) {
  taskQueue.enqueue(() => Shiny.bindAll(document.body));
}

/******************************************************************************
* Handle messages from the server-side Widget
******************************************************************************/

// ES modules referenced by widget models (e.g., Panel's Perspective).
// They can't ride the dependency channel: their import() must be awaited
// (models consult the globals at render time), and only import() exposes
// a module's exports.
type ModuleAssets = {
  // Side-effect-only modules to import.
  urls?: string[];
  // Global name -> module URL; the module's default export is assigned to
  // the global.
  exports?: Record<string, string>;
};

// Initialize the comm and model when a new widget is created
// This is basically our version of https://github.com/jupyterlab/jupyterlab/blob/d33de15/packages/services/src/kernel/default.ts#L1144-L1176
Shiny.addCustomMessageHandler("shinywidgets_comm_open", async (msg_txt) => {
  setBaseURL();
  const msg = jsonParse(msg_txt);
  const deps = msg.content.html_deps as HtmlDep[];
  // Dependencies (e.g. BokehJS) must finish loading before the model is
  // constructed below; otherwise require() of the widget's module fails.
  await Shiny.renderDependenciesAsync(deps);
  await loadModules(msg.content.modules as ModuleAssets | undefined);
  if (msg.content.protect_jquery) protectPageJQuery();
  const comm = new ShinyComm(msg.content.comm_id);
  // An explicit model_id survives widget re-creation on the Python side, so
  // an id can reopen after being closed; it must not stay marked closed or
  // renderValue() would render nothing for it.
  closedModels.delete(msg.content.comm_id);
  manager.handle_comm_open(comm, msg);
});

// Handle any mutation of the model (e.g., add a marker to a map, without a full redraw)
// Basically out version of https://github.com/jupyterlab/jupyterlab/blob/d33de15/packages/services/src/kernel/default.ts#L1200-L1215
Shiny.addCustomMessageHandler("shinywidgets_comm_msg", async (msg_txt) => {
  const msg = jsonParse(msg_txt);
  const id = msg.content.comm_id;
  if (!manager.has_model(id)) {
    console.error(`Couldn't handle message for model ${id} because it doesn't exist.`);
    return;
  }
  try {
    const m = await manager.get_model(id);
    // @ts-ignore for some reason IClassicComm doesn't have this method, but we do
    m.comm.handle_msg(msg);
  } catch (err) {
    console.error("Error handling message:", err);
  }
});


// Handle the closing of a widget/comm/model
Shiny.addCustomMessageHandler("shinywidgets_comm_close", async (msg_txt) => {
  const msg = jsonParse(msg_txt);
  const id = msg.content.comm_id;
  closedModels.add(id);
  if (!manager.has_model(id)) {
    console.error(`Couldn't close model ${id} because it doesn't exist.`);
    return;
  }

  try {
    const m = await manager.get_model(id);

    // Some widget views need explicit teardown before model.close() removes them.
    if (m.views) {
      await Promise.all(
        Object.values(m.views).map(async (viewPromise) => {
          try {
            manager.removeViewTree(await viewPromise);
          } catch (err) {
            console.error("Error cleaning up view:", err);
          }
        })
      );
    }

    // View removal updates _view_count. Mark the comm as inactive first so that
    // save_changes() does not try to send those updates after the comm is gone.
    m.comm_live = false;

    // Close model after all views are cleaned up. Python closed the comm, so
    // tell the model (as its own _handle_comm_closed would) not to close it
    // again, which would send a comm_close back.
    try {
      await m.close(true);
    } catch (closeErr) {
      if (!isIgnorableTeardownError(closeErr)) {
        console.error("Unexpected error while closing model:", closeErr);
      }
    }

    // HTMLManager releases the model from its registry on comm:close.
    try {
      m.trigger("comm:close");
    } catch (triggerErr) {
      if (!isIgnorableTeardownError(triggerErr)) {
        console.error("Unexpected error while triggering comm:close:", triggerErr);
      }
    }
  } catch (err) {
    console.error("Error during model cleanup:", err);
  }
});

$(document).on("shiny:connected", () => {
  setConnected(true);
});

$(document).on("shiny:disconnected", () => {
  setConnected(false);
  manager.clear_state();
});

// When in filling layout, some widgets (specifically, altair) incorrectly think their
// height is 0 after it's shown, hidden, then shown again. As a workaround, trigger a
// resize event when a tab is shown.
// TODO: This covers the 95% use case, but it's definitely not an ideal way to handle
// this situation. A more robust solution would use IntersectionObserver to detect when
// the widget becomes visible. Or better yet, we'd get altair to handle this situation
// better.
// https://github.com/posit-dev/py-shinywidgets/issues/172
document.addEventListener('shown.bs.tab', event => {
  window.dispatchEvent(new Event('resize'));
})

// Our version of https://github.com/jupyter-widgets/widget-cookiecutter/blob/9694718/%7B%7Bcookiecutter.github_project_name%7D%7D/js/lib/extension.js#L8
function setBaseURL(x: string = '') {
  const base_url = document.querySelector('body').getAttribute('data-base-url');
  if (!base_url) {
    document.querySelector('body').setAttribute('data-base-url', x);
  }
}

function isIgnorableTeardownError(err: unknown): boolean {
  const msg = errorMessage(err).toLowerCase();
  return (
    msg.includes("widget is not attached") ||
    msg.includes("no comm channel defined")
  );
}

function errorMessage(err: unknown): string {
  if (err instanceof Error) {
    return err.message;
  }
  return String(err);
}

async function loadModules(modules?: ModuleAssets): Promise<void> {
  if (!modules) return;
  const importUrl = (url: string) =>
    import(/* webpackIgnore: true */ new URL(url, document.baseURI).href);
  await Promise.all((modules.urls ?? []).map(importUrl));
  const globals = window as unknown as Record<string, unknown>;
  for (const [name, url] of Object.entries(modules.exports ?? {})) {
    const module = (await importUrl(url)) as { default: unknown };
    globals[name] = module.default;
  }
}
