import type { DOMWidgetView, WidgetModel } from '@jupyter-widgets/base';
import { setupJscatterAutoHeight, setupJscatterFixedHeight } from './jscatter';
import { setupKeplerAutoHeight } from './keplergl';
import { setupMplAutoResize } from './mpl';
import { findPlotlyGraphDiv, waitForPlotlyReadyToReveal } from './plotly';
import { setupQuakFit } from './quak';

/**
 * Per-package fill/resize behavior for widget outputs, keyed by `widget_pkg`
 * (the Python package's root module name, computed server-side and sent as
 * part of the output value -- the same key used by AS_WIDGET_MAP in
 * _as_widget.py and _LAYOUT_DEFAULTS in _render_widget_base.py).
 *
 * The output binding applies the shared machinery (waiting for the widget
 * implementation to render, staleness guards, cleanup on view removal) and
 * dispatches to these hooks for package-specific behavior, so renderValue()
 * doesn't accumulate `isXWidget` branches.
 */

export interface BehaviorContext {
  // The .shiny-ipywidget-output container
  el: HTMLElement;
  // The ipywidgets container (.lmWidget)
  lmWidget: HTMLElement;
  view: DOMWidgetView;
  model: WidgetModel;
  // The server-side fill decision (set_layout_defaults()): false means the
  // widget itself opted out of filling (e.g., an explicit size), so a
  // setupFixedSize() hook must leave its size alone
  widgetWantsFill: boolean;
}

export interface PostDisplayContext extends BehaviorContext {
  // True if a newer renderValue() call has superseded this render; callbacks
  // should bail out without side effects
  isStale(): boolean;
  // Trigger a window resize event (forces layout for widgets like altair)
  dispatchResize(): void;
  // Reveal the output (a no-op if the render is stale)
  reveal(): void;
}

export interface WidgetBehavior {
  // Runs (once the widget's implementation has rendered) when the output is
  // inside a fill container. May return a cleanup function, which the output
  // binding calls when the view is removed.
  setupFill?(ctx: BehaviorContext): void | (() => void);
  // Like setupFill(), but runs when the output isn't filling its container
  // (e.g., it has an explicit height, or the widget opted out of filling), for
  // widgets that need help respecting the size they're given.
  setupFixedSize?(ctx: BehaviorContext): void | (() => void);
  // Custom post-display behavior (runs once the widget's implementation has
  // rendered). Defaults to dispatchResize().
  onDisplayed?(ctx: PostDisplayContext): void;
}

// ipympl figures don't fit themselves to their container, so drive the
// figure size from the container's size (i.e., make fill actually work)
const ipymplBehavior: WidgetBehavior = {
  setupFill: ({ el, lmWidget, model }) => setupMplAutoResize(el, lmWidget, model),
};

// jupyter-scatter plots have a fixed pixel height, so drive it from the
// container's size (i.e., make fill and an explicit output height actually work)
const jscatterBehavior: WidgetBehavior = {
  setupFill: ({ el, lmWidget, model }) => setupJscatterAutoHeight(el, lmWidget, model),
  setupFixedSize: ({ el, lmWidget, model }) => setupJscatterFixedHeight(el, lmWidget, model),
};

// Plotly FigureWidget may first render at its internal 360px fallback, then
// resize after paint. The output is already hidden at this point (every
// render starts hidden, see renderValue()); keep it that way until a direct
// Plotly resize completes, so the first visible paint is already settled.
const plotlyBehavior: WidgetBehavior = {
  onDisplayed: (ctx) => {
    if (ctx.isStale()) return;

    const plotEl = findPlotlyGraphDiv(ctx.lmWidget);
    if (!plotEl) {
      ctx.dispatchResize();
      ctx.reveal();
      return;
    }

    void waitForPlotlyReadyToReveal(plotEl, ctx.dispatchResize).finally(ctx.reveal);
  },
};

const quakBehavior: WidgetBehavior = {
  setupFill: ({ el, lmWidget }) => setupQuakFit(el, lmWidget, true),
  setupFixedSize: ({ el, lmWidget }) => setupQuakFit(el, lmWidget, false),
};

// Aspect-management ownership per camera, persisted across view lifetimes
// (a cached Renderer gets a fresh view, and a fresh setupPythreejsResize()
// closure, on every render): the aspect value we last set on each camera.
// Without it, a re-render's new view would adopt a user-set aspect as the
// managed baseline and overwrite it on the first resize.
const managedCameraAspects = new WeakMap<WidgetModel, number>();

