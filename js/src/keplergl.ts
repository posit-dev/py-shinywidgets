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
  const syncHeight = () => {
    // A hidden output reports 0; keep the last size rather than collapsing
    const h = Math.round(el.clientHeight);
    if (h <= 0 || h === model.get('height')) return;
    model.set('height', h);
    model.save_changes();
  };

  // Observe the output container (not the widget) so the map's own size
  // changes don't create a feedback loop
  const observer = new ResizeObserver(syncHeight);
  observer.observe(el);
  syncHeight();

  return () => observer.disconnect();
}
