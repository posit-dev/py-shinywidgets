/**
 * Works around anywidget's hard-coded 2s model-initialization timeout in the
 * browser, at module-load time.
 *
 * anywidget's front-end (`Runtime`, packages/anywidget/src/runtime.ts) rejects
 * the model's `ready` promise via `AbortSignal.timeout(2000)` when loading the
 * widget's `_esm` takes too long, and `AnyModel._handle_comm_msg` awaits that
 * promise before delegating to `DOMWidgetModel._handle_comm_msg`. Widgets with
 * multi-MB inline ESM (keplergl's `_esm` is ~13MB) can't compile within 2s on
 * slower hardware, so after the rejection every subsequent Python -> browser
 * state update throws and is permanently dropped -- a silent, permanent desync
 * (the widget itself often still renders, since the view reads state lazily).
 *
 * Since we can't (and don't want to) patch anywidget's served source, we patch
 * the model class's prototype here, when the `anywidget` module is loaded
 * through our loader: state updates that fail because `ready` rejected are
 * applied via the base ipywidgets implementation instead. Everything is
 * feature-detected, so if anywidget's internals change, behavior reverts to
 * stock anywidget.
 */

// The message anywidget rejects `ready` with on init timeout. If upstream
// rewords it, the patch simply stops applying (stock behavior resumes).
const INIT_FAILURE_MESSAGE = 'Failed to initialize model';

// Per-model flag (own property on the model instance) marking that `ready`
// has rejected, so subsequent state updates skip the doomed `await ready`
// and go straight to the base implementation.
const READY_FAILED_FLAG = '__shinywidgetsAnywidgetReadyFailed';

type CommMsg = {
  content?: { data?: { method?: string } };
};

type CommMsgHandler = (this: object, msg: CommMsg) => Promise<unknown>;

let patchLogged = false;

// The Runtime's `ready` promise rejects at the 2s mark whether or not a comm
// message happens to be awaiting it right then. When none is, the rejection
// is unhandled and surfaces as a console error even though our patched
// `_handle_comm_msg` handles (and warns about) the failure on the next
// message. Suppress exactly that rejection -- it only exists because
// anywidget's budget expired, which is the condition this patch tolerates.
function suppressInitTimeoutRejections(): void {
  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason as unknown;
    if (
      reason instanceof Error &&
      reason.message.includes(INIT_FAILURE_MESSAGE)
    ) {
      event.preventDefault();
    }
  });
}

export function patchAnywidgetModelInit(module: unknown): void {
  try {
    const AnyModel = (module as Record<string, unknown>)?.AnyModel;
    if (typeof AnyModel !== 'function') return;
    const proto = AnyModel.prototype as Record<string, unknown> | null;
    if (!proto || typeof proto._handle_comm_msg !== 'function') return;

    const original = proto._handle_comm_msg as CommMsgHandler & {
      __shinywidgetsPatched?: boolean;
    };
    // require.js caches the module, but guard anyway so repeated loads don't
    // stack wrappers.
    if (original.__shinywidgetsPatched) return;

    // The base (DOMWidgetModel) implementation anywidget's override delegates
    // to after `await ready`. Walk the prototype chain rather than importing
    // `@jupyter-widgets/base` ourselves: anywidget's AMD bundle extends the
    // copy registered in libembed-amd.js, which may not be the same module
    // instance as the one bundled into this script.
    let baseProto = Object.getPrototypeOf(proto) as Record<string, unknown> | null;
    while (baseProto && typeof baseProto._handle_comm_msg !== 'function') {
      baseProto = Object.getPrototypeOf(baseProto) as Record<string, unknown> | null;
    }
    if (!baseProto) return;
    const baseHandleCommMsg = baseProto._handle_comm_msg as CommMsgHandler;

    const warned = new WeakSet<object>();

    const warnOnce = (model: object): void => {
      if (warned.has(model)) return;
      warned.add(model);
      console.warn(
        `[shinywidgets] anywidget model initialization timed out ` +
          `(anywidget's built-in 2s budget; the widget's JS bundle is likely ` +
          `too large to compile in time). Applying Python state updates ` +
          `without it; custom messages to this model will be dropped.`
      );
    };

    const isInitTimeout = (err: unknown): boolean =>
      err instanceof Error && err.message.includes(INIT_FAILURE_MESSAGE);

    const patched: CommMsgHandler & { __shinywidgetsPatched?: boolean } =
      function (this: Record<string, unknown>, msg: CommMsg) {
        const method = msg?.content?.data?.method;
        const isStateUpdate = method === 'update' || method === 'echo_update';
        const isCustom = method === 'custom';
        // Not a message shape anywidget's override gates on: leave untouched.
        if (!isStateUpdate && !isCustom) {
          return Promise.resolve(original.call(this, msg));
        }

        if (this[READY_FAILED_FLAG]) {
          // `ready` rejected permanently (first settle wins), so the original
          // would throw on every subsequent message. Backbone `set()`s are
          // safe before the view exists -- the view reads current state when
          // it renders -- so apply state updates via the base implementation.
          // Custom messages target the widget's JS module, which may never
          // have initialized; drop them (already warned).
          if (isStateUpdate) {
            return Promise.resolve(baseHandleCommMsg.call(this, msg));
          }
          return Promise.resolve();
        }

        return Promise.resolve(original.call(this, msg)).catch(
          (err: unknown) => {
            if (!isInitTimeout(err)) throw err;
            this[READY_FAILED_FLAG] = true;
            warnOnce(this);
            if (isStateUpdate) {
              return baseHandleCommMsg.call(this, msg);
            }
            return undefined;
          }
        );
      };
    patched.__shinywidgetsPatched = true;
    proto._handle_comm_msg = patched;

    if (!patchLogged) {
      patchLogged = true;
      suppressInitTimeoutRejections();
      console.debug(
        '[shinywidgets] Patched anywidget AnyModel to survive model-init timeouts.'
      );
    }
  } catch (err) {
    // Feature detection failed in an unexpected way: keep stock behavior.
    console.debug('[shinywidgets] Skipping anywidget init-timeout patch:', err);
  }
}
