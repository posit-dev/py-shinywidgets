import type { DOMWidgetView, WidgetModel } from '@jupyter-widgets/base';
import { Throttler } from './utils';

/**
 * ipyvolume figures render their WebGL canvas at the fixed pixel size of the
 * model's `width`/`height` traits and have no built-in "fit to container"
 * behavior (outside the figure's own fullscreen mode). To make
 * render_ipyvolume() outputs actually fill a fillable container (or respect
 * an explicit output/widget height), observe the output container's size and
 * drive the canvas size through those traits -- the figure view re-renders at
 * the new size on `change:width`/`change:height`, and save_changes() syncs
 * the size back to Python (the same place ipympl's resize message puts it).
 *
 * `enabled`, when given, is consulted at resize time (not setup time):
 * styles it depends on (e.g., a Layout height on the widget) may only be
 * applied after setup runs.
 *
 * Returns a cleanup function that detaches the observer.
 */
export function setupIpyvolumeAutoResize(
  el: HTMLElement,
  view: DOMWidgetView,
  model: WidgetModel,
  enabled?: () => boolean
): () => void {
  let lastWidth = -1;
  let lastHeight = -1;
  let disposed = false;
  const throttler = new Throttler(100);

  const resizeToFit = () => {
    throttler.throttle(() => {
      if (disposed) return;
      if (enabled && !enabled()) return;
      // The figure's toolbar (the first child of the view's element, above
      // .ipyvolume-canvas-container) takes up vertical space that isn't
      // available to the canvas
      const toolbar = view.el.firstElementChild as HTMLElement | null;
      const chrome = toolbar?.offsetHeight ?? 0;
      const viewEl = view.el as HTMLElement;
      // A Layout(width=/height=) on the widget lands as an inline style on
      // the view, which is then smaller than the output (an output_widget()
      // stays a fill item even when the widget disables filling). Measure
      // the explicitly sized view in that case; otherwise the output
      // supplies the size.
      const w = viewEl.style.width ? viewEl.clientWidth : el.clientWidth;
      const h = (viewEl.style.height ? viewEl.clientHeight : el.clientHeight) - chrome;
      // A hidden (or not-yet-laid-out) output has no size to match
      if (w < 5 || h < 5) return;
      if (w === lastWidth && h === lastHeight) return;
      lastWidth = w;
      lastHeight = h;
      model.set('width', w);
      model.set('height', h);
      model.save_changes();
      // The toolbar's height can still be settling when a container resize
      // fires (e.g., the transition out of a card's fullscreen mode), and no
      // further event corrects a measurement taken mid-transition --
      // re-measure once after such transitions have finished
      setTimeout(resizeToFit, 350);
    });
  };

  // Observe the output container (not the widget) so the canvas's own size
  // changes don't create a feedback loop
  const observer = new ResizeObserver(resizeToFit);
  observer.observe(el);
  // A Layout(height=...) on the widget arrives after setup (it's applied by
  // the widget's own LayoutView); watch for it so fixed-size outputs get
  // their resize even when it shows up late
  const styleObserver = new MutationObserver(resizeToFit);
  styleObserver.observe(view.el, { attributes: true, attributeFilter: ['style'] });
  // A Layout size in viewport units (e.g., Layout(height="50vh")) can resize
  // the view without changing its inline style or the output's size, which
  // neither observer above catches, so watch the view's geometry too. When
  // the view has no explicit Layout size it just tracks the canvas, and
  // resizeToFit() measures the output (guarded by its size cache) in that
  // case, so this can't feed back.
  const viewObserver = new ResizeObserver(resizeToFit);
  viewObserver.observe(view.el);
  resizeToFit();

  return () => {
    disposed = true;
    observer.disconnect();
    styleObserver.disconnect();
    viewObserver.disconnect();
  };
}
