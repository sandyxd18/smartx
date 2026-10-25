import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FakeEventSource } from "../test/fakeEventSource";
import { useRunEvents } from "./useRunEvents";

describe("useRunEvents", () => {
  it("does nothing without a run", () => {
    const { result } = renderHook(() => useRunEvents(null));
    expect(result.current).toEqual({ lines: [], status: null });
    expect(FakeEventSource.instances).toHaveLength(0);
  });

  it("does not duplicate lines when EventSource reconnects", () => {
    const { result } = renderHook(() => useRunEvents("r1"));
    const source = FakeEventSource.last();

    source.emit("open");
    source.emit("log", { line: "a" });
    // Connection dropped; the browser reconnects and the server replays from the start.
    source.emit("open");
    source.emit("log", { line: "a" });
    source.emit("log", { line: "b" });

    expect(result.current.lines).toEqual(["a", "b"]);
  });

  it("starts fresh when switching runs and closes the old stream", () => {
    const { result, rerender } = renderHook(({ id }) => useRunEvents(id), {
      initialProps: { id: "r1" },
    });
    const first = FakeEventSource.last();
    first.emit("log", { line: "from r1" });
    first.emit("status", { status: "running" });

    rerender({ id: "r2" });

    expect(first.closed).toBe(true);
    expect(FakeEventSource.last().url).toBe("/api/runs/r2/events");
    expect(result.current).toEqual({ lines: [], status: null });
  });

  it("closes the stream on a final status", () => {
    const { result } = renderHook(() => useRunEvents("r1"));
    const source = FakeEventSource.last();

    source.emit("status", { status: "running" });
    expect(source.closed).toBe(false);
    source.emit("status", { status: "timeout" });

    expect(source.closed).toBe(true);
    expect(result.current.status).toBe("timeout");
  });
});
