import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import type { ExerciseSummary } from "../api/client";
import { routes } from "../routes";
import { mockFetch } from "../test/mockFetch";

function ex(overrides: Partial<ExerciseSummary> & { id: string }): ExerciseSummary {
  return {
    title: `Soal ${overrides.id}`,
    step: 1,
    level: 1,
    topics: ["sequential"],
    order: null,
    requires: [],
    status: "not_started",
    attempts: 0,
    ...overrides,
  };
}

// API order (step, order, id) is the curriculum order within a topic.
const EXERCISES: ExerciseSummary[] = [
  ex({ id: "dff-basic", title: "D flip-flop", status: "solved", attempts: 2 }),
  ex({ id: "mux-2to1", title: "Mux 2:1", topics: ["combinational", "mux"], level: 1 }),
  ex({
    id: "counter-4bit",
    title: "Counter 4-bit",
    level: 2,
    status: "attempted",
    attempts: 3,
    requires: ["dff-basic"],
  }),
  ex({ id: "latch-fix", title: "Perbaiki latch", topics: ["pitfalls"], level: 3 }),
  ex({ id: "seq-detect", title: "Deteksi 1011", topics: ["fsm"], level: 2 }),
  ex({ id: "misc", title: "Soal lain", topics: ["zzz-custom"] }),
];

function renderAt(path = "/latihan", exercises: ExerciseSummary[] = EXERCISES) {
  mockFetch({ "GET /api/exercises": () => exercises });
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />);
}

function sectionTitles(): string[] {
  return screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent ?? "");
}

function exerciseLinks(): string[] {
  return screen.queryAllByRole("link", { name: /Soal|Mux|Counter|D flip|latch|Deteksi/ })
    .map((a) => a.getAttribute("href") ?? "");
}

describe("ExerciseList", () => {
  it("groups by first topic in curriculum order with Indonesian labels", async () => {
    renderAt();
    await screen.findByText("Counter 4-bit");

    expect(sectionTitles()).toEqual([
      "Kombinasional1",
      "Sekuensial2",
      "FSM1",
      "Jebakan umum1",
      "zzz-custom1",
    ]);
    const sequential = screen.getByRole("region", { name: "Sekuensial" });
    const titles = within(sequential).getAllByRole("link").map((a) => a.textContent);
    expect(titles[0]).toContain("D flip-flop");
    expect(titles[1]).toContain("Counter 4-bit");
  });

  it("shows level, status, attempts and prerequisites", async () => {
    renderAt();
    const counter = (await screen.findByText("Counter 4-bit")).closest("a")!;

    expect(counter).toHaveAttribute("href", "/latihan/counter-4bit");
    expect(within(counter).getByText("Menengah")).toBeInTheDocument();
    expect(within(counter).getByText("Gagal")).toBeInTheDocument();
    expect(within(counter).getByText("3 percobaan")).toBeInTheDocument();
    expect(within(counter).getByText("Prasyarat: dff-basic")).toBeInTheDocument();

    const dff = screen.getByText("D flip-flop").closest("a")!;
    expect(within(dff).getByText("Dasar")).toBeInTheDocument();
    expect(within(dff).getByText("Lulus")).toBeInTheDocument();

    const latch = screen.getByText("Perbaiki latch").closest("a")!;
    expect(within(latch).getByText("Lanjut")).toBeInTheDocument();
    expect(within(latch).getByText("Belum")).toBeInTheDocument();
  });

  it("summarises progress", async () => {
    renderAt();
    expect(await screen.findByText("1 dari 6 soal lulus")).toBeInTheDocument();
  });

  it("filters by status, level and text", async () => {
    renderAt();
    await screen.findByText("Counter 4-bit");

    await userEvent.selectOptions(screen.getByLabelText("Status"), "solved");
    expect(exerciseLinks()).toEqual(["/latihan/dff-basic"]);

    await userEvent.selectOptions(screen.getByLabelText("Status"), "all");
    await userEvent.selectOptions(screen.getByLabelText("Level"), "2");
    expect(exerciseLinks()).toEqual(["/latihan/counter-4bit", "/latihan/seq-detect"]);

    await userEvent.selectOptions(screen.getByLabelText("Level"), "all");
    await userEvent.type(screen.getByLabelText("Cari"), "MUX");
    expect(exerciseLinks()).toEqual(["/latihan/mux-2to1"]);
    expect(sectionTitles()).toEqual(["Kombinasional1"]);
  });

  it("reads filters from the URL", async () => {
    renderAt("/latihan?status=not_started&level=3");
    await screen.findByText("Perbaiki latch");

    expect(exerciseLinks()).toEqual(["/latihan/latch-fix"]);
    expect(screen.getByLabelText("Status")).toHaveValue("not_started");
    expect(screen.getByLabelText("Level")).toHaveValue("3");
  });

  it("explains when nothing matches", async () => {
    renderAt("/latihan?q=tidak-ada-soal-ini");
    expect(await screen.findByText("Tidak ada soal yang cocok dengan filter.")).toBeInTheDocument();
  });

  it("explains when there are no exercises", async () => {
    renderAt("/latihan", []);
    expect(await screen.findByText(/Belum ada soal/)).toBeInTheDocument();
  });

  it("explains when the backend is unreachable", async () => {
    mockFetch({
      "GET /api/exercises": () => new Response("proxy error", { status: 502 }),
    });
    render(
      <RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/latihan"] })} />,
    );
    expect(
      await screen.findByText("Backend tidak bisa dihubungi (HTTP 502)."),
    ).toBeInTheDocument();
  });
});
