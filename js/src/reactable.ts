import type { WidgetModel } from '@jupyter-widgets/base';

/**
 * shinywidgets' reactable state bridge (see shinywidgets/_reactable.py).
 *
 * reactable-py's widget never calls model.send() itself, but its JS bundle
 * exports R reactable's state API (getState/onStateChange), keyed by the
 * table's elementId prop. When Python asks (a bind request, sent as an
 * accessor attaches), subscribe here and forward a pruned table state as
 * custom messages. Nothing is subscribed and no traffic flows until then.
 */

export interface ReactableBindRequest {
  shinywidgets: "bind-reactable";
}

export function isReactableBindRequest(content: unknown): content is ReactableBindRequest {
  return !!content && (content as any).shinywidgets === "bind-reactable";
}

interface ReactableModule {
  getState(elementId: string): Record<string, unknown>;
  onStateChange(elementId: string, fn: (state: Record<string, unknown>) => void): () => void;
}

// The state keys the accessors read. The raw state also carries the full
// dataset (data, sortedData, pageRows), which must never be sent.
const STATE_KEYS = ["page", "pageSize", "pages", "sorted", "filters", "searchValue", "selected"];

function prunedState(state: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const key of STATE_KEYS) out[key] = state?.[key] ?? null;
  return out;
}

// ipyreact registers the reactable ES module with the browser's import shim
// under the name "reactable" (both 0.4.x and 0.7 do; feature-detect so a
// future loading change degrades to "accessors don't fire" instead of
// breaking the table itself).
async function importReactableModule(): Promise<ReactableModule | null> {
  const w = window as any;
  try {
    if (typeof w.importShim === "function") {
      return (await w.importShim("reactable")) as ReactableModule;
    }
    // eslint-disable-next-line no-new-func
    return (await new Function('return import("reactable")')()) as ReactableModule;
  } catch (err) {
    console.error(
      "shinywidgets: couldn't import the reactable module; table state won't reach Python.",
      err
    );
    return null;
  }
}

// Models that want state reports (a bind request arrived), and models with a
// live subscription.
const requested = new WeakSet<WidgetModel>();
const subscribed = new WeakSet<WidgetModel>();

// A bind request can race the table's first render (the instance registers
// under its elementId only once the React component has mounted), so retry
// briefly before giving up until the next render re-triggers a bind.
const bindRetryDelayMs = 100;
const bindMaxAttempts = 50;

export async function requestReactableState(model: WidgetModel): Promise<void> {
  requested.add(model);
  if (subscribed.has(model)) {
    // A subscription already exists, so this request is another accessor
    // attaching: re-seed, or it would wait forever for the next interaction
    // (each accessor only sees messages sent after it attached)
    const state = await currentState(model);
    if (state) sendState(model, state);
    return;
  }
  await bindReactableState(model);
}

function sendState(model: WidgetModel, state: Record<string, unknown>): void {
  model.send({ shinywidgets: "reactable-state", state: prunedState(state) } as any, {});
}

// The table's current pruned state, or null if it can't be had (module
// unimportable, no elementId, or the instance hasn't registered yet)
async function currentState(model: WidgetModel): Promise<Record<string, unknown> | null> {
  const props = (model.get("props") ?? {}) as Record<string, unknown>;
  const elementId = props.elementId as string | undefined;
  if (!elementId) return null;
  const mod = await importReactableModule();
  if (!mod) return null;
  try {
    return mod.getState(elementId);
  } catch {
    return null;
  }
}

export async function bindReactableState(model: WidgetModel, attempt = 1): Promise<void> {
  if (!requested.has(model) || subscribed.has(model)) return;
  const props = (model.get("props") ?? {}) as Record<string, unknown>;
  const elementId = props.elementId as string | undefined;
  if (!elementId) return;
  const mod = await importReactableModule();
  if (!mod) return;

  let initial: Record<string, unknown>;
  try {
    initial = mod.getState(elementId);
  } catch {
    if (attempt < bindMaxAttempts) {
      window.setTimeout(() => void bindReactableState(model, attempt + 1), bindRetryDelayMs);
    }
    return;
  }
  subscribed.add(model);
  // Seed the current state, so state accessors resolve promptly after binding
  sendState(model, initial);
  mod.onStateChange(elementId, (state) => sendState(model, state));
}
