import { useCallback, useEffect, useRef, useState } from "react";

export type SaveStatus = "idle" | "pending" | "saving" | "saved" | "error";

/** `keepalive` is true when the page may be going away (the request must outlive it). */
export type SaveFn<T = string> = (value: T, options: { keepalive: boolean }) => Promise<void>;

/**
 * Debounced autosave. Call `schedule(value)` on every change; the latest value is saved
 * `delayMs` after the last change. Saves run one at a time, in order. A pending change
 * is flushed (with keepalive) on unmount and when the page is hidden or unloaded, so
 * a refresh right after typing does not lose the last keystrokes. `settle()` saves a
 * pending change right away and resolves when every save has finished: await it before
 * anything that must see the stored text (switching files, renaming, deleting).
 */
export function useAutosave<T = string>(save: SaveFn<T>, delayMs = 1000) {
  const [status, setStatus] = useState<SaveStatus>("idle");
  const saveRef = useRef(save);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Boxed, so any T (even null) can be pending.
  const pending = useRef<{ value: T } | null>(null);
  const chain = useRef<Promise<void>>(Promise.resolve());

  useEffect(() => {
    saveRef.current = save;
  }, [save]);

  const flush = useCallback((keepalive: boolean) => {
    if (timer.current !== null) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    const box = pending.current;
    if (box === null) return;
    pending.current = null;
    setStatus("saving");
    chain.current = chain.current.then(async () => {
      try {
        await saveRef.current(box.value, { keepalive });
        setStatus(pending.current === null ? "saved" : "pending");
      } catch {
        // The next change schedules a new save with the newer text.
        setStatus("error");
      }
    });
  }, []);

  const schedule = useCallback(
    (value: T) => {
      pending.current = { value };
      setStatus("pending");
      if (timer.current !== null) clearTimeout(timer.current);
      timer.current = setTimeout(() => flush(false), delayMs);
    },
    [delayMs, flush],
  );

  useEffect(() => {
    const onHide = () => flush(true);
    const onVisibility = () => {
      if (document.visibilityState === "hidden") flush(true);
    };
    window.addEventListener("pagehide", onHide);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.removeEventListener("pagehide", onHide);
      document.removeEventListener("visibilitychange", onVisibility);
      flush(true); // leaving the page inside the app
    };
  }, [flush]);

  const settle = useCallback(async () => {
    flush(false);
    await chain.current;
  }, [flush]);

  return { status, schedule, settle };
}
