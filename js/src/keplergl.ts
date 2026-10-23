import type { WidgetModel } from '@jupyter-widgets/base';

/**
 * kepler.gl sizes its map from the model's pixel `height` trait (default
 * 400) rather than from its container, so neither a filling layout nor an
 * explicit `output_widget(height=)` has any effect on its own. Drive the
 * trait from the output container's height instead (the map already tracks
 * its container's width).
 *
 * Returns a cleanup function that detaches the observer.
 */
export function setupKeplerAutoHeight(
  el: HTMLElement,
  model: WidgetModel
): () => void {
  const containerHeight = () => Math.round(el.clientHeight);

  const syncHeight = () => {
    // A hidden output reports 0; keep the last size rather than collapsing
    const h = containerHeight();
    if (h <= 0 || h === model.get('height')) return;
    model.set('height', h);
    model.save_changes();
  };

  // Observe the output container (not the widget) so the map's own size
  // changes don't create a feedback loop
  const observer = new ResizeObserver(syncHeight);
  observer.observe(el);
  syncHeight();

  // kepler.gl's React app reads `height` once when it mounts and only later
  // subscribes to `change:height` (in a useEffect), so a syncHeight() that
  // lands in between is silently dropped, leaving the map stuck at the
  // default 400px. Re-assert the height until the rendered map reflects it
  // (kepler.gl's listener re-reads the trait, so a manual trigger suffices
  // when the value itself hasn't changed).
  const reassert = setInterval(() => {
    const h = containerHeight();
    const kepler = el.querySelector('.kepler-gl') as HTMLElement | null;
    if (!kepler || h <= 0) return;
    if (Math.abs(kepler.getBoundingClientRect().height - h) <= 1) {
      stopReassert();
      return;
    }
    if (model.get('height') === h) {
      model.trigger('change:height');
    } else {
      syncHeight();
    }
  }, 250);
  const stopReassert = () => clearInterval(reassert);
  // Give up eventually (e.g. the map never renders); the ResizeObserver
  // above still tracks container resizes.
  const giveUp = setTimeout(stopReassert, 30000);

  return () => {
    observer.disconnect();
    clearInterval(reassert);
    clearTimeout(giveUp);
  };
}
