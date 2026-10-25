import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { ExerciseDetail, ExerciseRun, GradeResult } from "../api/client";
import { routes } from "../routes";
import { FakeEventSource } from "../test/fakeEventSource";
import { mockFetch } from "../test/mockFetch";

vi.mock("../components/CodeEditor", async () => ({
  CodeEditor: (await import("../test/fakeCodeEditor")).FakeCodeEditor,
}));

// The page is a lazy route. Its first import (Markdown, etc.) can take longer than the
// default findBy timeout on a busy machine, so load it once before the tests start.
beforeAll(async () => {
  await import("./ExercisePage");
});

const STARTER = "module counter4(input clk, input rst, input en, output reg [3:0] q);\nendmodule\n";
const RUN_ID = "3d2b1bde0c1946ed91b904bf4e735ed3";

function detail(overrides: Partial<ExerciseDetail> = {}): ExerciseDetail {
  return {
    id: "counter-4bit",
    title: "Counter 4-bit",
    step: 1,
    level: 1,
    topics: ["sequential"],
    order: null,
    requires: [],
    status: "not_started",
    attempts: 0,
    toplevel: "counter4",
    language: "verilog",
    statement: "# Counter 4-bit\n\n| Port | Arah |\n|---|---|\n| `clk` | input |\n",
    starter: STARTER,
    code: STARTER,
    hints: [],
    hints_total: 2,
    solution_available: false,
    solution_unlock_attempts: 5,
    last_run: null,
    ...overrides,
  };
}

function grade(overrides: Partial<GradeResult> = {}): GradeResult {
  return {
    exercise_id: "counter-4bit",
    status: "pass",
    simulator: "icarus",
    tests: [
      { name: "reset_sets_zero", passed: true, message: "", sim_time_ns: 10 },
      { name: "counts_and_wraps", passed: true, message: "", sim_time_ns: 200 },
      { name: "random_stimulus", passed: true, message: "", sim_time_ns: 900 },
    ],
    diagnostics: [],
    log: "cocotb log line",
    wave_file: "build/sim_build/counter4.fst",
    wave_url: `/api/runs/${RUN_ID}/files/build/sim_build/counter4.fst`,
    ...overrides,
  };
}

function run(overrides: Partial<ExerciseRun> = {}): ExerciseRun {
  return {
    id: RUN_ID,
    project_id: null,
    kind: "grade",
    status: "succeeded",
    params: {},
    result: null,
    tool_versions: null,
    created_at: "2026-10-25T10:00:00Z",
    started_at: null,
    finished_at: null,
    exit_code: 0,
    error: null,
    grade: grade(),
    ...overrides,
  };
}

const BASE = "/api/exercises/counter-4bit";

function renderPage(routesTable: Parameters<typeof mockFetch>[0]) {
  const fetch = mockFetch(routesTable);
  render(
    <RouterProvider
      router={createMemoryRouter(routes, { initialEntries: ["/latihan/counter-4bit"] })}
    />,
  );
  return fetch;
}

async function editor(): Promise<HTMLTextAreaElement> {
  return screen.findByLabelText<HTMLTextAreaElement>("Editor kode");
}

/** Click Run and drive the SSE stream to the end; returns the POSTed body. */
async function runToEnd(fetch: ReturnType<typeof mockFetch>, finalStatus = "succeeded") {
  await userEvent.click(screen.getByRole("button", { name: /^Run/ }));
  const source = FakeEventSource.last();
  expect(source.url).toBe(`/api/runs/${RUN_ID}/events`);
  source.emit("status", { status: "running" });
  expect(screen.getByText("Menjalankan…")).toBeInTheDocument();
  source.emit("status", { status: finalStatus });
  const post = fetch.mock.calls.map(([r]) => r).find((r) => r.method === "POST");
  return (await post!.json()) as unknown;
}

