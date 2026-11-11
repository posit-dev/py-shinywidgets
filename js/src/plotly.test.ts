import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  HOVER_THROTTLE_MS,
  eventPayload,
  throttleLeadTrail,
  visibilitySeed,
} from "./plotly";

describe("throttleLeadTrail", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("forwards the first call immediately (leading edge)", () => {
    const fn = vi.fn();
    const throttled = throttleLeadTrail(fn, HOVER_THROTTLE_MS);
    throttled("a");
    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenLastCalledWith("a");
  });

  it("collapses calls inside the window and forwards the last (trailing edge)", () => {
    const fn = vi.fn();
    const throttled = throttleLeadTrail(fn, HOVER_THROTTLE_MS);
    throttled("a"); // leading
    vi.advanceTimersByTime(50);
    throttled("b");
    vi.advanceTimersByTime(50);
    throttled("c");
    expect(fn).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(HOVER_THROTTLE_MS);
    expect(fn).toHaveBeenCalledTimes(2);
    expect(fn).toHaveBeenLastCalledWith("c");
  });

  it("doesn't fire a trailing call when nothing was suppressed", () => {
    const fn = vi.fn();
    const throttled = throttleLeadTrail(fn, HOVER_THROTTLE_MS);
    throttled("a");
    vi.advanceTimersByTime(HOVER_THROTTLE_MS * 2);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("treats a call after a quiet window as a new leading edge", () => {
    const fn = vi.fn();
    const throttled = throttleLeadTrail(fn, HOVER_THROTTLE_MS);
    throttled("a");
    vi.advanceTimersByTime(HOVER_THROTTLE_MS);
    throttled("b");
    expect(fn).toHaveBeenCalledTimes(2);
    expect(fn).toHaveBeenLastCalledWith("b");
  });

  it("cancel() drops a pending trailing call", () => {
    const fn = vi.fn();
    const throttled = throttleLeadTrail(fn, HOVER_THROTTLE_MS);
    throttled("a");
    throttled("b");
    throttled.cancel();
    vi.advanceTimersByTime(HOVER_THROTTLE_MS * 2);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("drops a stale pending value when its timer fires late", () => {
    const fn = vi.fn();
    const throttled = throttleLeadTrail(fn, HOVER_THROTTLE_MS);
    const t0 = Date.now(); // fake timers start at the real time, not epoch 0
    throttled("a"); // t0, leading
    vi.setSystemTime(t0 + 50);
    const timeoutSpy = vi.spyOn(globalThis, "setTimeout");
    throttled("b"); // pending, trailing timer due at t0+250
    const trailing = timeoutSpy.mock.calls[0][0] as () => void;
    // The timer runs late (event-loop contention), after the window closed
    vi.setSystemTime(t0 + 300);
    throttled("c"); // new leading edge
    trailing(); // the overdue timer finally runs: must not publish stale "b"
    expect(fn.mock.calls.map((c) => c[0])).toEqual(["a", "c"]);
    timeoutSpy.mockRestore();
  });

  it("cancel()ed throttle forwards the next call as a new leading edge", () => {
    const fn = vi.fn();
    const throttled = throttleLeadTrail(fn, HOVER_THROTTLE_MS);
    throttled("a");
    throttled("b");
    throttled.cancel();
    throttled("c");
    expect(fn).toHaveBeenCalledTimes(2);
    expect(fn).toHaveBeenLastCalledWith("c");
  });
});

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
  });
});
