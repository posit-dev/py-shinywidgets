import { afterEach, describe, expect, it, vi } from "vitest";
import {
  eventPayload,
  normalizeBindEvents,
  requestPlotlyEvents,
  selectionSeed,
  visibilitySeed,
} from "./plotly";

const legendData = {
  curveNumber: 2,
  data: [
    { name: "a", legendgroup: "g1", x: [1, 2], y: [3, 4] },
    { name: "b", legendgroup: "g2", x: [1, 2], y: [3, 4] },
    { name: "c", legendgroup: "g1", x: [1, 2], y: [3, 4] },
  ],
};

describe("eventPayload plotly_legendclick", () => {
  it("ships the clicked trace first, then its legendgroup, without trace data", () => {
    const payload = eventPayload("plotly_legendclick", legendData);
    expect(payload).toEqual({
      legend: {
        traces: [
          { trace_index: 2, name: "c", legendgroup: "g1" },
          { trace_index: 0, name: "a", legendgroup: "g1" },
        ],
      },
    });
  });

  it("ships only the clicked trace when it has no legendgroup", () => {
    const payload = eventPayload("plotly_legendclick", {
      curveNumber: 1,
      data: legendData.data,
    });
    expect(payload).toEqual({
      legend: { traces: [{ trace_index: 1, name: "b", legendgroup: "g2" }] },
    });
    // An empty-string legendgroup is plotly's default, not a group
    const ungrouped = eventPayload("plotly_legendclick", {
      curveNumber: 0,
      data: [{ name: "a", legendgroup: "" }],
    });
    expect(ungrouped).toEqual({
      legend: { traces: [{ trace_index: 0, name: "a", legendgroup: "" }] },
    });
  });

  it("ships only the clicked trace when the legend's groupclick is toggleitem", () => {
    const payload = eventPayload("plotly_legendclick", {
      curveNumber: 2,
      data: legendData.data,
      fullData: legendData.data.map((t, i) => ({ ...t, index: i })),
      fullLayout: { legend: { groupclick: "toggleitem" } },
    });
    expect(payload).toEqual({
      legend: { traces: [{ trace_index: 2, name: "c", legendgroup: "g1" }] },
    });
  });

  it("expands the group when the clicked trace's legend has groupclick togglegroup", () => {
    const grouped = eventPayload("plotly_legendclick", {
      curveNumber: 2,
      data: legendData.data,
      fullData: legendData.data.map((t, i) => ({ ...t, index: i })),
      fullLayout: { legend: { groupclick: "togglegroup" } },
    });
    expect(grouped).toEqual({
      legend: {
        traces: [
          { trace_index: 2, name: "c", legendgroup: "g1" },
          { trace_index: 0, name: "a", legendgroup: "g1" },
        ],
      },
    });
    // The applicable legend is the clicked trace's own (legend2 here): its
    // toggleitem wins even though the default legend toggles groups
    const secondLegend = eventPayload("plotly_legendclick", {
      curveNumber: 2,
      data: legendData.data,
      fullData: legendData.data.map((t, i) => ({
        ...t,
        index: i,
        legend: i === 2 ? "legend2" : "legend",
      })),
      fullLayout: {
        legend: { groupclick: "togglegroup" },
        legend2: { groupclick: "toggleitem" },
      },
    });
    expect(secondLegend).toEqual({
      legend: { traces: [{ trace_index: 2, name: "c", legendgroup: "g1" }] },
    });
  });

  it("leaves out group mates hidden with visible false (plotly doesn't toggle them)", () => {
    const payload = eventPayload("plotly_legendclick", {
      curveNumber: 2,
      data: [
        { name: "a", legendgroup: "g1", visible: false },
        { name: "b", legendgroup: "g2" },
        { name: "c", legendgroup: "g1" },
      ],
    });
    expect(payload).toEqual({
      legend: { traces: [{ trace_index: 2, name: "c", legendgroup: "g1" }] },
    });
  });

  it("resolves auto-generated names from fullData when indices align", () => {
    const payload = eventPayload("plotly_legendclick", {
      curveNumber: 0,
      data: [{}],
      fullData: [{ index: 0, name: "trace 0" }],
    });
    expect(payload).toEqual({
      legend: { traces: [{ trace_index: 0, name: "trace 0", legendgroup: null }] },
    });
  });

  it("is empty without trace data", () => {
    expect(eventPayload("plotly_legendclick", undefined)).toEqual({});
    expect(eventPayload("plotly_legendclick", { curveNumber: 0 })).toEqual({});
  });
});

