import type { DOMWidgetView } from '@jupyter-widgets/base';

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
  trackHeight = true
): () => void {
  const stage = view as unknown as NglviewView;
  const observer = new ResizeObserver(() => {
    const height = trackHeight
      ? `${el.clientHeight}px`
      : stage.stage.viewer.container.style.height;
    stage.setSize(`${el.clientWidth}px`, height);
  });
  observer.observe(el);
  return () => observer.disconnect();
}
