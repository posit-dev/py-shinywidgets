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
export type PlotlyPayloadShape = "region" | "points";

export interface PlotlyBindRequest {
  shinywidgets: "bind";
  events: (string | { name: string; payload?: PlotlyPayloadShape })[];
}

// Union the bind requests' payload shapes per event; "points" wins over
// "region". Bare string entries (clears, non-selection events) mean full
// payloads, so they normalize to "points".
export function normalizeBindEvents(
  events: PlotlyBindRequest["events"],
): Map<string, PlotlyPayloadShape> {
  const out = new Map<string, PlotlyPayloadShape>();
  for (const e of events) {
    const name = typeof e === "string" ? e : e.name;
    const payload = (typeof e === "object" && e.payload) || "points";
    if (out.get(name) !== "points") out.set(name, payload);
  }
  return out;
}

// The payload shape requested for each event of each model, applied to
// every view of it ("points" wins over "region" for the same event)
const requestedEvents = new WeakMap<WidgetModel, Map<string, PlotlyPayloadShape>>();
// The events already bound on each graph div
const boundEvents = new WeakMap<HTMLElement, Set<string>>();

export function isPlotlyBindRequest(content: unknown): content is PlotlyBindRequest {
  return (
    !!content &&
    (content as any).shinywidgets === "bind" &&
    Array.isArray((content as any).events) &&
    (content as any).events.every(
      (e: unknown) => typeof e === "string" || (!!e && typeof (e as any).name === "string"),
    )
  );
}

export async function requestPlotlyEvents(
  model: WidgetModel,
  events: PlotlyBindRequest["events"],
): Promise<void> {
  const incoming = normalizeBindEvents(events);
  const requested = requestedEvents.get(model) ?? new Map<string, PlotlyPayloadShape>();
  for (const [name, payload] of incoming) {
    if (requested.get(name) !== "points") requested.set(name, payload);
  }
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
  let boundSelected = false;
  let boundVisibility = false;
  for (const event of requested.keys()) {
    if (bound.has(event)) continue;
    bound.add(event);
    if (event === "plotly_selected") boundSelected = true;
    if (VISIBILITY_EVENTS.has(event)) boundVisibility = true;
    plotEl.on(event, (data?: any) => {
      model.send(
        {
          shinywidgets: "event",
          event,
          ...eventPayload(event, data, plotEl, requested.get(event) === "points"),
        },
        {},
      );
    });
  }
  // Like the selection seed below: trace visibility is state on the graph
  // div, so report it at bind (as a synthetic restyle, which is how later
  // visibility changes arrive).
  if (boundVisibility) {
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
      {
        shinywidgets: "event",
        event: "plotly_selected",
        ...selectionSeed(plotEl, requested.get("plotly_selected") === "points"),
      },
      {},
    );
  }
}

