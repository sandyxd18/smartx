import { useEffect, useRef, useState } from "react";

// The Surfer web build from `make surfer` (frontend/public/surfer, pinned in the Makefile).
// "#dev" makes Surfer's index.html skip registering its service worker.
const SURFER_SRC = "/surfer/index.html#dev";
const VERSION_FILE = "/surfer/SURFER_VERSION";
const READY_POLL_MS = 100;
const READY_TIMEOUT_MS = 20_000;

/** Surfer's index.html puts `inject_message` on its window once the WASM module is up. */
function isSurferReady(win: Window | null | undefined): win is Window {
  return !!win && "inject_message" in win && typeof win.inject_message === "function";
}

type Install = "checking" | "installed" | "missing";
type Viewer = "loading" | "ready" | "failed";

function absolute(url: string): string {
  return new URL(url, window.location.origin).href;
}

/** Ask Surfer to (re)load a waveform. Documented in surfer/integration.js. */
function loadInSurfer(win: Window, url: string) {
  win.postMessage({ command: "LoadUrl", url: absolute(url) }, window.location.origin);
}

/**
 * Embedded Surfer waveform viewer for an .fst/.vcd artifact URL, with a download
 * link as fallback. All Surfer specifics live here (see DECISIONS D10).
 */
export function WaveView({ url }: { url: string }) {
  const [install, setInstall] = useState<Install>("checking");
  const [viewer, setViewer] = useState<Viewer>("loading");
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const urlRef = useRef(url);
  const sentUrl = useRef<string | null>(null);
  const poll = useRef<ReturnType<typeof setInterval> | null>(null);

  function send(win: Window, target: string) {
    sentUrl.current = target;
    loadInSurfer(win, target);
  }

  useEffect(() => {
    let cancelled = false;
    // Vite serves index.html for unknown paths, so check the content, not the status.
    fetch(new Request(absolute(VERSION_FILE)))
      .then((r) => (r.ok ? r.text() : ""))
      .then(
        (text) => {
          if (!cancelled) setInstall(/^v\d/.test(text.trim()) ? "installed" : "missing");
        },
        () => {
          if (!cancelled) setInstall("missing");
        },
      );
    return () => {
      cancelled = true;
    };
  }, []);

  // A newer run replaces the waveform in the running viewer instead of reloading it.
  useEffect(() => {
    urlRef.current = url;
    const win = iframeRef.current?.contentWindow;
    // Only for a different file: becoming "ready" already loaded the current one.
    if (viewer === "ready" && win && sentUrl.current !== url) send(win, url);
  }, [url, viewer]);

  useEffect(
    () => () => {
      if (poll.current !== null) clearInterval(poll.current);
    },
    [],
  );

  function handleLoad() {
    // The page has loaded, but Surfer's WASM starts asynchronously after that. Messages
    // sent before `inject_message` exists are lost, so wait for it (same origin).
    if (poll.current !== null) clearInterval(poll.current);
    let waited = 0;
    const id = setInterval(() => {
      const win = iframeRef.current?.contentWindow;
      const ready = isSurferReady(win);
      waited += READY_POLL_MS;
      if (!ready && waited < READY_TIMEOUT_MS) return;
      clearInterval(id);
      poll.current = null;
      if (ready) {
        send(win, urlRef.current);
        setViewer("ready");
      } else {
        setViewer("failed");
      }
    }, READY_POLL_MS);
    poll.current = id;
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-2">
      <div className="flex items-center gap-3 text-xs text-slate-500">
        <a href={url} download className="text-blue-700 underline">
          Unduh .fst
        </a>
        <span>untuk GTKWave atau Surfer desktop</span>
        {install === "installed" && viewer === "loading" && <span>· Memuat viewer…</span>}
      </div>
      {install === "missing" && (
        <p className="text-sm text-slate-600">
          Viewer waveform belum terpasang. Jalankan <code>make surfer</code> sekali (±5 menit),
          lalu muat ulang halaman.
        </p>
      )}
      {viewer === "failed" && (
        <p className="text-sm text-red-700">
          Viewer waveform gagal dimuat. Unduh file .fst dan buka di GTKWave atau Surfer desktop.
        </p>
      )}
      {install === "installed" && viewer !== "failed" && (
        <iframe
          ref={iframeRef}
          title="Waveform (Surfer)"
          src={SURFER_SRC}
          onLoad={handleLoad}
          className="min-h-0 w-full flex-1 rounded border border-slate-200"
        />
      )}
    </div>
  );
}