describe("visibilitySeed", () => {
  it("reports each trace's visible attribute, legendonly included", () => {
    const plotEl = {
      data: [
        { name: "a" },
        { name: "b", visible: false },
        { name: "c", visible: "legendonly" },
        { name: "d", visible: true },
      ],
    } as unknown as HTMLElement;
    expect(visibilitySeed(plotEl)).toEqual([
      { trace_index: 0, name: "a", visible: true },
      { trace_index: 1, name: "b", visible: false },
      { trace_index: 2, name: "c", visible: false },
      { trace_index: 3, name: "d", visible: true },
    ]);
  });

  it("falls back to plotly's auto-generated names", () => {
    const plotEl = {
      data: [{}],
      _fullData: [{ index: 0, name: "trace 0" }],
    } as unknown as HTMLElement;
    expect(visibilitySeed(plotEl)).toEqual([
      { trace_index: 0, name: "trace 0", visible: true },
    ]);
  });

  it("shapes restyle and update payloads from the graph div's current state", () => {
    const plotEl = {
      data: [{ name: "a", visible: "legendonly" }],
    } as unknown as HTMLElement;
    const expected = {
      traces: [{ trace_index: 0, name: "a", visible: false }],
    };
    expect(eventPayload("plotly_restyle", [["visible", "legendonly"], [0]], plotEl)).toEqual(expected);
    // Plotly.update (e.g. plotly.py's batch_update) emits plotly_update, not plotly_restyle
    expect(eventPayload("plotly_update", {}, plotEl)).toEqual(expected);
    // Plotly.addTraces/deleteTraces/moveTraces redraw, emitting plotly_redraw
    expect(eventPayload("plotly_redraw", undefined, plotEl)).toEqual(expected);
  });
});

describe("normalizeBindEvents", () => {
  it("unions shapes with points winning over region", () => {
    const m = normalizeBindEvents([
      { name: "plotly_selected", payload: "region" },
      { name: "plotly_selected", payload: "points" },
      "plotly_deselect",
    ]);
    expect(m.get("plotly_selected")).toBe("points");
    expect(m.get("plotly_deselect")).toBe("points");
  });

  it("keeps region when only region is requested", () => {
    const m = normalizeBindEvents([{ name: "plotly_selected", payload: "region" }]);
    expect(m.get("plotly_selected")).toBe("region");
  });
});

