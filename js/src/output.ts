import { HTMLManager, requireLoader } from '@jupyter-widgets/html-manager';
import { ShinyComm } from './comm';
import { jsonParse } from './utils';
import type { ErrorsMessageValue } from 'rstudio-shiny/srcts/types/src/shiny/shinyapp';

/******************************************************************************
 * Define a custom HTMLManager for use with Shiny
 ******************************************************************************/

class OutputManager extends HTMLManager {
  // In a soon-to-be-released version of @jupyter-widgets/html-manager,
  // display_view()'s first "dummy" argument will be removed... this shim simply
  // makes it so that our manager can work with either version
  // https://github.com/jupyter-widgets/ipywidgets/commit/159bbe4#diff-45c126b24c3c43d2cee5313364805c025e911c4721d45ff8a68356a215bfb6c8R42-R43
  async display_view(view: any, options: { el: HTMLElement; }): Promise<any> {
    const n_args = super.display_view.length
    if (n_args === 3) {
      return super.display_view({}, view, options)
    } else {
      // @ts-ignore
      return super.display_view(view, options)
    }
  }
}

const manager = new OutputManager({ loader: requireLoader });


/******************************************************************************
* Define the Shiny binding
******************************************************************************/

// Ideally we'd extend Shiny's HTMLOutputBinding, but the implementation isn't exported
class IPyWidgetOutput extends Shiny.OutputBinding {
  find(scope: HTMLElement): JQuery<HTMLElement> {
    return $(scope).find(".shiny-ipywidget-output");
  }
  onValueError(el: HTMLElement, err: ErrorsMessageValue): void {
    Shiny.unbindAll(el);
    this.renderError(el, err);
  }
  renderValue(el: HTMLElement, data): void {
    // TODO: allow for null value
    const model = manager.get_model(data.model_id);
    if (!model) {
      throw new Error(`No model found for id ${data.model_id}`);
    }
    model.then((m) => {
      const view = manager.create_view(m, {});
      view.then(v => {
        manager.display_view(v, {el: el}).then(() => {
          // TODO: This is not an ideal way to handle the case where another render
          // is requested before the last one is finished displaying the view, but
          // it's probably the least unobtrusive way to handle this for now
          // 
          while (el.childNodes.length > 1) {
            el.removeChild(el.childNodes[0]);
          }
        })
      });
    });
  }
}

Shiny.outputBindings.register(new IPyWidgetOutput(), "shiny.IPyWidgetOutput");

// By the time this code executes (i.e., by the time the `callback` in
// `require(["@jupyter-widgets/html-manager"], callback)` executes, it seems to be too
// late to register the output binding in a way that it'll "just work" for dynamic UI.
// Moreover, when this code executes, dynamic UI when yet be loaded, so schedule
// a bind to happen on the next tick.
// TODO: this is a hack. Could we do something better?
setTimeout(() => { Shiny.bindAll(document.body); }, 0);


/******************************************************************************
* Handle messages from the server-side Widget
******************************************************************************/

// Initialize the comm and model when a new widget is created
// This is basically our version of https://github.com/jupyterlab/jupyterlab/blob/d33de15/packages/services/src/kernel/default.ts#L1144-L1176
Shiny.addCustomMessageHandler("ipyshiny_comm_open", (msg_txt) => {
  setBaseURL();
  const msg = jsonParse(msg_txt);
  Shiny.renderDependencies(msg.content.html_deps);
  const comm = new ShinyComm(msg.content.comm_id);
  manager.handle_comm_open(comm, msg);
});

// Handle any mutation of the model (e.g., add a marker to a map, without a full redraw)
// Basically out version of https://github.com/jupyterlab/jupyterlab/blob/d33de15/packages/services/src/kernel/default.ts#L1200-L1215
Shiny.addCustomMessageHandler("ipyshiny_comm_msg", (msg_txt) => {
  const msg = jsonParse(msg_txt);
  manager.get_model(msg.content.comm_id).then(m => {
    // @ts-ignore for some reason IClassicComm doesn't have this method, but we do
    m.comm.handle_msg(msg);
  });
});

// TODO: test that this actually works
Shiny.addCustomMessageHandler("ipyshiny_comm_close", (msg_txt) => {
  const msg = jsonParse(msg_txt);
  manager.get_model(msg.content.comm_id).then(m => {
    // @ts-ignore for some reason IClassicComm doesn't have this method, but we do
    m.comm.handle_close(msg)
  });
});


// Our version of https://github.com/jupyter-widgets/widget-cookiecutter/blob/9694718/%7B%7Bcookiecutter.github_project_name%7D%7D/js/lib/extension.js#L8
function setBaseURL(x: string = '') {
  const base_url = document.querySelector('body').getAttribute('data-base-url');
  if (!base_url) {
    document.querySelector('body').setAttribute('data-base-url', x);
  }
}
