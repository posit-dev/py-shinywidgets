import { describe, expect, it } from "vitest";
import { eventPayload, visibilitySeed } from "./plotly";

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
