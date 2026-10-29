import { base64EncodeBuffers, Throttler } from "./utils";

type CommMsgType = "comm_open" | "comm_msg" | "comm_close";

// Once Shiny disconnects there's nothing to send to; clear_state() then closes
// every model (and so every comm), which must not try.
let connected = true;

export function setConnected(value: boolean): void {
  connected = value;
}

const IDLE = {content: {execution_state: "idle"}};

const comms = new Map<string, ShinyComm>();

export function ack_comm(comm_id: string, msg_id: string): void {
  comms.get(comm_id)?.ack(msg_id);
}

// For comms Python closed, where the model closes without calling close().
export function dispose_comm(comm_id: string): void {
  comms.get(comm_id)?.dispose();
}

// This class is a striped down version of Comm from @jupyter-widgets/base
// https://github.com/jupyter-widgets/ipywidgets/blob/88cec8/packages/base/src/services-shim.ts#L192-L335
// Note that the Kernel.IComm implementation is located here
// https://github.com/jupyterlab/jupyterlab/blob/master/packages/services/src/kernel/comm.ts
export class ShinyComm {

  // It seems like we'll want one comm per model
  comm_id: string;
  throttler: Throttler;
  private msgCount = 0;
  private closed = false;
  // msg_id -> the model's status callback, for messages awaiting a server ack.
  private pending = new Map<string, (msg: any) => void>();
  constructor(model_id: string) {
    this.comm_id = model_id;
    comms.set(model_id, this);
    // TODO: make this configurable (see comments in send() below)?
    this.throttler = new Throttler(100);
  }

  // This might not be needed
  get target_name(): string {
    return "jupyter.widget";
  }

  _msg_callback;
  _close_callback;

  send(
    data: any,
    callbacks: any,
    metadata?: any,
    buffers?: ArrayBuffer[] | ArrayBufferView[]
  ): string {
    const [msg_id, msg_txt] = this._message("comm_msg", {data: data}, metadata, buffers);

    // Since ipyleaflet can send mousemove events very quickly when hovering over the map,
    // we throttle them to ensure that the server doesn't get overwhelmed. Said events
    // generate a payload that looks like this:
    // {"method": "custom", "content": {"event": "interaction", "type": "mousemove", "coordinates": [-17.76259815404015, 12.096729340756617]}}
    //
    // TODO: This is definitely not ideal. It would be better to have a way to specify/
    // customize throttle rates instead of having such a targetted fix for ipyleaflet.
    const is_mousemove =
      data.method === "custom" &&
      data.content.event === "interaction" &&
      data.content.type === "mousemove";

    // ipywidgets keeps one sync message in flight and buffers the rest until
    // the status callback reports idle (see
    // https://github.com/jupyter-widgets/ipywidgets/blob/88cec8b/packages/base/src/widget.ts#L550-L557).
    // The server acks each message after the flush that handled it, and ack()
    // reports idle then, so bursts coalesce under load as they do in Jupyter.
    const onIdle = callbacks?.iopub?.status;
    if (is_mousemove) {
      this.throttler.throttle(() => {
        Shiny.setInputValue("shinywidgets_comm_send", msg_txt, {priority: "event"});
      });
      // The throttler may drop this message, so it may never be acked.
      if (onIdle) setTimeout(() => onIdle(IDLE), 0);
    } else {
      this.throttler.flush();
      if (onIdle) this.pending.set(msg_id, onIdle);
      Shiny.setInputValue("shinywidgets_comm_send", msg_txt, {priority: "event"});
    }

    return msg_id;
  }

  // The browser created this model (e.g. bqplot's toolbar PanZoom): ask Python
  // to construct its counterpart, as a kernel's jupyter.widget target would.
  open(
    data: any,
    callbacks: any,
    metadata?: any,
    buffers?: ArrayBuffer[] | ArrayBufferView[]
  ): string {
    const [msg_id, msg_txt] = this._message(
      "comm_open", {target_name: this.target_name, data: data}, metadata, buffers
    );
    Shiny.setInputValue("shinywidgets_comm_send", msg_txt, {priority: "event"});
    return msg_id;
  }

  close(
    data?: any,
    callbacks?: any,
    metadata?: any,
    buffers?: ArrayBuffer[] | ArrayBufferView[]
  ): string {
    if (this.closed) {
      return this.comm_id;
    }
    this.closed = true;
    this.throttler.flush();
    this.dispose();
    const content = {data: data || {}};
    const [msg_id, msg_txt] = this._message("comm_close", content, metadata, buffers);
    if (connected) {
      Shiny.setInputValue("shinywidgets_comm_send", msg_txt, {priority: "event"});
    }
    // Like JupyterLab's CommHandler.close(): the model's own close handler runs
    // too, which is what makes it fire comm:close so the manager drops it.
    this.handle_close({content: {comm_id: this.comm_id, ...content}});
    return msg_id;
  }

  // Not ack(): reporting idle would make the closing model flush its buffered
  // change through this closed comm.
  dispose(): void {
    this.pending.clear();
    if (comms.get(this.comm_id) === this) comms.delete(this.comm_id);
  }

  ack(msg_id: string): void {
    const onIdle = this.pending.get(msg_id);
    if (!onIdle) return;
    this.pending.delete(msg_id);
    onIdle(IDLE);
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

  private _message(
    msg_type: CommMsgType,
    content: Record<string, any>,
    metadata?: any,
    buffers?: ArrayBuffer[] | ArrayBufferView[]
  ): [string, string] {
    // The model remembers the returned id for the attributes it just sent, and
    // ignores Python's echo_updates until one names this id in its
    // parent_header (which Python copies from this header), so stale echoes
    // can't overwrite newer browser-side values.
    const msg_id = `${this.comm_id}-${++this.msgCount}`;
    const msg = {
      content: {comm_id: this.comm_id, ...content},
      metadata: metadata,
      buffers: base64EncodeBuffers(buffers || []),
      header: {msg_id: msg_id, msg_type: msg_type}
    };
    return [msg_id, JSON.stringify(msg)];
  }
}
