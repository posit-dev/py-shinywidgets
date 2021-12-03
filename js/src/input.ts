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

const EVENT_NAME = 'IPyWidgetInputValueChange'

// Let the world know about a value change so the Shiny input binding 
// can subscribe to it (and thus call getValue() whenever that happens)
class InputManager extends HTMLManager {
  display_view(msg, view, options): ReturnType<typeof HTMLManager.prototype.display_view> {
    view.model.on('change:value', (x) => {
      const evt = jQuery.Event(EVENT_NAME, { value: x.attributes.value });
      $(document).trigger(evt);
    });
    return super.display_view(msg, view, options)
  }
}

class IPyWidgetInput extends window.Shiny.InputBinding {
  find(scope: HTMLElement): JQuery<HTMLElement> {
    return $(scope).find(".shiny-ipywidget-input");
  }
  // The JSON state payload doesn't get updated when the value changes
  // client side, so we manage that ourselves via the subscribe() method
  _clientValue = undefined;
  getValue(el: HTMLElement): any {
    return (this._clientValue === undefined) ? 
      getValue(getStates(el)) : 
      this._clientValue;
  }
  setValue(el: HTMLElement, value: any): void {
    let states = getStates(el);
    Object.entries(states).forEach(([key, val]) => {
      if (val.state && val.state.hasOwnProperty('value')) {
        states[key].state.value = value;
      }
    });
    let el_state = el.querySelector('script[type="application/vnd.jupyter.widget-state+json"]');
    el_state.textContent = JSON.stringify(states);
    // Re-render the widget with the new state
    // Unfortunately renderWidgets() doesn't clear out the div.widget-subarea,
    // so repeated calls to renderWidgets() will render multiple views
    el.querySelector('.widget-subarea').remove();
    renderWidgets(() => new InputManager({ loader: requireLoader }), el)
  }
  subscribe(el: HTMLElement, callback: (x: boolean) => void): void {
    let that = this;
    $(document).on(EVENT_NAME, function (x) {
      // @ts-ignore: TODO: provide a type for this event
      that._clientValue = x.value;
      callback(true);
    });
  }
  unsubscribe(el: HTMLElement): void {
    $(document).off(EVENT_NAME);
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
  // TODO: implement receiveMessage
}

window.Shiny.inputBindings.register(new IPyWidgetInput(), "shiny.IPyWidgetInput");


// Each widget has multiple "models", and each model has a state.
// For an input widget, it seems reasonable to assume there is only one model
// state that contains the value, so we search the collection of model
// states for one with a value property, and return that (otherwise, error)
function getValue(states: object): any {
  const vals = [];
  Object.entries(states).forEach(([key, val]) => {
    if (val.state && val.state.hasOwnProperty('value')) {
      vals.push(val.state.value);
    }
  });
  if (vals.length > 1) {
    console.error("Expected there to be exactly one model state with a value property, but found", vals.length);
  }
  return vals[0];
}

function getStates(el: HTMLElement): object {
  const el_state = el.querySelector('script[type="application/vnd.jupyter.widget-state+json"]');
  return JSON.parse(el_state.textContent).state;
}