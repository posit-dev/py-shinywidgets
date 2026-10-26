import type { DOMWidgetView, WidgetModel } from '@jupyter-widgets/base';
import { setupJscatterAutoHeight, setupJscatterFixedHeight } from './jscatter';
import { setupKeplerAutoHeight } from './keplergl';
import { setupMplAutoResize } from './mpl';
import { setupNglviewAutoSize } from './nglview';
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

    void waitForPlotlyReadyToReveal(plotEl, ctx.dispatchResize).finally(ctx.reveal);
  },
};

const quakBehavior: WidgetBehavior = {
  setupFill: ({ el, lmWidget }) => setupQuakFit(el, lmWidget, true),
  setupFixedSize: ({ el, lmWidget }) => setupQuakFit(el, lmWidget, false),
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
  setupFixedSize: ({ el, view, model }) =>
    setupNglviewAutoSize(el, view, model, !!el.style.height),
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
  nglview: nglviewBehavior,
  plotly: plotlyBehavior,
  quak: quakBehavior,
  ipyleaflet: ipyleafletBehavior,
};

// The behavior for a widget whose package key isn't in WIDGET_BEHAVIORS (see
// WidgetBehavior.matches)
export function behaviorForModel(model: WidgetModel): WidgetBehavior | undefined {
  return Object.values(WIDGET_BEHAVIORS).find((behavior) =>
    behavior.matches ? behavior.matches(model) : false
  );
}
