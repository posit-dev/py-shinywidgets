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

// plotly_hover streams per mousemove, so the bridge throttles its forwarding
// (leading + trailing edge of a streak) to bound websocket traffic. Python's
// own debounce limits reactive invalidation, but not bytes on the wire.
export const HOVER_THROTTLE_MS = 250;

export interface Throttled {
  (data?: any): void;
  cancel(): void;
}

// Leading + trailing throttle: the first call forwards immediately, calls
// inside the window collapse into one trailing forward of the last value when
// the window closes. cancel() drops a pending trailing forward (e.g. an
// unhover must not be followed by a stale hover).
export function throttleLeadTrail(
  fn: (data?: any) => void,
  windowMs: number,
): Throttled {
  let last = Number.NEGATIVE_INFINITY;
  let pending: { data: any } | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  const throttled = ((data?: any) => {
    const now = Date.now();
    if (now - last >= windowMs) {
      last = now;
      fn(data);
      return;
    }
    pending = { data };
    if (timer === null) {
      timer = setTimeout(() => {
        timer = null;
        if (pending !== null) {
          const p = pending;
          pending = null;
          last = Date.now();
          fn(p.data);
        }
      }, windowMs - (now - last));
    }
  }) as Throttled;
  throttled.cancel = () => {
    pending = null;
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
    last = Number.NEGATIVE_INFINITY;
  };
  return throttled;
}

export function bindPlotlyEvents(plotEl: HTMLElement, model: WidgetModel): void {
  const requested = requestedEvents.get(model);
  if (!requested || !hasMethod<PlotlyEventEmitter, "on">(plotEl, "on")) return;
  const bound = boundEvents.get(plotEl) ?? new Set<string>();
  boundEvents.set(plotEl, bound);
  let boundSelected = false;
  let boundRestyle = false;
  // Hover's throttler is created before any binding below, so unhover can
  // cancel its trailing forward regardless of the requested set's order.
  const hoverThrottle =
    requested.has("plotly_hover") && !bound.has("plotly_hover")
      ? throttleLeadTrail((data?: any) => {
          model.send(
            { shinywidgets: "event", event: "plotly_hover", ...eventPayload("plotly_hover", data) },
            {},
          );
        }, HOVER_THROTTLE_MS)
      : undefined;
  for (const event of requested) {
    if (bound.has(event)) continue;
    bound.add(event);
    if (event === "plotly_selected") boundSelected = true;
    if (event === "plotly_restyle") boundRestyle = true;
    if (event === "plotly_hover" && hoverThrottle) {
      plotEl.on(event, hoverThrottle);
      continue;
    }
    if (event === "plotly_unhover" && hoverThrottle) {
      plotEl.on(event, (data?: any) => {
        hoverThrottle.cancel();
        model.send({ shinywidgets: "event", event, ...eventPayload(event, data) }, {});
      });
      continue;
    }
    plotEl.on(event, (data?: any) => {
      model.send({ shinywidgets: "event", event, ...eventPayload(event, data, plotEl) }, {});
    });
  }
  // Like the selection seed below: trace visibility is state on the graph
  // div, so report it at bind (as a synthetic restyle, which is how later
  // visibility changes arrive).
  if (boundRestyle) {
    model.send(
      { shinywidgets: "event", event: "plotly_restyle", traces: visibilitySeed(plotEl) },
      {},
    );
  }
  // A selection is state on the graph div (trace `selectedpoints`), not just
  // an event: a lasso drawn before this bind (e.g. before an accessor's first
  // read asked for the event) is still recoverable, so report the current
  // selection as if plotly.js had just fired it. An empty payload is a
  // no-data `plotly_selected`, which plotly.js itself sends for an empty
  // selection and Python reads as "nothing selected".
  if (boundSelected) {
    model.send(
      { shinywidgets: "event", event: "plotly_selected", ...selectionSeed(plotEl) },
      {},
    );
  }
}

