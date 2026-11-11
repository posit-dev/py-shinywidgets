import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HOVER_THROTTLE_MS, throttleLeadTrail } from "./plotly";

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
