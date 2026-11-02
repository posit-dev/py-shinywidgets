import type { WidgetModel } from '@jupyter-widgets/base';

interface PlotlyEventEmitter {
  on(eventName: string, callback: (data?: any) => void): void;
  once(eventName: string, callback: () => void): void;
  removeListener(eventName: string, callback: () => void): void;
}

const plotlyAfterPlotTimeoutMs = 5000;

export function findPlotlyGraphDiv(root: HTMLElement): HTMLElement | null {
  const plotlyEl = root.matches(".js-plotly-plot")
    ? root
    : root.querySelector(".js-plotly-plot");
  return plotlyEl instanceof HTMLElement ? plotlyEl : null;
}

// The plotly event bridge (see shinywidgets/_plotly.py): forwards plotly.js
// events that plotly.py's widget doesn't, as custom messages to Python. Python
// asks for the events its accessors need; nothing is bound until then.
export interface PlotlyBindRequest {
  shinywidgets: "bind";
  events: string[];
}

// The events requested for each model, applied to every view of it
const requestedEvents = new WeakMap<WidgetModel, Set<string>>();
// The events already bound on each graph div
const boundEvents = new WeakMap<HTMLElement, Set<string>>();

export function isPlotlyBindRequest(content: unknown): content is PlotlyBindRequest {
  return (
    !!content &&
    (content as any).shinywidgets === "bind" &&
    Array.isArray((content as any).events)
  );
}

export async function requestPlotlyEvents(
  model: WidgetModel,
  events: string[],
): Promise<void> {
  const requested = requestedEvents.get(model) ?? new Set<string>();
  events.forEach((e) => requested.add(e));
  requestedEvents.set(model, requested);

  // Views that render later bind in bindPlotlyEvents(), via plotlyBehavior
  for (const viewPromise of Object.values((model as any).views ?? {})) {
    try {
      const view: any = await viewPromise;
      // The view can exist well before Plotly draws its graph div into it
      // (e.g., while its JS is still loading); wait for the draw rather than
      // skipping the view, or the events would never get bound.
      const plotEl = await waitForPlotlyGraphDiv(view.el);
      if (!plotEl) continue;
      await waitForPlotlyAfterPlot(plotEl);
      bindPlotlyEvents(plotEl, model);
    } catch (err) {
      console.error("Error binding plotly events:", err);
    }
  }
}

const plotlyGraphDivTimeoutMs = 30000;

// Like findPlotlyGraphDiv, but waits (a bounded time) for the graph div to
// appear: Plotly draws asynchronously after the view is displayed, and a
// caller that gives up before then never gets another chance to bind.
export function waitForPlotlyGraphDiv(
  root: HTMLElement,
  timeoutMs: number = plotlyGraphDivTimeoutMs,
): Promise<HTMLElement | null> {
  const existing = findPlotlyGraphDiv(root);
  if (existing) return Promise.resolve(existing);

  return new Promise((resolve) => {
    const finish = (el: HTMLElement | null) => {
      observer.disconnect();
      window.clearTimeout(timer);
      resolve(el);
    };
    const observer = new MutationObserver(() => {
      const el = findPlotlyGraphDiv(root);
      if (el) finish(el);
    });
    const timer = window.setTimeout(() => finish(null), timeoutMs);
    observer.observe(root, { childList: true, subtree: true });
  });
}

export function bindPlotlyEvents(plotEl: HTMLElement, model: WidgetModel): void {
  const requested = requestedEvents.get(model);
  if (!requested || !hasMethod<PlotlyEventEmitter, "on">(plotEl, "on")) return;
  const bound = boundEvents.get(plotEl) ?? new Set<string>();
  boundEvents.set(plotEl, bound);
  for (const event of requested) {
    if (bound.has(event)) continue;
    bound.add(event);
    plotEl.on(event, (data?: any) => {
      model.send({ shinywidgets: "event", event, ...eventPayload(event, data) }, {});
    });
  }
}

// Shaped like R plotly's event_data(): one entry per point, with its trace
// index, its index within the trace, coordinates, and customdata.
function eventPayload(event: string, data: any): Record<string, unknown> {
  if (event === "plotly_relayout") return { relayout: data };
  const out: Record<string, unknown> = {};
  if (!data) return out;
  if (Array.isArray(data.points)) out.points = data.points.flatMap(pointEntries);
  if (data.range) out.range = data.range;
  if (data.lassoPoints) out.lassoPoints = data.lassoPoints;
  return out;
}

function pointEntries(p: any): Record<string, unknown>[] {
  // Aggregated traces (e.g. histograms) report every underlying point
  const aggregated = Array.isArray(p.pointNumbers);
  const indices: number[] = aggregated ? p.pointNumbers : [p.pointNumber ?? p.pointIndex];
  return indices.map((i) => {
    const entry: Record<string, unknown> = { trace_index: p.curveNumber, point_index: i };
    for (const key of ["x", "y", "z", "customdata"]) {
      const value = aggregated ? p.data?.[key]?.[i] : p[key];
      if (value !== undefined) entry[key] = jsonable(value);
    }
    return entry;
  });
}

// plotly.js decodes plotly.py's binary arrays into typed arrays, which
// JSON.stringify would turn into {"0": ..., "1": ...} objects.
function jsonable(value: unknown): unknown {
  return ArrayBuffer.isView(value) ? Array.from(value as unknown as ArrayLike<number>) : value;
}

export async function waitForPlotlyReadyToReveal(
  plotEl: HTMLElement,
  dispatchResize: () => void,
): Promise<void> {
  const plotly = (window as any).Plotly;
  await waitForPlotlyAfterPlot(plotEl);

  if (plotly?.Plots?.resize) {
    try {
      const afterResize = waitForPlotlyAfterPlot(plotEl);
      await plotly.Plots.resize(plotEl);
      await afterResize;
    } catch (err) {
      console.error("Error resizing Plotly widget before reveal:", err);
    }
  }

  dispatchResize();
}

export function waitForPlotlyAfterPlot(plotEl: HTMLElement): Promise<void> {
  // If Plotly has already completed its render, _fullLayout will be populated.
  // This avoids waiting for an event that already fired before we subscribed.
  if ((plotEl as any)._fullLayout) {
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    const handler = () => {
      cleanup();
      resolve();
    };

    const cleanup = () => {
      if (hasMethod<PlotlyEventEmitter, "removeListener">(plotEl, "removeListener")) {
        plotEl.removeListener("plotly_afterplot", handler);
      }
      window.clearTimeout(timeoutId);
    };

    const timeoutId = window.setTimeout(() => {
      cleanup();
      resolve();
    }, plotlyAfterPlotTimeoutMs);

    if (hasMethod<PlotlyEventEmitter, "once">(plotEl, "once")) {
      plotEl.once("plotly_afterplot", handler);
      return;
    }

    if (hasMethod<PlotlyEventEmitter, "on">(plotEl, "on")) {
      plotEl.on("plotly_afterplot", handler);
      return;
    }

    cleanup();
    resolve();
  });
}

function hasMethod<T, K extends keyof T>(
  x: unknown,
  key: K,
): x is T & Record<K, (...args: any[]) => unknown> {
  return !!x && typeof (x as any)[key] === "function";
}