describe("ExercisePage", () => {
  it("shows the statement, the code and the locked solution", async () => {
    renderPage({ [`GET ${BASE}`]: () => detail({ code: "// my code\n", attempts: 2 }) });

    expect(await editor()).toHaveValue("// my code\n");
    // The README's own "# Counter 4-bit" is dropped: one title, from exercise.yaml.
    expect(screen.getAllByRole("heading", { level: 1 }).map((h) => h.textContent)).toEqual([
      "Counter 4-bit",
    ]);
    expect(screen.getByRole("table")).toHaveTextContent("clk");
    expect(screen.getByText(/Solusi terbuka setelah lulus atau setelah 5 percobaan/)).toHaveTextContent(
      "(sekarang 2)",
    );
    expect(screen.getByRole("button", { name: "Buka petunjuk (0/2)" })).toBeInTheDocument();
  });

  it("says when the exercise does not exist", async () => {
    renderPage({
      [`GET ${BASE}`]: () => Response.json({ detail: "Soal tidak ditemukan." }, { status: 404 }),
    });
    expect(await screen.findByText("Soal tidak ditemukan.")).toBeInTheDocument();
  });

  it("runs the code and shows passing tests", async () => {
    let solved = false;
    const fetch = renderPage({
      [`GET ${BASE}`]: () =>
        solved
          ? detail({ status: "solved", attempts: 1, solution_available: true })
          : detail(),
      [`POST ${BASE}/runs`]: () => {
        solved = true;
        return Response.json(run({ status: "queued", grade: null }), { status: 201 });
      },
      [`GET ${BASE}/runs/${RUN_ID}`]: () => run(),
    });
    await userEvent.type(await editor(), "// edit");

    const body = await runToEnd(fetch);

    expect(body).toEqual({ code: `${STARTER}// edit` });
    expect(await screen.findByText("Lulus semua test (3/3)")).toBeInTheDocument();
    const tests = screen.getByRole("list", { name: "Hasil test" });
    expect(within(tests).getAllByRole("listitem")).toHaveLength(3);
    // Progress is refreshed: the solution is now available.
    expect(await screen.findByRole("button", { name: "Lihat solusi" })).toBeInTheDocument();
  });

  it("shows failing tests with their messages", async () => {
    const failing = grade({
      status: "fail",
      tests: [
        { name: "reset_sets_zero", passed: true, message: "", sim_time_ns: 0 },
        { name: "counts_and_wraps", passed: false, message: "siklus 3: q=2, seharusnya 3", sim_time_ns: 0 },
        { name: "random_stimulus", passed: false, message: "siklus 7: q=X", sim_time_ns: 0 },
      ],
    });
    const fetch = renderPage({
      [`GET ${BASE}`]: () => detail(),
      [`POST ${BASE}/runs`]: () => Response.json(run({ status: "queued", grade: null }), { status: 201 }),
      [`GET ${BASE}/runs/${RUN_ID}`]: () => run({ exit_code: 1, grade: failing }),
    });
    await editor();

    await runToEnd(fetch);

    expect(await screen.findByText("2 dari 3 test gagal")).toBeInTheDocument();
    expect(screen.getByText("siklus 3: q=2, seharusnya 3")).toBeInTheDocument();
  });

  it("marks compile errors in the editor", async () => {
    const broken = grade({
      status: "compile_error",
      tests: [],
      wave_file: null,
      wave_url: null,
      log: "/work/build/dut.v:4: syntax error",
      diagnostics: [{ line: 4, severity: "error", message: "syntax error" }],
    });
    const fetch = renderPage({
      [`GET ${BASE}`]: () => detail(),
      [`POST ${BASE}/runs`]: () => Response.json(run({ status: "queued", grade: null }), { status: 201 }),
      [`GET ${BASE}/runs/${RUN_ID}`]: () => run({ exit_code: 1, grade: broken }),
    });
    await editor();

    await runToEnd(fetch);

    expect(await screen.findByText("Kode tidak bisa dikompilasi")).toBeInTheDocument();
    expect(screen.getByText("Baris 4: syntax error")).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Penanda editor" })).toHaveTextContent(
      "error 4: syntax error",
    );
  });

  it("explains a run that failed or timed out", async () => {
    const fetch = renderPage({
      [`GET ${BASE}`]: () => detail(),
      [`POST ${BASE}/runs`]: () => Response.json(run({ status: "queued", grade: null }), { status: 201 }),
      [`GET ${BASE}/runs/${RUN_ID}`]: () =>
        run({ status: "timeout", grade: null, error: "Melebihi batas waktu 60 detik." }),
    });
    await editor();

    await runToEnd(fetch, "timeout");

    expect(await screen.findByText("Melebihi batas waktu 60 detik.")).toBeInTheDocument();
  });

  it("runs with Ctrl+Enter from the editor", async () => {
    const fetch = renderPage({
      [`GET ${BASE}`]: () => detail(),
      [`POST ${BASE}/runs`]: () => Response.json(run({ status: "queued", grade: null }), { status: 201 }),
    });
    const textarea = await editor();
    // Like Monaco right after a keystroke: the editor already holds the new text but
    // React state has not caught up yet. Ctrl+Enter must still send what is on screen.
    textarea.value = "// typed just now\n";

    textarea.focus();
    await userEvent.keyboard("{Control>}{Enter}{/Control}");

    await waitFor(() =>
      expect(fetch.mock.calls.some(([r]) => r.method === "POST")).toBe(true),
    );
    const post = fetch.mock.calls.map(([r]) => r).find((r) => r.method === "POST");
    expect(await post!.json()).toEqual({ code: "// typed just now\n" });
  });

  it("resets the code to the starter", async () => {
    renderPage({ [`GET ${BASE}`]: () => detail({ code: "// old attempt\n" }) });
    const textarea = await editor();

    await userEvent.click(screen.getByRole("button", { name: "Reset ke starter" }));

    expect(textarea).toHaveValue(STARTER);
  });

  it("shows the previous result after a reload", async () => {
    renderPage({
      [`GET ${BASE}`]: () => detail({ attempts: 1, status: "solved", last_run: run() }),
    });

    expect(await screen.findByText("Lulus semua test (3/3)")).toBeInTheDocument();
    expect(FakeEventSource.instances).toHaveLength(0); // no stream for a finished run
  });

  it("has log and waveform tabs", async () => {
    renderPage({
      [`GET ${BASE}`]: () => detail({ last_run: run() }),
      "GET /surfer/SURFER_VERSION": () => new Response("v0.7.0"),
    });
    await screen.findByText("Lulus semua test (3/3)");

    await userEvent.click(screen.getByRole("tab", { name: "Log" }));
    expect(screen.getByText("cocotb log line")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("tab", { name: "Waveform" }));
    expect(screen.getByRole("link", { name: /Unduh \.fst/ })).toHaveAttribute(
      "href",
      `/api/runs/${RUN_ID}/files/build/sim_build/counter4.fst`,
    );
    expect(await screen.findByTitle("Waveform (Surfer)")).toBeInTheDocument();
  });

  it("keeps the waveform viewer when switching tabs", async () => {
    renderPage({
      [`GET ${BASE}`]: () => detail({ last_run: run() }),
      "GET /surfer/SURFER_VERSION": () => new Response("v0.7.0"),
    });
    await screen.findByText("Lulus semua test (3/3)");
    await userEvent.click(screen.getByRole("tab", { name: "Waveform" }));
    const iframe = await screen.findByTitle("Waveform (Surfer)");

    await userEvent.click(screen.getByRole("tab", { name: "Tests" }));
    await userEvent.click(screen.getByRole("tab", { name: "Waveform" }));

    expect(screen.getByTitle("Waveform (Surfer)")).toBe(iframe);
  });

  it("says there is no waveform after a compile error", async () => {
    const broken = grade({ status: "compile_error", tests: [], wave_file: null, wave_url: null });
    renderPage({ [`GET ${BASE}`]: () => detail({ last_run: run({ grade: broken }) }) });
    await screen.findByText("Kode tidak bisa dikompilasi");

    await userEvent.click(screen.getByRole("tab", { name: "Waveform" }));

    expect(screen.getByText(/Belum ada waveform/)).toBeInTheDocument();
  });

  it("opens hints one by one", async () => {
    renderPage({
      [`GET ${BASE}`]: () => detail(),
      [`POST ${BASE}/hints/next`]: () => ({ hints: ["Pakai always @(posedge clk)."], total: 2 }),
    });
    await editor();

    await userEvent.click(screen.getByRole("button", { name: "Buka petunjuk (0/2)" }));

    expect(await screen.findByText("Pakai always @(posedge clk).")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Buka petunjuk (1/2)" })).toBeInTheDocument();
  });

  it("shows the solution once it is available", async () => {
    renderPage({
      [`GET ${BASE}`]: () => detail({ solution_available: true }),
      [`GET ${BASE}/solution`]: () => ({ code: "module counter4(/* resmi */);\nendmodule\n" }),
    });
    await editor();

    await userEvent.click(screen.getByRole("button", { name: "Lihat solusi" }));

    expect(await screen.findByText(/resmi/)).toBeInTheDocument();
  });
});

