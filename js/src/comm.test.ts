import { afterEach, describe, expect, it, vi } from "vitest";
import { messageWithinLimit, setMaxClientMessageBytes } from "./comm";

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
});
