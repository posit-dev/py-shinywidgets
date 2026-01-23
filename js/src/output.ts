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

  // shiny provides a shim of require.js which allows <script>s with anonymous
  // define()s to be loaded without error. When an anonymous define() occurs,
  // the shim uses the data-requiremodule attribute (set by require.js) on the script
  // to determine the module name.
  // https://github.com/posit-dev/py-shiny/blob/230940c/scripts/define-shims.js#L10-L16
  // In the context of shinywidgets, when a widget gets rendered, it should
  // come with another <script> tag that does `require.config({paths: {...}})`
  // which maps the module name to a URL of the widget's JS file.
  const oldAmd = (window as any).define.amd;

  // This is probably not necessary, but just in case -- especially now in a
  // anywidget/ES6 world, we probably don't want to load AMD modules
  // (plotly is one example of a widget that will fail to load if AMD is enabled)
  (window as any).define.amd = false;

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
    // N.B. It's probably better to get view(s) from m.views and .remove() them,
    // but empirically, this seems to work better
    while (el.childNodes.length > 1) {
      el.removeChild(el.childNodes[0]);
    }

    // The ipywidgets container (.lmWidget)
    const lmWidget = el.children[0] as HTMLElement;

    if (fill) {
      this._onImplementation(lmWidget, () => this._doAddFillClasses(lmWidget));
    }
    this._onImplementation(lmWidget, this._doResize);
  }
  _onImplementation(lmWidget: HTMLElement, callback: () => void): void {
    if (this._hasImplementation(lmWidget)) {
      callback();
      return;
    }

    // Some widget implementation (e.g., ipyleaflet, pydeck) won't actually
    // have rendered to the DOM at this point, so wait until they do
    const mo = new MutationObserver((mutations) => {
      if (this._hasImplementation(lmWidget)) {
        mo.disconnect();
        callback();
      }
    });

    mo.observe(lmWidget, {childList: true});
  }
  // In most cases, we can get widgets to fill through Python/CSS, but some widgets
  // (e.g., quak) don't have a Python API and use shadow DOM, which can only access
  // from JS
  _doAddFillClasses(lmWidget: HTMLElement): void {
    const impl = lmWidget.children[0];
    const isQuakWidget = impl && !!impl.shadowRoot?.querySelector(".quak");
    if (isQuakWidget) {
      impl.classList.add("html-fill-container", "html-fill-item");
      const quakWidget = impl.shadowRoot.querySelector(".quak") as HTMLElement;
      quakWidget.style.maxHeight = "unset";
    }
  }
  _doResize(): void {
    // Trigger resize event to force layout (setTimeout() is needed for altair)
    // TODO: debounce this call?
    setTimeout(() => {
      window.dispatchEvent(new Event('resize'))
    }, 0);
  }
  _hasImplementation(lmWidget: HTMLElement): boolean {
    const impl = lmWidget.children[0];
    return impl && (impl.children.length > 0 || impl.shadowRoot?.children.length > 0);
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
Shiny.addCustomMessageHandler("shinywidgets_comm_msg", async (msg_txt) => {
  const msg = jsonParse(msg_txt);
  const id = msg.content.comm_id;
  const model = manager.get_model(id);
  if (!model) {
    console.error(`Couldn't handle message for model ${id} because it doesn't exist.`);
    return;
  }
  try {
    const m = await model;
    // @ts-ignore for some reason IClassicComm doesn't have this method, but we do
    m.comm.handle_msg(msg);
  } catch (err) {
    console.error("Error handling message:", err);
  }
});


// Handle the closing of a widget/comm/model
Shiny.addCustomMessageHandler("shinywidgets_comm_close", async (msg_txt) => {
  const msg = jsonParse(msg_txt);
  const id = msg.content.comm_id;
  const model = manager.get_model(id);
  if (!model) {
    console.error(`Couldn't close model ${id} because it doesn't exist.`);
    return;
  }

  try {
    const m = await model;

    // Before .close()ing the model (which will .remove() each view), do some
    // additional cleanup that .remove() might miss
    if (m.views) {
      await Promise.all(
        Object.values(m.views).map(async (viewPromise) => {
        try {
          const v = await viewPromise;

          // Old versions of plotly need a .destroy() to properly clean up
          // https://github.com/plotly/plotly.py/pull/3805/files#diff-259c92d
          if (hasMethod<DestroyMethod>(v, 'destroy')) {
            v.destroy();
            // Also, empirically, when this destroy() is relevant, it also helps to
            // delete the view's reference to the model, I think this is the only
            // way to drop the resize event listener (see the diff in the link above)
            // https://github.com/posit-dev/py-shinywidgets/issues/166
            delete v.model;
            // Ensure sure the lm-Widget container is also removed
            v.remove();
          }


        } catch (err) {
          console.error("Error cleaning up view:", err);
        }
      })
    );
    }

    // Prevent sync errors during close. When m.close() removes views, they try to
    // sync _view_count back to the server. But m.close() deletes the comm before
    // removing views, causing "Syncing error: no comm channel defined".
    // Setting comm_live=false prevents save_changes() from attempting to sync.
    // This is particularly important for anywidget-based widgets (like plotly 6.x)
    // that don't have a destroy() method and thus aren't handled in the loop above.
    m.comm_live = false;

    // Close model after all views are cleaned up.
    // Wrap in try-catch because close() may trigger events that access already-cleaned state.
    try {
      await m.close();
    } catch (closeErr) {
      // Ignore errors during close - the model state may already be partially cleaned up
    }

    // Trigger comm:close event to remove manager's reference.
    // This may throw if the manager tries to access model state that's been cleaned up,
    // but that's acceptable since the model is already closed.
    try {
      m.trigger("comm:close");
    } catch (triggerErr) {
      // Ignore errors during comm:close trigger - the model is already closed
    }
  } catch (err) {
    console.error("Error during model cleanup:", err);
  }
});

$(document).on("shiny:disconnected", () => {
  manager.clear_state();
});

// When in filling layout, some widgets (specifically, altair) incorrectly think their
// height is 0 after it's shown, hidden, then shown again. As a workaround, trigger a
// resize event when a tab is shown.
// TODO: This covers the 95% use case, but it's definitely not an ideal way to handle
// this situation. A more robust solution would use IntersectionObserver to detect when
// the widget becomes visible. Or better yet, we'd get altair to handle this situation
// better.
// https://github.com/posit-dev/py-shinywidgets/issues/172
document.addEventListener('shown.bs.tab', event => {
  window.dispatchEvent(new Event('resize'));
})

// Our version of https://github.com/jupyter-widgets/widget-cookiecutter/blob/9694718/%7B%7Bcookiecutter.github_project_name%7D%7D/js/lib/extension.js#L8
function setBaseURL(x: string = '') {
  const base_url = document.querySelector('body').getAttribute('data-base-url');
  if (!base_url) {
    document.querySelector('body').setAttribute('data-base-url', x);
  }
}

// TypeGuard to safely check if an object has a method
function hasMethod<T>(obj: any, methodName: keyof T): obj is T {
    return typeof obj[methodName] === 'function';
}

interface DestroyMethod {
    destroy(): void;
}
