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

// kepler.gl's size comes from a pixel `height` trait, so it needs to be driven
// from the container whenever the container's height is defined by the app
// (a filling layout, or an explicit output_widget(height=)).
const keplerglBehavior: WidgetBehavior = {
  setupFill: ({ el, model }) => setupKeplerAutoHeight(el, model),
  setupFixedSize: ({ el, model }) => {
    if (el.style.height) return setupKeplerAutoHeight(el, model);
  },
};

export const WIDGET_BEHAVIORS: Record<string, WidgetBehavior> = {
  ipympl: ipymplBehavior,
  jscatter: jscatterBehavior,
  keplergl: keplerglBehavior,
  plotly: plotlyBehavior,
  quak: quakBehavior,
};
