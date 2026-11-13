import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { isMuteRequest, ShinyComm } from "./comm";

describe("isMuteRequest", () => {
  it("recognizes the request render_widget_base sends", () => {
    expect(isMuteRequest({ shinywidgets: "mute", traits: ["a"] })).toBe(true);
  });

  it("rejects other custom messages", () => {
    expect(isMuteRequest({ shinywidgets: "bind", events: [] })).toBe(false);
    expect(isMuteRequest({ shinywidgets: "mute" })).toBe(false);
    expect(isMuteRequest(undefined)).toBe(false);
  });
});

// What the comm handed to Shiny for the server, parsed
function sentMessages(setInputValue: ReturnType<typeof vi.fn>): any[] {
  return setInputValue.mock.calls.map(([, msg_txt]) => JSON.parse(msg_txt as string));
}

describe("ShinyComm muted traits", () => {
  let setInputValue: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    setInputValue = vi.fn();
    vi.stubGlobal("Shiny", { setInputValue });
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("doesn't send an update that only sets a muted trait, and reports idle", () => {
    const comm = new ShinyComm("m1");
    comm.setMutedTraits(["heavy"]);
    const status = vi.fn();

    comm.send(
      { method: "update", state: { heavy: [1, 2, 3] }, buffer_paths: [] },
      { iopub: { status } },
    );

    expect(setInputValue).not.toHaveBeenCalled();
    // ipywidgets holds later changes until the in-flight message reports
    // idle; nothing will ack a message that was never sent
    vi.runAllTimers();
    expect(status).toHaveBeenCalledOnce();
    expect(status.mock.calls[0][0].content.execution_state).toBe("idle");
  });

  it("sends the other traits of an update that also sets a muted one", () => {
    const comm = new ShinyComm("m2");
    comm.setMutedTraits(["heavy"]);

    comm.send(
      { method: "update", state: { heavy: [1, 2, 3], light: 1 }, buffer_paths: [] },
      {},
    );

    const [msg] = sentMessages(setInputValue);
    expect(msg.content.data.state).toEqual({ light: 1 });
  });

  it("drops a muted trait's binary buffers along with it", () => {
    const comm = new ShinyComm("m3");
    comm.setMutedTraits(["heavy"]);
    const heavy = new Uint8Array([1, 2, 3]).buffer;
    const light = new Uint8Array([9]).buffer;

    comm.send(
      {
        method: "update",
        state: { heavy: { value: null }, light: { value: null } },
        buffer_paths: [["heavy", "value"], ["light", "value"]],
      },
      {},
      {},
      [heavy, light],
    );

    const [msg] = sentMessages(setInputValue);
    expect(msg.content.data.state).toEqual({ light: { value: null } });
    expect(msg.content.data.buffer_paths).toEqual([["light", "value"]]);
    expect(msg.buffers).toHaveLength(1);
    expect(atob(msg.buffers[0])).toBe(String.fromCharCode(9));
  });

  it("leaves custom messages alone, even ones that mention a muted trait", () => {
    const comm = new ShinyComm("m4");
    comm.setMutedTraits(["heavy"]);

    comm.send({ method: "custom", content: { heavy: 1 } }, {});

    const [msg] = sentMessages(setInputValue);
    expect(msg.content.data).toEqual({ method: "custom", content: { heavy: 1 } });
  });

  it("sends the trait again once it is no longer muted", () => {
    const comm = new ShinyComm("m5");
    comm.setMutedTraits(["heavy"]);
    comm.setMutedTraits([]);

    comm.send({ method: "update", state: { heavy: [1] }, buffer_paths: [] }, {});

    const [msg] = sentMessages(setInputValue);
    expect(msg.content.data.state).toEqual({ heavy: [1] });
  });
});
