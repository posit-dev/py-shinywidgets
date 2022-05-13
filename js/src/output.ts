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

// Define our own custom module loader for Shiny
const shinyRequireLoader = async function(moduleName: string, moduleVersion: string): Promise<any> {

  // shiny provides require.js and also sets `define.amd=false` to prevent <script>s
  // with UMD loaders from triggering anonymous define() errors. ipyshiny should
  // generally be able to avoid anonymous define errors though since there should only
  // be one 'main' anonymous define() for the widget's module (located in a JS file that
  // we've already require.config({paths: {...}})ed; and in that case, requirejs adds a
  // data-requiremodule attribute to the <script> tag that shiny's custom define will
  // recognize and use as the name).)
  const oldAmd = (window as any).define.amd;

  // The is the original value for define.amd that require.js sets
  (window as any).define.amd = {jQuery: true};

  // Store jQuery global since loading we load a module, it may overwrite it
  // (qgrid is one good example)
  const old$ = (window as any).$;
  const oldJQ = (window as any).jQuery;

  if (moduleName === 'qgrid') {
    // qgrid wants to use base/js/dialog (if it's available) for full-screen tables
    // https://github.com/quantopian/qgrid/blob/877b420/js/src/qgrid.widget.js#L11-L16
    // Maybe that's worth supporting someday, but for now, we define it to be nothing
    // to avoid require('qgrid') from producing an error
    (window as any).define("base/js/dialog", [], function() { return null });
  }

  return requireLoader(moduleName, moduleVersion).finally(() => {
    (window as any).define.amd = oldAmd;
    (window as any).$ = old$;
    (window as any).jQuery = oldJQ;
  });
}

const manager = new OutputManager({ loader: shinyRequireLoader });


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

    // Allow for a None/null value to hide the widget (css inspired by htmlwidgets)
    if (!data) {
      el.style.visibility = "hidden";
      return;
    } else {
      el.style.visibility = "inherit";
    }

    // At this time point, we should've already handled an 'open' message, and so
    // the model should be ready to use
    const model = manager.get_model(data.model_id);
    if (!model) {
      throw new Error(`No model found for id ${data.model_id}`);
    }

    model.then((m) => {
      const view = manager.create_view(m, {});
      view.then(v => {
        manager.display_view(v, {el: el}).then(() => {
          // TODO: It would be better to .close() the widget here, but
          // I'm not sure how to do that yet (at least client-side)
          while (el.childNodes.length > 1) {
            el.removeChild(el.childNodes[0]);
          }
        })
      });
    }); 
  }
}

Shiny.outputBindings.register(new IPyWidgetOutput(), "shiny.IPyWidgetOutput");

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
