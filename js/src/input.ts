import { HTMLManager, requireLoader } from '@jupyter-widgets/html-manager';
// N.B. for this to work properly, it seems we must include
// https://unpkg.com/@jupyter-widgets/html-manager@*/dist/libembed-amd.js
// on the page first, which is why that comes in as a
import { renderWidgets } from '@jupyter-widgets/html-manager/lib/libembed';
import { RatePolicyModes } from 'rstudio-shiny/srcts/types/src/inputPolicies/inputRateDecorator';


// Render the widgets on page load, so that once the Shiny app initializes,
// it has a chance to bind to the rendered widgets.
window.addEventListener("load", () => {
  renderWidgets(() => new InputManager({ loader: requireLoader }));
});


// Let the world know about a value change so the Shiny input binding 
// can subscribe to it (and thus call getValue() whenever that happens)
class InputManager extends HTMLManager {
  display_view(msg, view, options): ReturnType<typeof HTMLManager.prototype.display_view> {

    return super.display_view(msg, view, options).then((view) => {

      // Get the Shiny input container element for this view
      const $el_input = view.$el.parents(INPUT_SELECTOR);

      // At least currently, ipywidgets have a tagify method, meaning they can 
      // be directly statically rendered (i.e., without a input_ipywidget() container)
      if ($el_input.length == 0) {
        return;
      }

      // Some widgets (e.g., RadioButtons) represent their "current value" using the
      // index (rather than the value) property.
      let val = view.model.get("value");
      if (val === undefined) {
        val = view.model.get("index");
      }
      // Checkbox() apparently doesn't have a value/index property
      // on the model on the initial render (but does in the change event???)
      if (val === undefined && view.hasOwnProperty("checkbox")) {
        val = view.checkbox.checked;
      }

      // Mock a change event now so that we know Shiny binging has a chance to
      // read it. The reason this is done on the next tick is because the
      // binding hasn't had a chance to subscribe to the change event yet.
      setTimeout(() => _doChangeEvent($el_input[0], val), 0);

      // Relay changes to the model to the Shiny input binding 
      view.model.on('change', (x) => {
        let val;
        if (x.changed.hasOwnProperty("value")) {
          val = x.changed.value;
        } else if (x.changed.hasOwnProperty("index")) {
          val = x.changed.index;
        } else {
          throw new Error("Unknown change event" +  JSON.stringify(x.changed));
        }
        _doChangeEvent($el_input[0], val);
      });

    });

  }
}

function _doChangeEvent(el: HTMLElement, val: any): void {
  const evt = new CustomEvent(CHANGE_EVENT_NAME, { detail: val });
  el.dispatchEvent(evt);
}

class IPyWidgetInput extends Shiny.InputBinding {
  find(scope: HTMLElement): JQuery<HTMLElement> {
    return $(scope).find(INPUT_SELECTOR);
  }
  getValue(el: HTMLElement): any {
    return $(el).data("value");
  }
  setValue(el: HTMLElement, value: any): void {
    $(el).data("value", value);
  }
  subscribe(el: HTMLElement, callback: (x: boolean) => void): void {
    this._eventListener = (e: CustomEvent) => {
      this.setValue(el, e.detail);
      callback(true);
    };
    el.addEventListener(CHANGE_EVENT_NAME, this._eventListener);
  }
  _eventListener;
  unsubscribe(el: HTMLElement): void {
    el.removeEventListener(CHANGE_EVENT_NAME, this._eventListener);  
  }
  getRatePolicy(el: HTMLElement): { policy: RatePolicyModes; delay: number } {
    const policy = el.attributes.getNamedItem('data-rate-policy');
    const delay = el.attributes.getNamedItem('data-rate-delay');
    return {
      // @ts-ignore: python typing ensures this is a valid policy
      policy: policy ? policy.value : 'debounce',
      delay: delay ? parseInt(delay.value) : 250
    }
  }
  // TODO: implement receiveMessage?
}

Shiny.inputBindings.register(new IPyWidgetInput(), "shiny.IPyWidgetInput");


const INPUT_SELECTOR = ".shiny-ipywidget-input";
const CHANGE_EVENT_NAME = 'IPyWidgetInputValueChange'




// // Each widget has multiple "models", and each model has a state.
// // For an input widget, it seems reasonable to assume there is only one model
// // state that contains the value/index, so we search the collection of model
// // states for one with a value property, and return that (otherwise, error)
// function _getValue(states: object): any {
//   const vals = [];
//   Object.entries(states).forEach(([key, val]) => {
//     if (val.state.hasOwnProperty('value')) {
//       vals.push(val.state.value);
//     } else if (val.state.hasOwnProperty('index')) {
//       vals.push(val.state.index);
//     }
//   });
//   if (vals.length > 1) {
//     throw new Error("Expected there to be exactly one model state with a value property, but found: " + vals.length);
//   }
//   return vals[0];
// }
// 
// function _getStates(el: HTMLElement): object {
//   const el_state = el.querySelector('script[type="application/vnd.jupyter.widget-state+json"]');
//   return JSON.parse(el_state.textContent).state;
// }

// function set_state(el) {
//   let states = _getStates(el);
//   Object.entries(states).forEach(([key, val]) => {
//     if (val.state && val.state.hasOwnProperty('value')) {
//       states[key].state.value = value;
//     }
//   });
//   let el_state = el.querySelector(WIDGET_STATE_SELECTOR);
//   el_state.textContent = JSON.stringify(states);
//   // Re-render the widget with the new state
//   // Unfortunately renderWidgets() doesn't clear out the div.widget-subarea,
//   // so repeated calls to renderWidgets() will render multiple views
//   el.querySelector('.widget-subarea').remove();
//   renderWidgets(() => new InputManager({ loader: requireLoader }), el);
// }