// Helpers for tearing down widget views. These reach into third-party
// internals (Lumino's message protocol, ipyleaflet's native Leaflet map,
// plotly <6's FigureView) that aren't dependencies of this bundle, so they're
// deliberately loosely typed -- keep the loose types and their justifications
// together here.
import type { DOMWidgetView, WidgetView } from '@jupyter-widgets/base';

// `create_child_view` stamps `options.parent` on every child view; `options`
// is `any` upstream, so read the narrowest shape from it.
export function viewParent(view: WidgetView): WidgetView | undefined {
  return (view.options as { parent?: WidgetView } | undefined)?.parent;
}

export function hasAncestor(view: WidgetView, root: WidgetView): boolean {
  for (let parent = viewParent(view); parent; parent = viewParent(parent)) {
    if (parent === root) {
      return true;
    }
  }
  return false;
}

// Built structurally (Lumino's `Message` has no private state) so the bundle
// doesn't carry a second copy of @lumino/messaging alongside libembed's.
type LuminoMessage = Parameters<DOMWidgetView['luminoWidget']['processMessage']>[0];

function detachMessage(type: 'before-detach' | 'after-detach'): LuminoMessage {
  return { type, isConflatable: false, conflate: () => false };
}

const BEFORE_DETACH_MSG = detachMessage('before-detach');
const AFTER_DETACH_MSG = detachMessage('after-detach');

// Lumino's `dispose()` calls `detach()` when its "attached" flag is set, and
// `detach()` throws "Widget is not attached" if the node already left the DOM
// (e.g. ipyleaflet replaces its container on teardown). Replaying the detach
// messages clears the flag so `view.remove()` -> `luminoWidget.dispose()` can
// finish cleanly.
export function finishDetach(view: WidgetView): void {
  if (!('luminoWidget' in view)) {
    return;
  }
  const w = (view as DOMWidgetView).luminoWidget;
  if (w && w.parent === null && w.isAttached && !w.node.isConnected) {
    w.processMessage(BEFORE_DETACH_MSG);
    w.processMessage(AFTER_DETACH_MSG);
  }
}

// Dispose of native third-party resources that `view.remove()` doesn't
// reach, before the view is removed.
export function disposeNative(view: WidgetView): void {
  if (!view.model) {
    return;
  }

  // plotly <6's FigureView leaves DOM state and listeners behind unless
  // destroy() runs before the view is removed; clearing the model
  // back-reference drops its resize listener (#166, #169). plotly >=6 is
  // anywidget-based and cleans up in remove(), so hasDestroy() is false there.
  if (hasDestroy(view)) {
    view.destroy();
    delete (view as any).model;
    return;
  }

  disposeLeafletMap(view);
  disposeNglviewStage(view);
}

const patchedMplCanvasViews = new WeakSet<WidgetView>();

// ipympl's MPLCanvasView overrides remove() without calling super.remove(), so
// Lumino disposal, stopListening(), and the "remove" event (which fires our
// cleanups) never happen, and a container that drops the view (e.g. a VBox
// whose children change) leaves its figure on screen. Patch the class once,
// on its first view, so remove() also runs the remove() it overrides. Running
// the base remove() twice is harmless (ipywidgets' own Lumino disposal already
// re-enters it), so this stays safe if ipympl starts calling super.remove().
export function patchMplCanvasRemove(view: WidgetView): void {
  if (view.model.get('_view_name') !== 'MPLCanvasView') {
    return;
  }
  const proto: WidgetView = Object.getPrototypeOf(view);
  if (patchedMplCanvasViews.has(proto)) {
    return;
  }
  patchedMplCanvasViews.add(proto);
  const nativeRemove = proto.remove;
  const baseRemove = (Object.getPrototypeOf(proto) as WidgetView).remove;
  proto.remove = function (this: WidgetView) {
    nativeRemove.call(this);
    return baseRemove.call(this);
  };
}

interface DestroyableView {
  destroy(): void;
}

function hasDestroy(view: WidgetView): view is WidgetView & DestroyableView {
  return typeof (view as Partial<DestroyableView>).destroy === 'function';
}

// ipyleaflet's LeafletMapView stores the native Leaflet map as `view.obj`
// (loosely typed: Leaflet isn't a dependency of this bundle) and never
// disposes it on remove, so its resize timer and event handlers keep firing
// -- and touching `model.views` -- after the model has closed.
interface NativeLeafletMap {
  _sizeTimer?: ReturnType<typeof setTimeout>;
  off(events?: string): void;
  remove(): void;
}

// nglview's NGLView never overrides remove(), and nothing ever disposes its
// NGL stage (nglview 4.0.1), so every removed viewer keeps its render loop and
// WebGL context -- browsers cap the number of live contexts, so repeated
// re-renders can exhaust them. `view.stage` is loosely typed because NGL
// isn't a dependency of this bundle. Note the `stage` reference is left in
// place after disposal: nglview's own pending callbacks (e.g. its deferred
// camera-orientation sync) still read `this.stage.viewerControls` after the
// view is gone, and would throw on a deleted stage.
interface NativeNglStage {
  dispose(): void;
}

