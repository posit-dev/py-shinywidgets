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