describe("eventPayload selection slimming", () => {
  const data = {
    points: [
      { curveNumber: 0, pointNumber: 3, x: 1.5, y: 2.5, customdata: "row-3" },
      { curveNumber: 0, pointNumber: 4, x: 1.6, y: 2.6 },
    ],
    range: { x: [1, 2], y: [2, 3] },
  };

  it("plotly_selected sends slim points and the region when points requested", () => {
    const out = eventPayload("plotly_selected", data, undefined, true);
    expect(out.points).toEqual([
      { trace_index: 0, point_index: 3, customdata: "row-3" },
      { trace_index: 0, point_index: 4 },
    ]);
    expect(out.range).toEqual(data.range);
  });

  it("plotly_selected omits points but keeps the region when region-only", () => {
    const out = eventPayload("plotly_selected", data, undefined, false);
    expect("points" in out).toBe(false);
    expect(out.range).toEqual(data.range);
  });

  it("aggregated traces keep per-sample customdata from pointNumbers", () => {
    const agg = {
      points: [
        {
          curveNumber: 0,
          pointNumber: 0,
          pointNumbers: [10, 11],
          data: { customdata: ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"] },
        },
      ],
    };
    const out = eventPayload("plotly_selected", agg, undefined, true);
    expect(out.points).toEqual([
      { trace_index: 0, point_index: 10, customdata: "k" },
      { trace_index: 0, point_index: 11, customdata: "l" },
    ]);
  });

  it("plotly_click keeps coordinates", () => {
    const out = eventPayload("plotly_click", data, undefined, false);
    expect(out.points).toEqual([
      { trace_index: 0, point_index: 3, x: 1.5, y: 2.5, customdata: "row-3" },
      { trace_index: 0, point_index: 4, x: 1.6, y: 2.6 },
    ]);
  });
});

describe("requestPlotlyEvents", () => {
  // The tests run in node, so give findPlotlyGraphDiv's `instanceof
  // HTMLElement` a class to check the fake graph div against
  class FakeHTMLElement {}
  afterEach(() => vi.unstubAllGlobals());

  const makePlotEl = () =>
    Object.assign(new FakeHTMLElement(), {
      matches: () => true,
      on: vi.fn(),
      data: [
        {
          x: [1, 2, 3],
          y: [4, 5, 6],
          customdata: ["a", "b", "c"],
          selectedpoints: [0, 2],
        },
      ],
      _fullLayout: { selections: [{ xref: "x", yref: "y", x0: 1, x1: 3, y0: 4, y1: 6 }] },
    });

  const makeModel = (plotEl: unknown, sent: unknown[]) =>
    ({
      views: { "1": Promise.resolve({ el: plotEl }) },
      send: (msg: unknown) => sent.push(msg),
    }) as any;

  it("re-sends the current selection with points on a region -> points upgrade", async () => {
    vi.stubGlobal("HTMLElement", FakeHTMLElement);
    const sent: any[] = [];
    const model = makeModel(makePlotEl(), sent);

    await requestPlotlyEvents(model, [{ name: "plotly_selected", payload: "region" }]);
    expect(sent).toHaveLength(1);
    expect(sent[0]).toMatchObject({
      shinywidgets: "event",
      event: "plotly_selected",
      range: { x: [1, 3], y: [4, 6] },
    });
    expect("points" in sent[0]).toBe(false);

    await requestPlotlyEvents(model, [{ name: "plotly_selected", payload: "points" }]);
    expect(sent).toHaveLength(2);
    expect(sent[1]).toMatchObject({
      shinywidgets: "event",
      event: "plotly_selected",
      range: { x: [1, 3], y: [4, 6] },
      points: [
        { trace_index: 0, point_index: 0, customdata: "a" },
        { trace_index: 0, point_index: 2, customdata: "c" },
      ],
    });
  });

  it("doesn't re-seed a bound view for an unchanged request", async () => {
    vi.stubGlobal("HTMLElement", FakeHTMLElement);
    const sent: any[] = [];
    const model = makeModel(makePlotEl(), sent);

    await requestPlotlyEvents(model, [{ name: "plotly_selected", payload: "points" }]);
    expect(sent).toHaveLength(1);
    await requestPlotlyEvents(model, [{ name: "plotly_selected", payload: "points" }]);
    expect(sent).toHaveLength(1);
  });
});

describe("selectionSeed slimming", () => {
  const plotEl: any = {
    data: [
      {
        x: [1, 2, 3],
        y: [4, 5, 6],
        customdata: ["a", "b", "c"],
        selectedpoints: [0, 2],
      },
    ],
    _fullLayout: { selections: [{ xref: "x", yref: "y", x0: 1, x1: 3, y0: 4, y1: 6 }] },
  };

  it("sends slim points plus the region when points requested", () => {
    const out = selectionSeed(plotEl, true);
    expect(out.points).toEqual([
      { trace_index: 0, point_index: 0, customdata: "a" },
      { trace_index: 0, point_index: 2, customdata: "c" },
    ]);
    expect(out.range).toEqual({ x: [1, 3], y: [4, 6] });
  });

  it("sends only the region when points are not requested", () => {
    const out = selectionSeed(plotEl, false);
    expect("points" in out).toBe(false);
    expect(out.range).toEqual({ x: [1, 3], y: [4, 6] });
  });

  it("doesn't traverse selectedpoints on the region-only path", () => {
    const trace: any = {
      x: [1, 2, 3],
      y: [4, 5, 6],
      get selectedpoints(): number[] {
        throw new Error("selectedpoints should not be read");
      },
    };
    const el: any = { data: [trace], _fullLayout: plotEl._fullLayout };
    expect(selectionSeed(el, false)).toEqual({ range: { x: [1, 3], y: [4, 6] } });
    // No region and no data scan means nothing was selected
    expect(selectionSeed({ data: [trace] } as any, false)).toEqual({});
  });
});