function disposeNglviewStage(view: WidgetView): void {
  const tracked = view as WidgetView & {
    stage?: NativeNglStage;
    __shinywidgetsNativeDisposed?: boolean;
  };
  const stage = tracked.stage;
  if (
    tracked.__shinywidgetsNativeDisposed ||
    !view.model ||
    view.model.get('_view_name') !== 'NGLView' ||
    !stage ||
    typeof stage.dispose !== 'function'
  ) {
    return;
  }
  tracked.__shinywidgetsNativeDisposed = true;
  stage.dispose();
}

// Removing a view directly -- an ipywidgets container whose children change
// calls remove() on the dropped child views itself -- never reaches
// removeViewTree(), so hook the stage disposal into the view's own removal too.
// disposeNglviewStage() is idempotent, so the teardown path may also dispose
// before removing (as it does for plotly and leaflet).
export function disposeNglviewStageOnRemove(view: WidgetView): void {
  if (!view.model || view.model.get('_view_name') !== 'NGLView') {
    return;
  }
  view.once('remove', () => disposeNglviewStage(view));
}

function disposeLeafletMap(view: WidgetView): void {
  const tracked = view as WidgetView & {
    obj?: NativeLeafletMap;
    __shinywidgetsNativeDisposed?: boolean;
  };
  const map = tracked.obj;
  if (
    tracked.__shinywidgetsNativeDisposed ||
    !view.model ||
    view.model.get('_view_name') !== 'LeafletMapView' ||
    !map
  ) {
    return;
  }
  tracked.__shinywidgetsNativeDisposed = true;
  clearTimeout(map._sizeTimer);
  map.off('moveend movestart zoomend');
  view.once('remove', () => {
    try {
      map.remove();
    } finally {
      clearTimeout(map._sizeTimer);
      map.off();
    }
  });
}

// Patches for ipysigma's SigmaView. These patch the module in the loader (unlike
// the create_view-time patches above) because setLayout() runs as soon as the view
// is displayed, before any create_view() callback could intervene. `widgetModule`
// is the module's untyped export object.
//
// - ipysigma reuses the `layout` trait (normally an ipywidgets Layout model) for
//   its node positions, so a plain object reaches DOMWidgetView.setLayout(), which
//   tries to create a child view for it and rejects. The view never has a Layout
//   to apply, so make setLayout() a no-op.
// - shinywidgets rewrites sigma's default height to 100% so the graph fills (see
//   ipysigma_layout_defaults()), but the output container's height may not be
//   definite (e.g. output_widget(fillable=False)), so it collapses to 0 and sigma
//   throws. Python can't see the container, so fall back to sigma's default height
//   once displayed.
// - sigma's kill() drops its canvases but not their WebGL contexts, which keep
//   counting against the browser's per-page cap (~16) until GC. Past the cap the
//   browser evicts the oldest contexts, so re-rendering one graph a few times
//   blanks the other graphs on the page. Release them before the view goes.
interface SigmaView {
  el: HTMLElement;
  container: HTMLElement;
  model: { set(key: 'height', value: string): void };
  displayed: Promise<unknown>;
  render(): unknown;
  remove(): void;
}

const SIGMA_DEFAULT_HEIGHT = '500px';

export function patchSigmaView(widgetModule: { SigmaView?: { prototype: SigmaView } }): void {
  const proto = widgetModule.SigmaView?.prototype;
  if (!proto) {
    return;
  }
  const nativeRender = proto.render;
  const nativeRemove = proto.remove;
  Object.assign(proto, {
    setLayout: () => {},
    render(this: SigmaView) {
      // Registered before the native render() registers the handler that creates
      // the sigma renderer, so this runs first
      void this.displayed.then(() => {
        if (this.el.style.height.endsWith('%') && this.el.clientHeight === 0) {
          // ipysigma's fullscreen exit restores the model's height
          this.model.set('height', SIGMA_DEFAULT_HEIGHT);
          this.el.style.height = SIGMA_DEFAULT_HEIGHT;
          this.container.style.height = SIGMA_DEFAULT_HEIGHT;
        }
      });
      return nativeRender.call(this);
    },
    remove(this: SigmaView) {
      // getContext() returns the canvas' existing context (or null for sigma's 2D
      // canvases), so this never creates one
      for (const canvas of this.el.querySelectorAll('canvas')) {
        const gl = canvas.getContext('webgl2') ?? canvas.getContext('webgl');
        gl?.getExtension('WEBGL_lose_context')?.loseContext();
      }
      return nativeRemove.call(this);
    },
  });
}
