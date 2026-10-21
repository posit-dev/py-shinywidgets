import type { DOMWidgetView } from '@jupyter-widgets/base';

/**
 * Size nglview's stage to the output container, tracking it as it resizes.
 * Observes the output rather than the widget so the stage's own size changes
 * don't create a feedback loop.
 *
 * Returns a cleanup function that detaches the observer.
 */
export function setupNglviewAutoSize(el: HTMLElement, view: DOMWidgetView): () => void {
  // nglview's view (not its model) exposes setSize(), which resizes the stage
  const stage = view as unknown as { setSize(width: string, height: string): void };
  const observer = new ResizeObserver(() => {
    stage.setSize(`${el.clientWidth}px`, `${el.clientHeight}px`);
  });
  observer.observe(el);
  return () => observer.disconnect();
}