// Rebuilds a plotly_selected payload from graph-div state: one slim entry
// per selected point, plus the region (box range or lasso vertices)
// plotly.js keeps on the last layout selection.
export function selectionSeed(
  plotEl: HTMLElement,
  includePoints: boolean = true,
): Record<string, unknown> {
  const data = (plotEl as any).data;
  if (!Array.isArray(data)) return {};
  const points = includePoints
    ? data.flatMap((trace: any, curveNumber: number) => {
        // jsonable(): a selection preconfigured from plotly.py arrives as a
        // typed array, which Array.isArray rejects (and whose .map can't
        // hold point objects)
        const selected = jsonable(trace?.selectedpoints);
        if (!Array.isArray(selected)) return [];
        return (selected as number[]).map((i) => {
          const entry: Record<string, unknown> = {
            trace_index: curveNumber,
            point_index: i,
          };
          const custom = trace.customdata?.[i];
          if (custom !== undefined) entry.customdata = jsonable(custom);
          return entry;
        });
      })
    : [];
  // An empty drag selection is still a selection: plotly.js reports it as
  // points: [] plus the region (or, when points weren't requested, as just
  // the region). So is a preconfigured selectedpoints: [] (plotly dims
  // every point with unselected styling). No points, no region, and no
  // trace supplying a selection array means nothing was ever selected (or
  // a deselect), the no-data case.
  const region = regionSeed(plotEl);
  const anySelectionArray = data.some((trace: any) =>
    Array.isArray(jsonable(trace?.selectedpoints)),
  );
  if (points.length === 0 && Object.keys(region).length === 0 && !anySelectionArray) {
    return {};
  }
  const out: Record<string, unknown> = { ...region };
  if (includePoints) out.points = points;
  return out;
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

function lassoValue(token: string): unknown {
  const t = token.trim();
  const n = Number(t);
  return Number.isNaN(n) ? t.replace("_", " ") : n;
}

// Selection events ship slim points ({trace_index, point_index,
// customdata?}) — coordinates would duplicate data the server already has
// (#459)
const SLIM_EVENTS = new Set(["plotly_selected", "plotly_selecting"]);

// Shaped like R plotly's event_data(): one entry per point, with its trace
// index, its index within the trace, coordinates, and customdata.
export function eventPayload(
  event: string,
  data: any,
  plotEl?: HTMLElement,
  includePoints: boolean = true,
): Record<string, unknown> {
  if (event === "plotly_relayout") return { relayout: data };
  // The event args themselves aren't useful; what matters is the
  // visibility they left behind, which the graph div holds post-restyle
  // (Plots.restyle emits plotly_restyle after applying the update).
  // plotly_update covers Plotly.update (e.g. plotly.py's batch_update),
  // which emits it instead of plotly_restyle; plotly_redraw covers
  // Plotly.addTraces/deleteTraces/moveTraces, which redraw without either
  if (VISIBILITY_EVENTS.has(event)) {
    return plotEl ? { traces: visibilitySeed(plotEl) } : {};
  }
  if (event === "plotly_legendclick") return legendPayload(data);
  const out: Record<string, unknown> = {};
  if (!data) return out;
  if (Array.isArray(data.points)) {
    if (SLIM_EVENTS.has(event)) {
      if (includePoints) out.points = data.points.flatMap(slimPointEntries);
    } else {
      out.points = data.points.flatMap(pointEntries);
    }
  }
  if (data.range) out.range = data.range;
  if (data.lassoPoints) out.lassoPoints = data.lassoPoints;
  return out;
}

// Events that leave trace visibility (or the trace list itself) changed:
// the visibility snapshot is recomputed from the graph div when one fires
const VISIBILITY_EVENTS = new Set(["plotly_restyle", "plotly_update", "plotly_redraw"]);

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
  if (group && groupClickTogglesGroup(data)) {
    traces.forEach((t: any, i: number) => {
      // plotly.js toggles the group mates too, except ones already at
      // visible: false (a click can't make them more hidden)
      if (i !== data.curveNumber && t?.legendgroup === group && t?.visible !== false) {
        ordered.push(i);
      }
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

// plotly.js's handleItemClick expands a legend click to the whole
// legendgroup only when the clicked trace's own legend has
// groupclick="togglegroup" (the default); "toggleitem" toggles just the
// clicked trace. Full traces carry their legend's id ("legend", "legend2",
// ...) in .legend, and the legend objects live on fullLayout under it.
function groupClickTogglesGroup(data: any): boolean {
  const fullData = data.fullData;
  const fullTrace = Array.isArray(fullData) ? fullData[data.curveNumber] : undefined;
  const legendId = typeof fullTrace?.legend === "string" ? fullTrace.legend : "legend";
  const groupclick = data.fullLayout?.[legendId]?.groupclick;
  // supplyDefaults fills groupclick, so a missing one means the payload
  // came without fullLayout (keep the default behavior)
  return groupclick === undefined || groupclick === "togglegroup";
}

// One entry per trace with its current visibility, seeded at bind and
// recomputed on every restyle. `visible` is the trace's own attribute (false
// once a legend click hides it), so traces expanded by a groupby transform
// report their own visibility, not each group's.
export function visibilitySeed(
  plotEl: HTMLElement,
): { trace_index: number; name: string; visible: boolean }[] {
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
function traceName(fullData: any, traces: any[], i: number): string {
  const full = Array.isArray(fullData) ? fullData[i] : undefined;
  if (full?.index === i && typeof full.name === "string") return full.name;
  return traces[i]?.name ?? `trace ${i}`;
}

// Like pointEntries, but without coordinates: the join key (customdata) is
// all selected_rows() needs, and coordinates are what made selection
// messages big enough to kill sessions
function slimPointEntries(p: any): Record<string, unknown>[] {
  const aggregated = Array.isArray(p.pointNumbers);
  const indices: number[] = aggregated ? p.pointNumbers : [p.pointNumber ?? p.pointIndex];
  return indices.map((i) => {
    const entry: Record<string, unknown> = { trace_index: p.curveNumber, point_index: i };
    const custom = aggregated ? p.data?.customdata?.[i] : p.customdata;
    if (custom !== undefined) entry.customdata = jsonable(custom);
    return entry;
  });
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