// A pythreejs Renderer draws into a canvas fixed to its _width/_height pixel
// traits (and three.js doesn't update the camera's aspect ratio when the
// canvas resizes), so drive both from the container's size. The traits are
// synced, so the Python-side Renderer/camera see the new values too.
function setupPythreejsResize({ el, lmWidget, model }: BehaviorContext): () => void {
  // An inline <canvas> sits on the text baseline, leaving a ~6px strut of
  // line height below it. In a container whose height is content-derived
  // (plain page_fluid, an auto-height card), that strut makes el taller than
  // the canvas, so sizing the canvas to el grows el, which fires the observer
  // again -- an unbounded feedback loop. Block display removes the strut, so
  // sizing the canvas to el is a fixed point.
  const canvas = lmWidget.querySelector('canvas');
  if (canvas) canvas.style.display = 'block';

  // Python can replace the camera in place (renderer.camera = ...), so
  // (re)capture the active camera on change:camera rather than only here.
  let camera: WidgetModel | undefined;
  // Manage the aspect ratio only while it holds a value we set (or the
  // initial one): a user-set aspect (from either side) wins.
  let lastAspect: number | undefined;
  let lastWidth = -1;
  let lastHeight = -1;

  const applySize = (w: number, h: number) => {
    model.set('_width', w);
    model.set('_height', h);
    model.save_changes();
    if (camera && lastAspect !== undefined && camera.get('aspect') === lastAspect) {
      lastAspect = w / h;
      camera.set('aspect', lastAspect);
      camera.save_changes();
      managedCameraAspects.set(camera, lastAspect);
    }
  };

  const trackCamera = () => {
    camera = model.get('camera') as WidgetModel | undefined;
    // A camera we've managed before keeps the aspect we last set as the
    // baseline, so a user-set aspect (from either side) still wins after a
    // re-render; a never-managed camera adopts its current (initial) aspect.
    const managed = camera ? managedCameraAspects.get(camera) : undefined;
    if (managed !== undefined) {
      lastAspect = managed;
    } else {
      const aspect = camera?.get('aspect');
      lastAspect = typeof aspect === 'number' ? aspect : undefined;
    }
    // A replacement camera still holds its own (stale) aspect, so apply the
    // current dimensions immediately. resizeToFit()'s dimension cache would
    // suppress this when the container size hasn't changed.
    if (lastWidth > 0 && lastHeight > 0) applySize(lastWidth, lastHeight);
  };

  const resizeToFit = () => {
    const w = el.clientWidth;
    const h = el.clientHeight;
    if (w <= 0 || h <= 0 || (w === lastWidth && h === lastHeight)) return;
    lastWidth = w;
    lastHeight = h;
    applySize(w, h);
  };

  trackCamera();
  model.on('change:camera', trackCamera);
  const observer = new ResizeObserver(() => resizeToFit());
  // Observe the output container (not the widget): with the strut removed
  // above, the container tracks the canvas exactly, so resizing the canvas
  // to it doesn't change it and the observer settles.
  observer.observe(el);
  resizeToFit();
  return () => {
    model.off('change:camera', trackCamera);
    observer.disconnect();
  };
}

const pythreejsBehavior: WidgetBehavior = {
  setupFill: (ctx) => setupPythreejsResize(ctx),
  // A fixed-size output with an explicit height (e.g.,
  // output_widget(height="250px", fillable=False)) gets the canvas sized to
  // it too, unless the Renderer opted out of filling (its own explicit
  // width/height), in which case its pixel size is respected. An unsized
  // non-fillable output keeps the widget's own size rather than stretching
  // the canvas to the output's full width.
  setupFixedSize: (ctx) =>
    ctx.widgetWantsFill && ctx.el.style.height ? setupPythreejsResize(ctx) : undefined,
};

// kepler.gl's size comes from a pixel `height` trait, so it needs to be driven
// from the container whenever the container's height is defined by the app
// (a filling layout, or an explicit output_widget(height=)).
const keplerglBehavior: WidgetBehavior = {
  setupFill: ({ el, model }) => setupKeplerAutoHeight(el, model),
  setupFixedSize: ({ el, model }) => {
    if (el.style.height) return setupKeplerAutoHeight(el, model);
  },
};

// shinywidgets.css sizes an ipyleaflet map to its (non-filling) output's
// definite height via flex layout, unless the map has an explicit
// `Layout(height=...)` (an inline style), which takes precedence. A CSS
// attribute selector can't tell an inline `height:` apart from `min-height:`/
// `max-height:`, so track the explicit height with a class instead. Exported
// so output.ts can also apply it to Map subclasses (their widget_pkg is the
// subclass's package, not "ipyleaflet").
export const ipyleafletBehavior: WidgetBehavior = {
  setupFixedSize: ({ lmWidget }) => {
    if (!lmWidget.classList.contains('leaflet-widgets')) return;
    const sync = () =>
      lmWidget.classList.toggle('shinywidgets-explicit-height', lmWidget.style.height !== '');
    sync();
    const observer = new MutationObserver(sync);
    observer.observe(lmWidget, { attributes: true, attributeFilter: ['style'] });
    return () => observer.disconnect();
  },
};

export const WIDGET_BEHAVIORS: Record<string, WidgetBehavior> = {
  ipympl: ipymplBehavior,
  jscatter: jscatterBehavior,
  keplergl: keplerglBehavior,
  plotly: plotlyBehavior,
  pythreejs: pythreejsBehavior,
  quak: quakBehavior,
  ipyleaflet: ipyleafletBehavior,
};
