import { useCallback, useEffect, useRef, useState } from "react";

export type SaveStatus = "idle" | "pending" | "saving" | "saved" | "error";

/** `keepalive` is true when the page may be going away (the request must outlive it). */
export type SaveFn = (value: string, options: { keepalive: boolean }) => Promise<void>;

/**
 * Debounced autosave. Call `schedule(value)` on every change; the latest value is saved
 * `delayMs` after the last change. Saves run one at a time, in order. A pending change
 * is flushed (with keepalive) on unmount and when the page is hidden or unloaded, so
 * a refresh right after typing does not lose the last keystrokes.
 */
export function useAutosave(save: SaveFn, delayMs = 1000) {
  const [status, setStatus] = useState<SaveStatus>("idle");
  const saveRef = useRef(save);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pending = useRef<string | null>(null);
  const chain = useRef<Promise<void>>(Promise.resolve());

  useEffect(() => {
    saveRef.current = save;
  }, [save]);

  const flush = useCallback((keepalive: boolean) => {
    if (timer.current !== null) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    const value = pending.current;
    if (value === null) return;
    pending.current = null;
    setStatus("saving");
    chain.current = chain.current.then(async () => {
      try {
        await saveRef.current(value, { keepalive });
        setStatus(pending.current === null ? "saved" : "pending");
      } catch {
        // The next change schedules a new save with the newer text.
        setStatus("error");
      }
    });
  }, []);

  const schedule = useCallback(
    (value: string) => {
      pending.current = value;
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

  return { status, schedule };
}
