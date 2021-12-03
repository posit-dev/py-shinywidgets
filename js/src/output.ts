import { HTMLManager, requireLoader } from '@jupyter-widgets/html-manager';
// N.B. for this to work properly, it seems we must include
// https://unpkg.com/@jupyter-widgets/html-manager@*/dist/libembed-amd.js
// on the page first, which is why that comes in as a
import { renderWidgets } from '@jupyter-widgets/html-manager/lib/libembed';

import type { renderContent } from 'rstudio-shiny/srcts/types/src/shiny/render';
import type { ErrorsMessageValue } from 'rstudio-shiny/srcts/types/src/shiny/shinyapp';

//if (window.require) {
//  console.log("require")
//  // @ts-ignore: this is a dynamic import
//  window.require.config({
//    paths: {
//      '@jupyter-widgets/base': 'https://unpkg.com/@jupyter-widgets/base@4.0.0/lib/index.js'
//    }
//  });
//}

// Whenever the ipywidget's state changes, let Shiny know about it
class OutputManager extends HTMLManager {
  display_view(msg, view, options): ReturnType<typeof HTMLManager.prototype.display_view> {
    return super.display_view(msg, view, options).then((view) => {
      const id = view.$el.parents(OUTPUT_SELECTOR).attr('id');
      _sendInputVal(id, view.model);
      view.model.on('change', (x) => _sendInputVal(id, x.model)); // TODO: verify this actually works
    });
  }
}

function _sendInputVal(id, model) {
  const attrs = Object.assign({}, model.attributes);
  const val = model.serialize(attrs);
  Shiny.setInputValue(id, val);
}

// Ideally we'd extend HTMLOutputBinding, but the implementation isn't exported
class IPyWidgetOutput extends Shiny.OutputBinding {
  find(scope: HTMLElement): JQuery<HTMLElement> {
    return $(scope).find(OUTPUT_SELECTOR);
  }
  onValueError(el: HTMLElement, err: ErrorsMessageValue): void {
    Shiny.unbindAll(el);
    this.renderError(el, err);
  }
  renderValue(el: HTMLElement, data: Parameters<typeof renderContent>[1]): void {
    Shiny.renderContent(el, data);
    renderWidgets(() => new OutputManager({ loader: requireLoader }), el);
  }
}

Shiny.outputBindings.register(new IPyWidgetOutput(), "shiny.IPyWidgetOutput");

const OUTPUT_SELECTOR = ".shiny-ipywidget-output";