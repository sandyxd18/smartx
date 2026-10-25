import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import type { Health, Run } from "../api/client";
import { routes } from "../routes";
import { FakeEventSource } from "../test/fakeEventSource";
import { mockFetch } from "../test/mockFetch";

const HEALTHY: Health = {
  status: "ok",
  version: "0.1.0",
  docker: { available: true, server_version: "29.8.2", error: null },
};

function run(overrides: Partial<Run> = {}): Run {
  return {
    id: "3d2b1bde0c1946ed91b904bf4e735ed3",
    project_id: null,
    kind: "echo",
    status: "queued",
    params: {},
    result: null,
    tool_versions: null,
    created_at: "2026-10-25T10:00:00Z",
    started_at: null,
    finished_at: null,
    exit_code: null,
    error: null,
    ...overrides,
  };
}

function renderDashboard() {
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/"] })} />);
}

describe("Dashboard health", () => {
  it("shows backend version and Docker status", async () => {
    mockFetch({ "GET /api/health": () => HEALTHY });
    renderDashboard();

    expect(await screen.findByText("OK (versi 0.1.0)")).toBeInTheDocument();
    expect(screen.getByText("Terdeteksi (versi 29.8.2)")).toBeInTheDocument();
  });

  it("explains when Docker is down", async () => {
    mockFetch({
      "GET /api/health": () => ({
        ...HEALTHY,
        docker: { available: false, server_version: null, error: "pipe tidak ada" },
      }),
    });
    renderDashboard();

    expect(await screen.findByText("Tidak terdeteksi: pipe tidak ada")).toBeInTheDocument();
  });

  it("explains when the backend is unreachable", async () => {
    mockFetch({
      "GET /api/health": () => {
        throw new TypeError("Failed to fetch");
      },
    });
    renderDashboard();

    expect(await screen.findByText("Backend tidak bisa dihubungi.")).toBeInTheDocument();
  });

  it("treats a proxy 502 as unreachable and can check again", async () => {
    let backendUp = false;
    mockFetch({
      "GET /api/health": () =>
        backendUp ? HEALTHY : new Response("proxy error", { status: 502 }),
    });
    renderDashboard();

    expect(
      await screen.findByText("Backend tidak bisa dihubungi (HTTP 502)."),
    ).toBeInTheDocument();

    backendUp = true;
    await userEvent.click(screen.getByRole("button", { name: "Periksa lagi" }));
    expect(await screen.findByText("OK (versi 0.1.0)")).toBeInTheDocument();
  });
});

describe("Echo job", () => {
  it("runs the job and streams its log live", async () => {
    const created = run();
    const fetch = mockFetch({
      "GET /api/health": () => HEALTHY,
      "POST /api/runs": () => Response.json(created, { status: 201 }),
    });
    renderDashboard();

    await userEvent.click(screen.getByRole("button", { name: "Jalankan echo job" }));

    const source = FakeEventSource.last();
    expect(source.url).toBe(`/api/runs/${created.id}/events`);
    const post = fetch.mock.calls.map(([req]) => req).find((req) => req.method === "POST");
    expect(await post?.json()).toEqual({ kind: "echo", params: {} });

    source.emit("open");
    source.emit("status", { status: "running" });
    expect(screen.getByText("Berjalan")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Jalankan echo job" })).toBeDisabled();

    source.emit("log", { line: "Yosys 0.70+219" });
    expect(screen.getByLabelText("Log run")).toHaveTextContent("Yosys 0.70+219");

    source.emit("status", { status: "succeeded" });
    expect(screen.getByText("Berhasil")).toBeInTheDocument();
    expect(source.closed).toBe(true);
    expect(screen.getByRole("button", { name: "Jalankan echo job" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Batalkan" })).not.toBeInTheDocument();
  });

  it("can hold the job and cancel it", async () => {
    const created = run();
    const fetch = mockFetch({
      "GET /api/health": () => HEALTHY,
      "POST /api/runs": () => Response.json(created, { status: 201 }),
      [`POST /api/runs/${created.id}/cancel`]: () =>
        Response.json(run({ status: "running" }), { status: 202 }),
    });
    renderDashboard();

    await userEvent.click(screen.getByLabelText(/Tahan 60 detik/));
    await userEvent.click(screen.getByRole("button", { name: "Jalankan echo job" }));
    const source = FakeEventSource.last();
    source.emit("status", { status: "running" });

    await userEvent.click(screen.getByRole("button", { name: "Batalkan" }));
    const posts = fetch.mock.calls.map(([req]) => req).filter((req) => req.method === "POST");
    expect(await posts[0]?.json()).toEqual({ kind: "echo", params: { sleep_s: 60 } });
    expect(new URL(posts[1]!.url).pathname).toBe(`/api/runs/${created.id}/cancel`);

    source.emit("status", { status: "cancelled" });
    expect(within(screen.getByText(/^Run/).parentElement!).getByText("Dibatalkan")).toBeVisible();
  });
});
