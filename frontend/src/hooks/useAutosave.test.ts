import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAutosave, type SaveFn } from "./useAutosave";

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

function setup(save: SaveFn = vi.fn<SaveFn>(() => Promise.resolve())) {
  const hook = renderHook(() => useAutosave(save, 1000));
  return { ...hook, save };
}

/** Let the save promise chain settle (fake timers do not run microtasks by themselves). */
async function settle() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
}

describe("useAutosave", () => {
  it("is idle until something changes", () => {
    const { result, save } = setup();
    expect(result.current.status).toBe("idle");
    expect(save).not.toHaveBeenCalled();
  });

  it("saves once, 1 second after the last change, with the latest value", async () => {
    const { result, save } = setup();

    act(() => result.current.schedule("a"));
    act(() => {
      vi.advanceTimersByTime(600);
    });
    act(() => result.current.schedule("ab"));
    expect(result.current.status).toBe("pending");

    act(() => {
      vi.advanceTimersByTime(999);
    });
    expect(save).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(1);
    });
    await settle();

    expect(save).toHaveBeenCalledTimes(1);
    expect(save).toHaveBeenCalledWith("ab", { keepalive: false });
    expect(result.current.status).toBe("saved");
  });

  it("runs saves one after another so an old draft never lands last", async () => {
    const order: string[] = [];
    const resolvers: (() => void)[] = [];
    const save = vi.fn<SaveFn>(
      (value) =>
        new Promise<void>((resolve) => {
          resolvers.push(() => {
            order.push(value);
            resolve();
          });
        }),
    );
    const { result } = setup(save);

    act(() => result.current.schedule("first"));
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    await settle();
    act(() => result.current.schedule("second"));
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    await settle();

    // The second save waits for the first one.
    expect(save).toHaveBeenCalledTimes(1);
    resolvers[0]!();
    await settle();
    expect(save).toHaveBeenCalledTimes(2);
    resolvers[1]!();
    await settle();

    expect(order).toEqual(["first", "second"]);
    expect(result.current.status).toBe("saved");
  });

  it("reports a failed save and retries on the next change", async () => {
    const save = vi
      .fn<SaveFn>()
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValue(undefined);
    const { result } = setup(save);

    act(() => result.current.schedule("a"));
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    await settle();
    expect(result.current.status).toBe("error");

    act(() => result.current.schedule("ab"));
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    await settle();
    expect(save).toHaveBeenLastCalledWith("ab", { keepalive: false });
    expect(result.current.status).toBe("saved");
  });

  it("flushes a pending change on unmount, with keepalive", async () => {
    const { result, save, unmount } = setup();

    act(() => result.current.schedule("unsaved"));
    unmount();
    await settle();

    expect(save).toHaveBeenCalledWith("unsaved", { keepalive: true });
  });

  it("flushes a pending change when the page is hidden or unloaded", async () => {
    const { result, save } = setup();

    act(() => result.current.schedule("before reload"));
    act(() => {
      window.dispatchEvent(new Event("pagehide"));
    });
    await settle();

    expect(save).toHaveBeenCalledWith("before reload", { keepalive: true });
    // Nothing left for the timer to do.
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    await settle();
    expect(save).toHaveBeenCalledTimes(1);
  });

  it("does nothing on unmount when everything is saved", async () => {
    const { result, save, unmount } = setup();
    act(() => result.current.schedule("a"));
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    await settle();

    unmount();
    await settle();

    expect(save).toHaveBeenCalledTimes(1);
  });
});
