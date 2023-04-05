class Throttler {
  fnToCall: Function;
  wait: number;
  timeoutId: ReturnType<typeof setTimeout>;
  get isWaiting(): boolean {
    return this.timeoutId !== null;
  }
  constructor(wait: number = 100) {
    if (wait < 0) throw new Error("wait must be a positive number");
    this.wait = wait;
    this._reset();
  }
  _reset() {
    this.fnToCall = null;
    clearTimeout(this.timeoutId);
    this.timeoutId = null;
  }
  _setTimeout() {
    this.timeoutId = setTimeout(() => {
      if (this.fnToCall) {
        // console.log("Timeout!", Date.now());

        // Call the function
        this.fnToCall();
        this.fnToCall = null;
        // Restart the timeout as we just called the function
        // This call is the key step of Throttler
        this._setTimeout();
      } else {
        // console.log("Empty!", Date.now());

        // Nothing was done, so reset
        this._reset();
      }
    }, this.wait);
  }
  // Execute the function immediately and reset the timeout
  // This is useful when the timeout is waiting and we want to
  // execute the function immediately to not have events be out
  // of order
  flush() {
    // console.log("Flush!", Date.now());

    if (this.fnToCall) this.fnToCall();
    this._reset();
  }
  // Try to execute the function immediately, if it is not waiting
  // If it is waiting, update the function to be called
  throttle(fn: Function) {
    if (!this.isWaiting) {
      // console.log("Call!", Date.now());

      // If there is nothing waiting, call it immediately
      // and start the throttling
      fn();
      this._setTimeout();
    } else {
      // If the timeout is currently waiting, update the func to be called
      this.fnToCall = fn;
    }
  }

}

// This class is a striped down version of Comm from @jupyter-widgets/base
// https://github.com/jupyter-widgets/ipywidgets/blob/88cec8/packages/base/src/services-shim.ts#L192-L335
// Note that the Kernel.IComm implementation is located here
// https://github.com/jupyterlab/jupyterlab/blob/master/packages/services/src/kernel/comm.ts
export class ShinyComm {

  // It seems like we'll want one comm per model
  comm_id: string;
  constructor(model_id: string) {
    this.comm_id = model_id;
  }

  // This might not be needed
  get target_name(): string {
    return "jupyter.widgets";
  }

  _msg_callback;
  _close_callback;
  // Throttle mousemove events to every 100ms
  _mouse_move_throttler = new Throttler(100);

  send(
    data: any,
    callbacks: any,
    metadata?: any,
    buffers?: ArrayBuffer[] | ArrayBufferView[]
  ): string {
    const msg = {
      content: {comm_id: this.comm_id, data: data},
      metadata: metadata,
      buffers: buffers || [],
      // this doesn't seem relevant to the widget?
      header: {}
    };

    const msg_txt = JSON.stringify(msg);

    // Ex `data` value:
    // {"method": "custom","content": {    "event": "interaction",    "type": "mousemove",    "coordinates": [        -17.76259815404015,        12.096729340756617    ]}}
    if (
      data.method === "custom" &&
      data.content.event === "interaction" &&
      data.content.type === "mousemove"
    ) {
      // mousemove events only
      this._mouse_move_throttler.throttle(() => {
        Shiny.setInputValue("shinywidgets_comm_send", msg_txt, {priority: "event"});
      })
    } else {
      // Mouse over, mouse out, click, etc. (Anything other than `"mousemove"`)
      this._mouse_move_throttler.flush()
      Shiny.setInputValue("shinywidgets_comm_send", msg_txt, {priority: "event"});
    }


    // When client-side changes happen to the WidgetModel, this send method
    // won't get called for _every_  change (just the first one). The
    // expectation is that this method will eventually end up calling itself
    // (via callbacks) when the server is ready (i.e., idle) to receive more
    // updates. To make sense of this, see
    // https://github.com/jupyter-widgets/ipywidgets/blob/88cec8b/packages/base/src/widget.ts#L550-L557
    if (callbacks && callbacks.iopub && callbacks.iopub.status) {
      setTimeout(() => {
        // TODO-future: this doesn't seem quite right. Maybe listen to the shiny-busy flag?
        // const state = document.querySelector("html").classList.contains("shiny-busy") ? "busy" : "idle";
        const msg = {content: {execution_state: "idle"}};
        callbacks.iopub.status(msg);
      }, 0);
    }

    return this.comm_id;
  }

  open(
    data: any,
    callbacks: any,
    metadata?: any,
    buffers?: ArrayBuffer[] | ArrayBufferView[]
  ): string {
    // I don't think we need to do anything here?
    return this.comm_id;
  }

  close(
    data?: any,
    callbacks?: any,
    metadata?: any,
    buffers?: ArrayBuffer[] | ArrayBufferView[]
  ): string {
    // I don't think we need to do anything here?
    return this.comm_id;
  }

  on_msg(callback: (x: any) => void): void {
    this._msg_callback = callback.bind(this);
  }

  on_close(callback: (x: any) => void): void {
    this._close_callback = callback.bind(this);
  }

  handle_msg(msg: any) {
    if (this._msg_callback) this._msg_callback(msg);
  }

  handle_close(msg: any) {
    if (this._close_callback) this._close_callback(msg);
  }
}
