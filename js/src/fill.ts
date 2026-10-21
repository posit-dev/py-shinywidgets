import type { DOMWidgetView, WidgetModel } from '@jupyter-widgets/base';
import { setupKeplerAutoHeight } from './keplergl';
import { setupMplAutoResize } from './mpl';
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
  // Keep the output hidden until onDisplayed() reveals it (e.g., plotly
  // settles its initial size before first paint to avoid flicker)
  hideUntilSettled?: boolean;
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

// Plotly FigureWidget may first render at its internal 360px fallback, then
// resize after paint. Keep it hidden until a direct Plotly resize completes
// so the first visible paint is already settled.
const plotlyBehavior: WidgetBehavior = {
  hideUntilSettled: true,
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
  keplergl: keplerglBehavior,
  plotly: plotlyBehavior,
  quak: quakBehavior,
};
