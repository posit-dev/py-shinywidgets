import { decode } from 'base64-arraybuffer';

// On the server, we're using jupyter_client.session.json_packer to serialize messages,
// and it encodes binary data (i.e., buffers) as base64, so decode it before passing it
// along to the comm logic
function jsonParse(x: string) {
  const msg = JSON.parse(x);
  msg.buffers = msg.buffers.map((base64: string) => new DataView(decode(base64)));
  return msg;
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


export { jsonParse, Throttler };