// Rebuilds a plotly_selected payload from graph-div state: one entry per
// selected point, plus the region (box range or lasso vertices) plotly.js
// keeps on the last layout selection.
function selectionSeed(plotEl: HTMLElement): Record<string, unknown> {
  const data = (plotEl as any).data;
  if (!Array.isArray(data)) return {};
  const points = data.flatMap((trace: any, curveNumber: number) => {
    // jsonable(): a selection preconfigured from plotly.py arrives as a
    // typed array, which Array.isArray rejects (and whose .map can't hold
    // point objects)
    const selected = jsonable(trace?.selectedpoints);
    if (!Array.isArray(selected)) return [];
    return (selected as number[]).map((i) => {
      const entry: Record<string, unknown> = {
        trace_index: curveNumber,
        point_index: i,
      };
      for (const key of ["x", "y", "z", "customdata"]) {
        let value = trace[key]?.[i];
        // A multicategory axis stores one array per category level (so the
        // trace array's length is the level count, not the point count, and
        // indexing it by sample is wrong); the coordinate combines each
        // level's value at i
        if (key !== "customdata" && Array.isArray(trace[key]) && Array.isArray(trace[key][0])) {
          value = (trace[key] as any[]).map((level) => level?.[i]);
        } else if (value === undefined && key !== "customdata") {
          // Coordinates the trace doesn't carry explicitly (implicit x,
          // bar x0/dx) are resolved on calcdata, matching the live event's
          // point objects
          value = calcCoord(plotEl, curveNumber, i, key, trace?.type);
        }
        if (value !== undefined) entry[key] = jsonable(value);
      }
      return entry;
    });
  });
  // An empty drag selection is still a selection: plotly.js reports it as
  // points: [] plus the region. So is a preconfigured selectedpoints: []
  // (plotly dims every point with unselected styling). No points, no
  // region, and no trace supplying a selection array means nothing was
  // ever selected (or a deselect), the no-data case.
  const region = regionSeed(plotEl);
  const anySelectionArray = data.some((trace: any) =>
    Array.isArray(jsonable(trace?.selectedpoints)),
  );
  if (points.length === 0 && Object.keys(region).length === 0 && !anySelectionArray) {
    return {};
  }
  return { points, ...region };
}

function regionSeed(plotEl: HTMLElement): Record<string, unknown> {
  const selections = (plotEl as any)._fullLayout?.selections;
  if (!Array.isArray(selections) || selections.length === 0) return {};
  const last = selections[selections.length - 1];
  // Selections on later subplots reference their axes (x2, y2, ...), and
  // live events key the region the same way
  const xref = typeof last.xref === "string" ? last.xref : "x";
  const yref = typeof last.yref === "string" ? last.yref : "y";
  // A box selection keeps its corners; the event reports each axis ascending
  if (last.x0 !== undefined) {
    const asc = (a: any, b: any) => (a <= b ? [a, b] : [b, a]);
    return { range: { [xref]: asc(last.x0, last.x1), [yref]: asc(last.y0, last.y1) } };
  }
  // A lasso keeps its vertices as an SVG path: "M x,y L x,y ...". On date
  // axes the values are date strings with "_" for the date/time separator;
  // live lassoPoints restore the space.
  if (typeof last.path === "string") {
    const x: unknown[] = [];
    const y: unknown[] = [];
    const vertex = /[ML]([^MLZz]+)/g;
    let m: RegExpExecArray | null;
    while ((m = vertex.exec(last.path)) !== null) {
      const sep = m[1].lastIndexOf(",");
      if (sep < 0) continue;
      x.push(lassoValue(m[1].slice(0, sep)));
      y.push(lassoValue(m[1].slice(sep + 1)));
    }
    if (x.length > 0) return { lassoPoints: { [xref]: x, [yref]: y } };
  }
  return {};
}

