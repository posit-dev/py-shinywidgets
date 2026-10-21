import type { WidgetModel } from '@jupyter-widgets/base';

// The regl-scatterplot instance jupyter-scatter attaches to its plot container
interface ScatterplotApi {
  set(options: { height: number | 'auto' }): unknown;
}

// jupyter-scatter's default `height` (JSCATTER_DEFAULT_HEIGHT in
// _render_widget_base.py). Any other value was chosen by the user, unless the
// browser set it while sizing that same widget earlier.
const DEFAULT_HEIGHT = 240;

const autoSizedModels = new WeakSet<WidgetModel>();

/**
 * Like setupJscatterAutoHeight(), but for an output that isn't filling: the
 * plot takes the output's explicit height, unless the plot has a height of
 * its own. Returns a cleanup function, or nothing if there's nothing to size.
 */
export function setupJscatterFixedHeight(
  el: HTMLElement,
  lmWidget: HTMLElement,
  model: WidgetModel
): (() => void) | undefined {
  if (!el.style.height) return;
  if (model.get('height') !== DEFAULT_HEIGHT && !autoSizedModels.has(model)) return;
  return setupJscatterAutoHeight(el, lmWidget, model);
}

/**
 * jupyter-scatter sizes its plot from the model's pixel `height` trait (there's
 * no "auto" height), and ignores its container's size. To make
 * render_jscatter() outputs fit a sized container (a filling layout, or an
 * explicit output height), observe the container and drive `height` from its
 * size, which jupyter-scatter applies to its layout (and syncs back to the
 * Python widget). Its drawing surface doesn't follow the trait once rendered,
 * so it's switched to track its layout box instead.
 *
 * N.B. this assumes one view per model. Two views of the same model would each
 * fit it to their own container (a rare setup that isn't handled).
 *
 * Returns a cleanup function that detaches the observers.
 */
export function setupJscatterAutoHeight(
  el: HTMLElement,
  lmWidget: HTMLElement,
  model: WidgetModel
): () => void {
  autoSizedModels.add(model);
  let disposed = false;
  let frame = 0;
  const observer = new ResizeObserver(() => fitHeight());
  // The size change that ended while recalculating was skipped, so catch up
  const classObserver = new MutationObserver(() => fitHeight());

  // The element jupyter-scatter sizes: the regl canvas sits in a wrapper, which
  // sits in this container. N.B. the container is taller than the `height`
  // trait by the axes' padding.
  const findPlotContainer = () =>
    lmWidget.querySelector('canvas')?.parentElement?.parentElement ?? null;

  function fitHeight(): void {
    // While the output recalculates, Shiny's busy indicator briefly changes
    // the output's size. Following that would re-layout a plot that's about to
    // be replaced, which makes it likelier that jupyter-scatter's queued resize
    // runs after the view is destroyed (it throws "The instance was already
    // destroyed"). This only reduces the odds of that race; it can't rule it out.
    if (el.classList.contains('recalculating')) return;
    const plot = findPlotContainer();
    if (!plot) return;
    const padding = plot.offsetHeight - model.get('height');
    const height = Math.floor(el.clientHeight - padding);
    if (height < 1 || height === model.get('height')) return;
    model.set('height', height);
    model.save_changes();
  }

  // jupyter-scatter creates its plot (and starts listening for `height`
  // changes) on the next animation frame after rendering
  const start = () => {
    if (disposed) return;
    const plot = findPlotContainer() as (HTMLElement & { api?: ScatterplotApi }) | null;
    if (!plot?.api) {
      frame = requestAnimationFrame(start);
      return;
    }
    plot.api.set({ height: 'auto' });
    // Observe the plot container too, for padding changes (e.g., toggling axes)
    observer.observe(el);
    observer.observe(plot);
    classObserver.observe(el, { attributes: true, attributeFilter: ['class'] });
  };
  start();

  return () => {
    disposed = true;
    cancelAnimationFrame(frame);
    observer.disconnect();
    classObserver.disconnect();
  };
}
