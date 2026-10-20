import { DOMWidgetView, type WidgetModel, type WidgetView } from '@jupyter-widgets/base';

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

  const resizeToFit = () => {
    // The widget's header ("Figure 1") and footer take up vertical space that
    // isn't available to the figure itself
    const header = lmWidget.querySelector('.jupyter-matplotlib-header') as HTMLElement | null;
    const footer = lmWidget.querySelector('.jupyter-matplotlib-footer') as HTMLElement | null;
    const chrome = (header?.offsetHeight ?? 0) + (footer?.offsetHeight ?? 0);
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
  // changes don't create a feedback loop
  observer.observe(el);
  resizeToFit();

  return () => observer.disconnect();
}

export function mplCanvasViewClass(ViewType: typeof WidgetView): typeof WidgetView {
  const CanvasView = ViewType as MplCanvasViewConstructor;
  return class extends CanvasView {
    private _removed = false;

    // ipympl binds these handlers with model.on(), retaining removed views of
    // a cached canvas. listenTo() preserves their behavior and lets base view
    // disposal release them.
    model_events(): void {
      this.listenTo(this.model, {
        'change:header_visible': this._update_header_visible,
        'change:footer_visible': this._update_footer_visible,
        'change:toolbar_visible': this._update_toolbar_visible,
        'change:toolbar_position': this._update_toolbar_position,
        'change:_figure_label': this._update_figure_label,
        'change:_message': this._update_message,
        'change:_cursor': this._update_cursor,
      });
    }

    remove(): this {
      if (this._removed) return this;
      this._removed = true;
      // ipympl removes its window listeners but omits the base implementation.
      // Lumino disposal can initiate or reenter removal, so guard the whole
      // operation independently of Lumino's disposed state.
      try {
        super.remove();
      } finally {
        DOMWidgetView.prototype.remove.call(this);
      }
      return this;
    }
  };
}

interface MplCanvasView extends DOMWidgetView {
  _update_header_visible(): void;
  _update_footer_visible(): void;
  _update_toolbar_visible(): void;
  _update_toolbar_position(): void;
  _update_figure_label(): void;
  _update_message(): void;
  _update_cursor(): void;
}

type MplCanvasViewConstructor = Omit<typeof WidgetView, 'prototype'> & {
  new (...args: ConstructorParameters<typeof WidgetView>): MplCanvasView;
  prototype: MplCanvasView;
};