describe("ExercisePage autosave", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  function puts(fetch: ReturnType<typeof mockFetch>) {
    return fetch.mock.calls.map(([r]) => r).filter((r) => r.method === "PUT");
  }

  it("saves the draft 1 second after typing stops", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const fetch = renderPage({
      [`GET ${BASE}`]: () => detail(),
      [`PUT ${BASE}/code`]: () => new Response(null, { status: 204 }),
    });
    await user.type(await editor(), "// wip");
    expect(puts(fetch)).toHaveLength(0);
    expect(screen.getByText("Menyimpan…")).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    expect(puts(fetch)).toHaveLength(1);
    expect(await puts(fetch)[0]!.json()).toEqual({ code: `${STARTER}// wip` });
    expect(await screen.findByText("Tersimpan")).toBeInTheDocument();
  });

  it("does not save just because the page was opened", async () => {
    const fetch = renderPage({ [`GET ${BASE}`]: () => detail() });
    await editor();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });

    expect(puts(fetch)).toHaveLength(0);
  });

  it("saves after a reset to the starter", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const fetch = renderPage({
      [`GET ${BASE}`]: () => detail({ code: "// old\n" }),
      [`PUT ${BASE}/code`]: () => new Response(null, { status: 204 }),
    });
    await editor();

    await user.click(screen.getByRole("button", { name: "Reset ke starter" }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    expect(await puts(fetch)[0]!.json()).toEqual({ code: STARTER });
  });

  it("tells the user when saving fails", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    renderPage({
      [`GET ${BASE}`]: () => detail(),
      [`PUT ${BASE}/code`]: () => new Response("proxy error", { status: 502 }),
    });
    await user.type(await editor(), "x");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    expect(await screen.findByText(/Gagal menyimpan/)).toBeInTheDocument();
  });
});
