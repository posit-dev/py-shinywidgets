import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { isMuteRequest, messageWithinLimit, setMaxClientMessageBytes, ShinyComm } from "./comm";

describe("messageWithinLimit", () => {
  afterEach(() => setMaxClientMessageBytes(16 * 1024 * 1024));

  it("accepts messages under the limit", () => {
    setMaxClientMessageBytes(256);
    expect(messageWithinLimit("x".repeat(99))).toBe(true);
  });

  it("measures the escaped wire form, not the raw message", () => {
    // Both raw messages fit a 300-byte limit, but the quote-dense one's
    // JSON-escaped form (each " becomes \") plus the update envelope
    // pushes the actual frame over it
    setMaxClientMessageBytes(300);
    expect(messageWithinLimit("x".repeat(100))).toBe(true);
    expect(messageWithinLimit('"'.repeat(100))).toBe(false);
  });

  it("rejects messages over the limit and logs the size and workaround", () => {
    setMaxClientMessageBytes(10);
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(messageWithinLimit("x".repeat(11), "my-model-id")).toBe(false);
    expect(spy).toHaveBeenCalledOnce();
    expect(spy.mock.calls[0][0]).toContain("my-model-id");
    expect(spy.mock.calls[0][0]).toContain("--ws-max-size");
    spy.mockRestore();
  });

  it("measures multibyte characters by bytes, not chars", () => {
    setMaxClientMessageBytes(4);
    // 2 chars, 6 bytes
    expect(messageWithinLimit("€€")).toBe(false);
  });

  it("shows the user a sticky error notification when Shiny is present", () => {
    setMaxClientMessageBytes(10);
    const show = vi.fn();
    vi.stubGlobal("Shiny", { notifications: { show } });
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(messageWithinLimit("x".repeat(11), "w1")).toBe(false);
    expect(show).toHaveBeenCalledOnce();
    expect(show.mock.calls[0][0]).toMatchObject({
      id: "shinywidgets-oversized-w1",
      type: "error",
      duration: null,
    });
    spy.mockRestore();
    vi.unstubAllGlobals();
  });

  it("re-notifies on repeat drops (Shiny replaces the same-id notification)", () => {
    setMaxClientMessageBytes(10);
    const show = vi.fn();
    vi.stubGlobal("Shiny", { notifications: { show } });
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(messageWithinLimit("x".repeat(11), "w1")).toBe(false);
    expect(messageWithinLimit("x".repeat(11), "w1")).toBe(false);
    expect(show).toHaveBeenCalledTimes(2);
    spy.mockRestore();
    vi.unstubAllGlobals();
  });

  it("does not require Shiny to be present", () => {
    setMaxClientMessageBytes(10);
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(messageWithinLimit("x".repeat(11), "w-no-shiny")).toBe(false);
    spy.mockRestore();
  });
});

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

  // ipywidgets' remove_buffers() deletes a top-level binary trait from the
  // state, so it shows up only in buffer_paths
  it("drops a muted binary trait even when the update's JSON traits are all unmuted", () => {
    const comm = new ShinyComm("m6");
    comm.setMutedTraits(["img"]);
    const img = new Uint8Array([1, 2]).buffer;
    const other = new Uint8Array([9]).buffer;

    comm.send(
      {
        method: "update",
        state: { light: 1 },
        buffer_paths: [["img"], ["other"]],
      },
      {},
      {},
      [img, other],
    );

    const [msg] = sentMessages(setInputValue);
    expect(msg.content.data.state).toEqual({ light: 1 });
    expect(msg.content.data.buffer_paths).toEqual([["other"]]);
    expect(msg.buffers).toHaveLength(1);
    expect(atob(msg.buffers[0])).toBe(String.fromCharCode(9));
  });

  it("doesn't send an update that only sets a muted binary trait, and reports idle", () => {
    const comm = new ShinyComm("m7");
    comm.setMutedTraits(["img"]);
    const status = vi.fn();

    comm.send(
      { method: "update", state: {}, buffer_paths: [["img"]] },
      { iopub: { status } },
      {},
      [new Uint8Array([1]).buffer],
    );

    expect(setInputValue).not.toHaveBeenCalled();
    vi.runAllTimers();
    expect(status).toHaveBeenCalledOnce();
  });

  it("still sends an unmuted binary trait when the update's JSON traits are all muted", () => {
    const comm = new ShinyComm("m8");
    comm.setMutedTraits(["clicked"]);
    const img = new Uint8Array([7]).buffer;

    comm.send(
      { method: "update", state: { clicked: 3 }, buffer_paths: [["img"]] },
      {},
      {},
      [img],
    );

    const [msg] = sentMessages(setInputValue);
    expect(msg.content.data.state).toEqual({});
    expect(msg.content.data.buffer_paths).toEqual([["img"]]);
    expect(atob(msg.buffers[0])).toBe(String.fromCharCode(7));
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
