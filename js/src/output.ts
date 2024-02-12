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
  // with UMD loaders from triggering anonymous define() errors. shinywidgets should
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
  async renderValue(el: HTMLElement, data): Promise<void> {

    // Allow for a None/null value to hide the widget (css inspired by htmlwidgets)
    if (!data) {
      el.style.visibility = "hidden";
      return;
    } else {
      el.style.visibility = "inherit";
    }

    // Only forward the potential to fill if `output_widget(fillable=True)`
    // _and_ the widget instance wants to fill
    const fill = data.fill && el.classList.contains("html-fill-container");
    if (fill) el.classList.add("forward-fill-potential");

    // At this time point, we should've already handled an 'open' message, and so
    // the model should be ready to use
    const model = await manager.get_model(data.model_id);
    if (!model) {
      throw new Error(`No model found for id ${data.model_id}`);
    }

    const view = await manager.create_view(model, {});
    await manager.display_view(view, {el: el});

    // Don't allow more than one .lmWidget container, which can happen
    // when the view is displayed more than once
    // TODO: It's probably better to get view(s) from m.views and .remove() them
    while (el.childNodes.length > 1) {
      el.removeChild(el.childNodes[0]);
    }

    // The ipywidgets container (.lmWidget)
    const lmWidget = el.children[0] as HTMLElement;

    this._maybeResize(lmWidget);
  }
  _maybeResize(lmWidget: HTMLElement): void {
    const impl = lmWidget.children[0];
    if (impl.children.length > 0) {
      return this._doResize(impl);
    }

    // Some widget implementation (e.g., ipyleaflet, pydeck) won't actually
    // have rendered to the DOM at this point, so wait until they do
    const mo = new MutationObserver((mutations) => {
      if (impl.children.length > 0) {
        mo.disconnect();
        this._doResize(impl);
      }
    });

    mo.observe(impl, {childList: true});
  }
  _doResize(impl: Element): void {
    // Trigger resize event to force layout (setTimeout() is needed for altair)
    // TODO: debounce this call?
    setTimeout(() => {
      window.dispatchEvent(new Event('resize'))
    }, 0);
  }
}

Shiny.outputBindings.register(new IPyWidgetOutput(), "shiny.IPyWidgetOutput");


// Due to the way HTMLManager (and widget implementations) get loaded (via
// require.js), the binding registration above can happen _after_ Shiny has
// already bound the DOM, especially in the dynamic UI case (i.e., output_binding()'s
// dependencies don't come in until after initial page load). And, in the dynamic UI
// case, UI is rendered asychronously via Shiny.shinyapp.taskQueue, so if it exists,
// we probably need to re-bind the DOM after the taskQueue is done.
const taskQueue = Shiny?.shinyapp?.taskQueue;
if (taskQueue) {
  taskQueue.enqueue(() => Shiny.bindAll(document.body));
}

/******************************************************************************
* Handle messages from the server-side Widget
******************************************************************************/

// Initialize the comm and model when a new widget is created
// This is basically our version of https://github.com/jupyterlab/jupyterlab/blob/d33de15/packages/services/src/kernel/default.ts#L1144-L1176
Shiny.addCustomMessageHandler("shinywidgets_comm_open", (msg_txt) => {
  setBaseURL();
  const msg = jsonParse(msg_txt);
  Shiny.renderDependencies(msg.content.html_deps);
  const comm = new ShinyComm(msg.content.comm_id);
  manager.handle_comm_open(comm, msg);
});

// Handle any mutation of the model (e.g., add a marker to a map, without a full redraw)
// Basically out version of https://github.com/jupyterlab/jupyterlab/blob/d33de15/packages/services/src/kernel/default.ts#L1200-L1215
Shiny.addCustomMessageHandler("shinywidgets_comm_msg", (msg_txt) => {
  const msg = jsonParse(msg_txt);
  manager.get_model(msg.content.comm_id).then(m => {
    // @ts-ignore for some reason IClassicComm doesn't have this method, but we do
    m.comm.handle_msg(msg);
  });
});

// TODO: test that this actually works
Shiny.addCustomMessageHandler("shinywidgets_comm_close", (msg_txt) => {
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
