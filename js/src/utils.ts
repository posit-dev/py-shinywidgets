import { decode, encode } from 'base64-arraybuffer';

// On the server, we're using jupyter_client.session.json_packer to serialize messages,
// and it encodes binary data (i.e., buffers) as base64, so decode it before passing it
// along to the comm logic
function jsonParse(x: string) {
  const msg = JSON.parse(x);
  msg.buffers = msg.buffers.map((base64: string) => new DataView(decode(base64)));
  return msg;
}

function normalizeBufferPayload(payload: ArrayBuffer | ArrayBufferView): ArrayBuffer {
  if (!ArrayBuffer.isView(payload)) {
    return payload;
  }

  const view = payload as ArrayBufferView;
  if (view.byteOffset === 0 && view.byteLength === view.buffer.byteLength) {
    return view.buffer;
  }

  return view.buffer.slice(view.byteOffset, view.byteOffset + view.byteLength);
}

function base64EncodeBuffer(payload: ArrayBuffer | ArrayBufferView): string {
  return encode(normalizeBufferPayload(payload));
}

function base64EncodeBuffers(
  buffers: ArrayBuffer[] | ArrayBufferView[]
): string[] {
  return buffers.map(base64EncodeBuffer);
}

class Throttler {
  fnToCall: Function;
  wait: number;
  timeoutId: ReturnType<typeof setTimeout>;
  constructor(wait: number = 100) {
    if (wait < 0) throw new Error("wait must be a positive number");
    this.wait = wait;
    this._reset();
  }
  // Try to execute the function immediately, if it is not waiting
  // If it is waiting, update the function to be called
  throttle(fn: Function) {
    if (fn.length > 0) throw new Error("fn must not take any arguments");

    if (this.isWaiting) {
      // If the timeout is currently waiting, update the func to be called
      this.fnToCall = fn;
    } else {
      // If there is nothing waiting, call it immediately
      // and start the throttling
      fn();
      this._setTimeout();
    }
  }
  // Execute the function immediately and reset the timeout
  // This is useful when the timeout is waiting and we want to
  // execute the function immediately to not have events be out
  // of order
  flush() {
    if (this.fnToCall) this.fnToCall();
    this._reset();
  }
  _setTimeout() {
    this.timeoutId = setTimeout(() => {
      if (this.fnToCall) {
        this.fnToCall();
        this.fnToCall = null;
        // Restart the timeout as we just called the function
        // This call is the key step of Throttler
        this._setTimeout();
      } else {
        this._reset();
      }
    }, this.wait);
  }
  _reset() {
    this.fnToCall = null;
    clearTimeout(this.timeoutId);
    this.timeoutId = null;
  }
  get isWaiting(): boolean {
    return this.timeoutId !== null;
  }
}


// itables' widget bundle assigns its own jQuery to the global `$` when its module is
// evaluated (which can happen at any point after page load, e.g., for an ITable nested
// in another widget). That breaks code that expects the page's jQuery (e.g., bslib's
// resize handling reads `$(el).data("shinyOutputBinding")`). `window.jQuery` is left
// alone by the bundle, so make `$` mirror it, but refuse jQuery instances assigned to
// `$` (anything else, e.g., `var $ = ...`, is honored). The server asks for this
// (`protect_jquery`) only when opening an itables model, before its module loads.
let pageJQueryProtected = false;

function protectPageJQuery(): void {
  if (pageJQueryProtected) return;
  pageJQueryProtected = true;

  const win = window as Window & { $?: unknown; jQuery?: unknown };
  // Keep a non-jQuery `$` that is already in place (e.g., after noConflict())
  const current = win.$;
  let hasOverride = current !== win.jQuery && !isJQuery(current);
  let override: unknown = hasOverride ? current : undefined;
  Object.defineProperty(win, '$', {
    configurable: true,
    enumerable: true,
    get: () => (hasOverride ? override : win.jQuery),
    set: (value: unknown) => {
      // itables evaluates JavascriptCode options against the global `$` (e.g., its
      // documented `$.fn.dataTable.render.number(...)`), so lend the refused jQuery's
      // DataTables plugin to the page jQuery
      if (isJQuery(value) && value !== win.jQuery) {
        lendDataTables(value as JQueryLike, win.jQuery as JQueryLike | undefined);
      }
      hasOverride = !isJQuery(value);
      override = hasOverride ? value : undefined;
    },
  });
}

type JQueryLike = { fn: { dataTable?: unknown; DataTable?: unknown } };

function lendDataTables(from: JQueryLike, to: JQueryLike | undefined): void {
  if (!to || !from.fn.dataTable || to.fn.dataTable) return;
  to.fn.dataTable = from.fn.dataTable;
  to.fn.DataTable = from.fn.DataTable;
}

function isJQuery(value: unknown): boolean {
  const fn = (value as { fn?: { jquery?: unknown } } | undefined)?.fn;
  return typeof value === 'function' && typeof fn?.jquery === 'string';
}

export { base64EncodeBuffers, jsonParse, protectPageJQuery, Throttler };
