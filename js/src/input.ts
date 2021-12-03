import { HTMLManager, requireLoader } from '@jupyter-widgets/html-manager';
// N.B. for this to work properly, it seems we must include
// https://unpkg.com/@jupyter-widgets/html-manager@*/dist/libembed-amd.js
// on the page first, which is why that comes in as a
import { renderWidgets } from '@jupyter-widgets/html-manager/lib/libembed';

// Let the world know about a change in the input value of this widget
// so that we can subscribe to it in the binding.
class InputManager extends HTMLManager {
  display_view(msg, view, options): ReturnType<typeof HTMLManager.prototype.display_view> {
    console.log("Display view", view);
    const evt = jQuery.Event('IPyWidgetInputValueChange');
    view.model.on('change:value', () => {
      console.log("change!!!");
      view.$el.trigger(evt);
    });
    return super.display_view(msg, view, options)
  }
}

// Each widget has multiple "models", and each model has a state.
// For an input widget, it seems reasonable to assume there is only one model
// state that contains the value, so we search the collection of model
// states for one with a value property, and return that (otherwise, error)
function getValue(states: object): any {
  const vals = [];
  Object.entries(states).forEach(([key, st]) => {
    // @ts-ignore: I don't think ipywidgets provides types for this
    if (st.hasOwnProperty('value')) vals.push(st.value);
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

window.addEventListener("load", () => {
  renderWidgets(() => new InputManager({ loader: requireLoader }));
});

class IPyWidgetInput extends window.Shiny.InputBinding {
  find(scope: HTMLElement): JQuery<HTMLElement> {
    return $(scope).find(".shiny-ipywidget-input");
  }
  getValue(el: HTMLElement): any {
    return getValue(getStates(el));
  }
  setValue(el: HTMLElement, value: any): void {
    let states = getStates(el);
    Object.entries(states).forEach(([key, st]) => {
      if (st.hasOwnProperty('value')) {
        states[key].value = value;
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
    // TODO: get this working!
    $(el).on("IPyWidgetInputValueChange", function () {
      console.log("change??????");
      callback(true);
    });
  }
  unsubscribe(el: HTMLElement): void {
    $(el).off("IPyWidgetInputValueChange");
  }
  // TODO: implement receiveMessage
}

window.Shiny.inputBindings.register(new IPyWidgetInput(), "shiny.IPyWidgetInput");
