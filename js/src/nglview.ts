import type { DOMWidgetView, WidgetModel } from '@jupyter-widgets/base';

// nglview's view (not its model) exposes setSize(), which resizes the stage
interface NglviewView {
  setSize(width: string, height: string): void;
  stage: { viewer: { container: HTMLElement } };
}

/**
 * Size nglview's stage to the output container, tracking it as it resizes.
 * Observes the output rather than the widget so the stage's own size changes
 * don't create a feedback loop. With `trackHeight = false` (for a widget with
 * a height of its own), only the width follows the output.
 *
 * Returns a cleanup function that detaches the observer.
 */
export function setupNglviewAutoSize(
  el: HTMLElement,
  view: DOMWidgetView,
  model: WidgetModel,
  trackHeight = true
): () => void {
  // Package-based dispatch also routes non-viewer nglview widgets here (e.g.
  // RepresentationControl, which renders as an ordinary ipywidgets Box).
  // Those views have no NGL stage or setSize(), so don't observe them.
  if (model.get('_view_name') !== 'NGLView') {
    return () => {};
  }
  const stage = view as unknown as NglviewView;
  const observer = new ResizeObserver(() => {
    // nglview stores an `NGLWidget(width=...)` argument on the synced
    // `_view_width` trait (default '') and sizes the stage to it, so an
    // explicit width opts out of tracking the output's width. Otherwise the
    // stage's own fixed pixel width would overflow or underfill the output.
    const width = model.get('_view_width') || `${el.clientWidth}px`;
    const height = trackHeight
      ? `${el.clientHeight}px`
      : stage.stage.viewer.container.style.height;
    stage.setSize(width, height);
  });
  observer.observe(el);
  return () => observer.disconnect();
}
