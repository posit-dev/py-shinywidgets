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

  send(
    data: any,
    callbacks: any, // TODO: to we need to call these?
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
    // A short-term solution to passing buffers (i.e. binary data)
    const msg_txt = JSON.stringify(msg);
    Shiny.setInputValue("ipyshiny_comm_send", msg_txt, {priority: "event"});
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
