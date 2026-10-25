import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockFetch } from "../test/mockFetch";
import { WaveView } from "./WaveView";

const URL_A = "/api/runs/aaaa/files/build/sim_build/counter4.fst";
const URL_B = "/api/runs/bbbb/files/build/sim_build/counter4.fst";

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
});
afterEach(() => {
  vi.useRealTimers();
});

function surferInstalled() {
  mockFetch({ "GET /surfer/SURFER_VERSION": () => new Response("v0.7.0\n") });
}

async function frame(): Promise<HTMLIFrameElement> {
  return screen.findByTitle<HTMLIFrameElement>("Waveform (Surfer)");
}

/** Pretend the Surfer WASM finished loading inside the iframe. */
function surferReady(iframe: HTMLIFrameElement) {
  const win = iframe.contentWindow as Window & { inject_message?: unknown };
  win.inject_message = vi.fn();
  const post = vi.spyOn(win, "postMessage").mockImplementation(() => undefined);
  return post;
}

describe("WaveView", () => {
  it("always offers the .fst download", () => {
    surferInstalled();
    render(<WaveView url={URL_A} />);
    expect(screen.getByRole("link", { name: /Unduh \.fst/ })).toHaveAttribute("href", URL_A);
  });

  it("loads the waveform once Surfer is ready", async () => {
    surferInstalled();
    render(<WaveView url={URL_A} />);
    const iframe = await frame();
    expect(iframe.getAttribute("src")).toBe("/surfer/index.html#dev");

    fireEvent.load(iframe);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500); // WASM still loading: nothing sent
    });
    const post = surferReady(iframe);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    expect(post).toHaveBeenCalledTimes(1);
    expect(post).toHaveBeenCalledWith(
      { command: "LoadUrl", url: `${window.location.origin}${URL_A}` },
      window.location.origin,
    );
  });

  it("loads the new waveform when a new run finishes", async () => {
    surferInstalled();
    const { rerender } = render(<WaveView url={URL_A} />);
    const iframe = await frame();
    const post = surferReady(iframe);
    fireEvent.load(iframe);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    rerender(<WaveView url={URL_B} />);

    expect(post).toHaveBeenLastCalledWith(
      { command: "LoadUrl", url: `${window.location.origin}${URL_B}` },
      window.location.origin,
    );
    expect(await frame()).toBe(iframe); // the viewer is reused, not reloaded
  });

  it("falls back to the download when Surfer never becomes ready", async () => {
    surferInstalled();
    render(<WaveView url={URL_A} />);
    fireEvent.load(await frame());

    await act(async () => {
      await vi.advanceTimersByTimeAsync(20_000);
    });

    expect(screen.getByText(/Viewer waveform gagal dimuat/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Unduh \.fst/ })).toBeInTheDocument();
  });

  it("explains how to install Surfer when it is missing", async () => {
    // Vite answers unknown paths with index.html (200), so the content is what counts.
    mockFetch({ "GET /surfer/SURFER_VERSION": () => new Response("<!doctype html>") });
    render(<WaveView url={URL_A} />);

    expect(await screen.findByText(/make surfer/)).toBeInTheDocument();
    expect(screen.queryByTitle("Waveform (Surfer)")).not.toBeInTheDocument();
  });
});
