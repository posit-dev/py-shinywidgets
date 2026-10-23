import type { WidgetModel } from '@jupyter-widgets/base';

/**
 * ipympl canvases render at the matplotlib figure's fixed pixel size and have
 * no built-in "fit to container" behavior (the `resizable` trait only enables
 * a manual drag handle). To make render_matplotlib() outputs actually fill a
 * fillable container, observe the output container's size and drive the figure
 * size through the model's resize() method, which immediately resizes the
 * canvas elements and sends a (throttled) resize message to the kernel, which
 * redraws the figure at the new size.
 *
 * Returns a cleanup function that detaches the observer.
 */
export function setupMplAutoResize(
  el: HTMLElement,
  lmWidget: HTMLElement,
  model: WidgetModel
): () => void {
  // N.B. the standard opt-out for fill/resize is the same as every other
  // widget (@render_matplotlib(fill=False), output_widget(fillable=False),
  // or an explicit height) -- this function only runs when the output is in
  // a fill container. This check is just a courtesy for the rare case where
  // the user constructs the ipympl Canvas themselves with resizable=False
  // and returns it directly (a plain Figure's canvas is a FigureCanvasAgg,
  // so setting `resizable` there wouldn't reach the widget model anyway).
  if (model.get('resizable') === false) {
    return () => {};
  }

  let lastWidth = -1;
  let lastHeight = -1;

  // The widget's header ("Figure 1") and footer (the cursor readout), and the
  // canvas's own margins, take up vertical space that isn't available to the
  // figure itself
  const header = lmWidget.querySelector('.jupyter-matplotlib-header') as HTMLElement | null;
  const footer = lmWidget.querySelector('.jupyter-matplotlib-footer') as HTMLElement | null;
  const canvasDiv = lmWidget.querySelector('.jupyter-matplotlib-canvas-div') as HTMLElement | null;

  const resizeToFit = () => {
    let chrome = (header?.offsetHeight ?? 0) + (footer?.offsetHeight ?? 0);
    if (canvasDiv) {
      const style = getComputedStyle(canvasDiv);
      chrome += parseFloat(style.marginTop) + parseFloat(style.marginBottom);
    }
    const w = el.clientWidth;
    const h = el.clientHeight - chrome;
    if (w === lastWidth && h === lastHeight) return;
    lastWidth = w;
    lastHeight = h;
    // MPLCanvasModel.resize() (not part of the base WidgetModel interface).
    // ipympl's frontend resize() silently drops sizes <= 5px, which also
    // keeps a 0/negative h (e.g. a hidden output) from reaching the kernel,
    // where set_size_inches() would raise.
    (model as unknown as { resize: (w: number, h: number) => void }).resize(w, h);
  };

  const observer = new ResizeObserver(() => resizeToFit());
  // Observe the output container (not the widget) so the canvas's own size
  // changes don't create a feedback loop. Also observe the header and footer,
  // whose heights change after the first paint: the footer stays empty until
  // the pointer first moves over the figure, and either can be hidden later
  // (header_visible/footer_visible).
  observer.observe(el);
  if (header) observer.observe(header);
  if (footer) observer.observe(footer);
  resizeToFit();

  return () => observer.disconnect();
}
