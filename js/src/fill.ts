import type { DOMWidgetView, WidgetModel } from '@jupyter-widgets/base';
import { setupIpyvolumeAutoResize } from './ipyvolume';
import { setupJscatterAutoHeight, setupJscatterFixedHeight } from './jscatter';
import { setupKeplerAutoHeight } from './keplergl';
import { setupMplAutoResize } from './mpl';
import { setupNglviewAutoSize } from './nglview';
import { bindPlotlyEvents, findPlotlyGraphDiv, waitForPlotlyReadyToReveal } from './plotly';
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
  // Identity check, consulted when the server-reported `widget_pkg` finds no
  // behavior. A widget class defined outside the widget package (e.g. an
  // NGLWidget subclass in app code) reports the app's module as its
  // widget_pkg, so package-based dispatch can't see it; these behaviors match
  // on what the widget inherits instead (e.g. the view name).
  matches?(model: WidgetModel): boolean;
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

    void waitForPlotlyReadyToReveal(plotEl, ctx.dispatchResize).finally(() => {
      bindPlotlyEvents(plotEl, ctx.model);
      ctx.reveal();
    });
  },
};

// ipyvolume figures render at a fixed pixel size and need their canvas
// resized to the container (see setupIpyvolumeAutoResize). The same applies
// when the output (or the widget's own Layout) has an explicit height;
// otherwise the figure's intrinsic size applies, so leave it alone.
const ipyvolumeBehavior: WidgetBehavior = {
  setupFill: ({ el, view, model }) => setupIpyvolumeAutoResize(el, view, model),
  setupFixedSize: ({ el, lmWidget, view, model, widgetWantsFill }) =>
    // Only resize when the output (or the widget's own Layout, which lands on
    // the widget element) has an explicit height; otherwise the figure's
    // intrinsic pixel size applies. Checked at resize time: the Layout style
    // may only be applied after setup runs.
    //
    // A Layout height on the widget is always a size to drive the canvas to,
    // but the output's CSS height only applies when the widget itself hasn't
    // opted out of filling (widgetWantsFill) -- an explicit figure size
    // (e.g., ipv.Figure(width=400, height=300)) keeps its pixel size even
    // inside an explicitly sized output.
    setupIpyvolumeAutoResize(
      el,
      view,
      model,
      () =>
        !!(
          (widgetWantsFill && (el.style.height || lmWidget.style.height)) ||
          (view.el as HTMLElement).style.height
        )
    ),
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

// nglview sizes its stage with fixed inline pixels (300px tall by default) and
// never re-measures its parent, so drive the stage size from the output: both
// dimensions when the output has a height of its own (a filling layout or an
// explicit output_widget(height=)), otherwise just the width.
const nglviewBehavior: WidgetBehavior = {
  // An app-defined NGLWidget subclass reports the app's own module as its
  // widget_pkg, but it inherits nglview's view
  matches: (model) => model.get('_view_name') === 'NGLView',
  setupFill: ({ el, view, model }) => setupNglviewAutoSize(el, view, model),
  // Track the output's height only when the widget wants to fill and the
  // output has a height of its own: a widget with a height of its own (e.g.
  // `NGLWidget(height=...)` or `layout.height`) keeps it even inside an
  // `output_widget(height=...)`, tracking only the width
  setupFixedSize: ({ el, view, model, widgetWantsFill }) =>
    setupNglviewAutoSize(el, view, model, widgetWantsFill && !!el.style.height),
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

// geolibre embeds its app in an <iframe> whose height comes from the widget's
// `height` trait; when that's left at the default, geolibre_layout_defaults()
// sets it to "100%", which only resolves against a sized view root. Mark the
// view root so shinywidgets.css can size it to the output (which is definite
// in the fixed-size cases that matter, e.g. output_widget(height=)); an
// indefinite output leaves the app at its flex-basis height.
export const geolibreBehavior: WidgetBehavior = {
  setupFixedSize: ({ lmWidget }) => {
    const mark = () => {
      const iframe = lmWidget.querySelector(':scope > iframe');
      if (iframe instanceof HTMLIFrameElement && iframe.style.height.endsWith('%')) {
        lmWidget.classList.add('shinywidgets-geolibre');
        return true;
      }
      return false;
    };
    // In geolibre's "remote" mode (which shinywidgets uses so the bundled app
    // loads same-origin), the <iframe> is only created after an async probe,
    // so it may not exist yet when this runs (the probe's placeholder text
    // already counts as "rendered").
    if (mark()) return;
    const mo = new MutationObserver(() => {
      if (mark()) mo.disconnect();
    });
    mo.observe(lmWidget, { childList: true });
    return () => mo.disconnect();
  },
};

// drawdata's widgets have an intrinsic pixel size (their width/height
// traits, 800x400 / 800x550 by default) that their frontends also cap the
// *display* to: ScatterWidget's <svg> gets an inline `max-width: {width}px`
// (and .dd-scatter-container a CSS `max-width: 1200px`), and BarWidget's
// chart <svg> gets fixed width/height attributes with no viewBox. The
// traits really define the *data
// coordinate space* (drawn points are stored in viewBox coordinates), so
// scaling the display around an unchanged viewBox is lossless (d3 resolves
// pointer coordinates through the svg's CTM, so brushing/dragging still
// works when scaled). Remove those caps so the widgets fill their
// container's width, with aspect-ratio preserving the coordinate aspect.
//
// In a sized output (a filling layout, or output_widget(height=)), scaling
// to the full width can make the chart taller than the output (e.g., a
// 1200x500 output grows the default 800x400 ScatterWidget to 1200x600),
// which the output's overflow:hidden then clips. So when the output's
// height is definite, also constrain the chart's width by the height left
// over after the controls. Returns a cleanup function when fitting.
function relaxDrawdataSize(ctx: BehaviorContext, fitHeight: boolean): (() => void) | void {
  const { el, lmWidget } = ctx;
  // Lift the containers' CSS width caps (and BarWidget's 20px vertical
  // margins, which just add slack in a sized output)
  for (const container of lmWidget.querySelectorAll<HTMLElement>(
    '.dd-scatter-container, .container'
  )) {
    container.style.maxWidth = 'none';
    container.style.marginTop = '0';
    container.style.marginBottom = '0';
  }
  // BarWidget's chart wrapper also carries a 20px bottom margin
  for (const wrap of lmWidget.querySelectorAll<HTMLElement>('.chart-container')) {
    wrap.style.marginBottom = '0';
  }
  // Find the chart svg: ScatterWidget's is the one with an inline pixel
  // max-width; BarWidget's is the one with pixel width/height attributes
  // and no viewBox (button icons are excluded -- they already have one).
  let chart: SVGSVGElement | undefined;
  for (const svg of lmWidget.querySelectorAll('svg')) {
    if (svg.style.maxWidth.endsWith('px')) {
      // ScatterWidget's chart svg: inline `max-width: {width}px` is the only
      // thing stopping its width:100%/aspect-ratio sizing from growing past
      // the trait width
      svg.style.maxWidth = 'none';
      chart = svg;
      continue;
    }
    // BarWidget's chart svg: fixed pixel width/height attributes, no
    // viewBox (button icons are excluded -- they already have a viewBox).
    // Give it one and let CSS scale it like ScatterWidget's.
    const w = Number(svg.getAttribute('width'));
    const h = Number(svg.getAttribute('height'));
    if (svg.getAttribute('viewBox') === null && w > 0 && h > 0) {
      svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
      svg.style.width = '100%';
      svg.style.height = 'auto';
      svg.style.aspectRatio = `${w} / ${h}`;
      chart = svg;
    }
  }

  // Fitting the height only makes sense when the output's height is
  // definite -- otherwise it's derived from the widget's own height, and
  // shrinking the chart would shrink the output (a feedback loop).
  //
  // BarWidget's chart svg is a direct child of its (classless, drawdata
  // 0.5.x) container, alongside the controls -- so measure the chart's own
  // position, not its parent's, to account for the controls above it.
  const wrap = chart?.parentElement;
  if (!fitHeight || !chart || !wrap) return;
  const chartSvg = chart;
  const chartWrap = wrap;

  const fit = () => {
    const viewBox = chartSvg.viewBox.baseVal;
    if (viewBox.width <= 0 || viewBox.height <= 0) return;
    // Available height = the output's bottom minus everything physically
    // above the chart (controls, margins). Measuring below-chart slack off
    // a container doesn't work in fill layouts, where the fill CSS chain
    // sizes the widget's containers to the output (so their bottoms no
    // longer track the chart's).
    const availH =
      el.getBoundingClientRect().bottom - chartSvg.getBoundingClientRect().top;
    const availW = chartWrap.clientWidth;
    const w = Math.floor(Math.min(availW, (availH * viewBox.width) / viewBox.height));
    chartSvg.style.width = `${Math.max(w, 1)}px`;
  };

  // Observing el (not the widget) is a fixed point: the chart's size changes
  // never change the definite-height output.
  const observer = new ResizeObserver(fit);
  observer.observe(el);
  fit();
  return () => observer.disconnect();
}

const drawdataBehavior: WidgetBehavior = {
  setupFill: (ctx) => relaxDrawdataSize(ctx, true),
  // Also relax in fixed-size outputs: BarWidget's fixed 800px width
  // otherwise overflows narrow containers, and full-width rendering matches
  // how other outputs (e.g., plotly) look in plain page flow. Only an
  // explicit output height is definite here, so only then fit the height.
  setupFixedSize: (ctx) => relaxDrawdataSize(ctx, !!ctx.el.style.height),
};

export const WIDGET_BEHAVIORS: Record<string, WidgetBehavior> = {
  drawdata: drawdataBehavior,
  ipympl: ipymplBehavior,
  ipyvolume: ipyvolumeBehavior,
  jscatter: jscatterBehavior,
  keplergl: keplerglBehavior,
  nglview: nglviewBehavior,
  plotly: plotlyBehavior,
  pythreejs: pythreejsBehavior,
  quak: quakBehavior,
  ipyleaflet: ipyleafletBehavior,
  geolibre: geolibreBehavior,
};

// The behavior for a widget whose package key isn't in WIDGET_BEHAVIORS (see
// WidgetBehavior.matches)
export function behaviorForModel(model: WidgetModel): WidgetBehavior | undefined {
  return Object.values(WIDGET_BEHAVIORS).find((behavior) =>
    behavior.matches ? behavior.matches(model) : false
  );
}
