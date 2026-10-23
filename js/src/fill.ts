import type { DOMWidgetView, WidgetModel } from '@jupyter-widgets/base';
import { setupJscatterAutoHeight, setupJscatterFixedHeight } from './jscatter';
import { setupMplAutoResize } from './mpl';
import { setupNglviewAutoSize } from './nglview';
import { findPlotlyGraphDiv, waitForPlotlyReadyToReveal } from './plotly';

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

// In most cases, we can get widgets to fill through Python/CSS, but quak
// doesn't have a Python API and uses shadow DOM, which can only be accessed
// from JS
const quakBehavior: WidgetBehavior = {
  setupFill: ({ lmWidget }) => {
    const impl = lmWidget.children[0] as HTMLElement | undefined;
    const quakWidget = impl?.shadowRoot?.querySelector('.quak') as HTMLElement | null;
    if (!impl || !quakWidget) return;
    impl.classList.add('html-fill-container', 'html-fill-item');
    quakWidget.style.maxHeight = 'unset';
  },
};

// nglview sizes its stage with fixed inline pixels (300px tall by default) and
// never re-measures its parent, so drive the stage size from the output: both
// dimensions when the output has a height of its own (a filling layout or an
// explicit output_widget(height=)), otherwise just the width.
const nglviewBehavior: WidgetBehavior = {
  setupFill: ({ el, view }) => setupNglviewAutoSize(el, view),
  setupFixedSize: ({ el, view }) => setupNglviewAutoSize(el, view, !!el.style.height),
};

export const WIDGET_BEHAVIORS: Record<string, WidgetBehavior> = {
  ipympl: ipymplBehavior,
  jscatter: jscatterBehavior,
  nglview: nglviewBehavior,
  plotly: plotlyBehavior,
  quak: quakBehavior,
};