// Resolved coordinates from calcdata, for the trace types where its layout
// is verified: scatter and bar align one calc point per data index
// (implicit x, x0/dx); scattergl keeps one calc entry whose .t holds typed
// coordinate arrays. Others don't align by sample index (histograms bin
// them) or are unverified, so their missing keys stay missing, as in live
// payloads.
function calcCoord(
  plotEl: HTMLElement,
  curveNumber: number,
  i: number,
  key: string,
  type: string | undefined,
): unknown {
  const cd = (plotEl as any).calcdata?.[curveNumber];
  if (!Array.isArray(cd)) return undefined;
  if (type === "scattergl") return cd[0]?.t?.[key]?.[i];
  if (type === "scatter" || type === "bar") return cd[i]?.[key];
  return undefined;
}

function lassoValue(token: string): unknown {
  const t = token.trim();
  const n = Number(t);
  return Number.isNaN(n) ? t.replace("_", " ") : n;
}

// Shaped like R plotly's event_data(): one entry per point, with its trace
// index, its index within the trace, coordinates, and customdata.
export function eventPayload(
  event: string,
  data: any,
  plotEl?: HTMLElement,
): Record<string, unknown> {
  if (event === "plotly_relayout") return { relayout: data };
  // The restyle args themselves aren't useful; what matters is the
  // visibility they left behind, which the graph div holds post-restyle
  // (Plots.restyle emits plotly_restyle after applying the update).
  if (event === "plotly_restyle") return plotEl ? { traces: visibilitySeed(plotEl) } : {};
  if (event === "plotly_legendclick") return legendPayload(data);
  const out: Record<string, unknown> = {};
  if (!data) return out;
  if (Array.isArray(data.points)) out.points = data.points.flatMap(pointEntries);
  if (data.range) out.range = data.range;
  if (data.lassoPoints) out.lassoPoints = data.lassoPoints;
  return out;
}

// A minimal answer to R plotly's legendEventData, which ships whole trace
// objects (data arrays included): the clicked trace first, then the other
// traces of its legendgroup (plotly.js toggles the whole group by default).
function legendPayload(data: any): Record<string, unknown> {
  if (!data || !Array.isArray(data.data)) return {};
  const traces: any[] = data.data;
  const clicked = traces[data.curveNumber];
  if (!clicked) return {};
  // An empty-string legendgroup is plotly's default, not a group
  const group = clicked.legendgroup || null;
  const ordered: number[] = [data.curveNumber];
  if (group) {
    traces.forEach((t: any, i: number) => {
      if (i !== data.curveNumber && t?.legendgroup === group) ordered.push(i);
    });
  }
  return {
    legend: {
      traces: ordered.map((i) => ({
        trace_index: i,
        name: traceName(data.fullData, traces, i),
        legendgroup: traces[i]?.legendgroup ?? null,
      })),
    },
  };
}

// One entry per trace with its current visibility, seeded at bind and
// recomputed on every restyle. `visible` is the trace's own attribute (false
// once a legend click hides it), so traces expanded by a groupby transform
// report their own visibility, not each group's.
export function visibilitySeed(plotEl: HTMLElement): Record<string, unknown>[] {
  const data = (plotEl as any).data;
  if (!Array.isArray(data)) return [];
  return data.map((trace: any, i: number) => ({
    trace_index: i,
    name: traceName((plotEl as any)._fullData, data, i),
    visible: trace?.visible !== false && trace?.visible !== "legendonly",
  }));
}

// plotly auto-names traces ("trace 0") only on the full trace; use it when
// fullData aligns with data by user-trace index (it doesn't once a transform
// expands a trace).
function traceName(fullData: any, traces: any[], i: number): unknown {
  const full = Array.isArray(fullData) ? fullData[i] : undefined;
  if (full?.index === i && typeof full.name === "string") return full.name;
  return traces[i]?.name ?? `trace ${i}`;
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
