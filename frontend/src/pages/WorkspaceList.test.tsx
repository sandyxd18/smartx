import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ExerciseSummary, ProjectDetail, ProjectSummary, ProjectTemplate } from "../api/client";
import { routes } from "../routes";
import { mockFetch } from "../test/mockFetch";

vi.mock("../components/CodeEditor", async () => ({
  CodeEditor: (await import("../test/fakeCodeEditor")).FakeCodeEditor,
}));

afterEach(() => {
  vi.restoreAllMocks();
});

const TEMPLATES: ProjectTemplate[] = [
  { id: "empty", title: "Kosong", description: "Mulai dari nol." },
  { id: "cocotb-basic", title: "cocotb dasar", description: "Counter dan testbench." },
];

const EXERCISES = [
  { id: "counter-4bit", title: "Counter 4-bit", topics: ["sequential"] },
  { id: "mux-2to1", title: "Mux 2:1", topics: ["combinational"] },
] as ExerciseSummary[];

function project(overrides: Partial<ProjectSummary> & { id: number }): ProjectSummary {
  return {
    name: `Proyek ${overrides.id}`,
    kind: "sandbox",
    source: "template:empty",
    created_at: "2026-10-25T10:00:00Z",
    updated_at: "2026-10-25T11:00:00Z",
    file_count: 2,
    ...overrides,
  };
}

function detail(id: number, name: string): ProjectDetail {
  return { ...project({ id, name }), entries: [{ path: "smartx.yaml", kind: "file" }] };
}

function renderList(routesTable: Parameters<typeof mockFetch>[0] = {}) {
  const fetch = mockFetch({
    "GET /api/projects": () => [
      project({ id: 2, name: "FIFO", source: "template:cocotb-basic", file_count: 4 }),
      project({ id: 1, name: "Latihan counter", source: "exercise:counter-4bit" }),
    ],
    "GET /api/project-templates": () => TEMPLATES,
    "GET /api/exercises": () => EXERCISES,
    ...routesTable,
  });
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/workspace"] })} />);
  return fetch;
}

async function bodyOf(fetch: ReturnType<typeof mockFetch>, method: string, path: string) {
  const call = fetch.mock.calls.find(
    ([req]) => req.method === method && new URL(req.url).pathname === path,
  );
  expect(call, `${method} ${path}`).toBeDefined();
  return (await call![0].clone().json()) as unknown;
}

describe("WorkspaceList", () => {
  it("lists projects with where they came from", async () => {
    renderList();

    const list = await screen.findByRole("list", { name: "Daftar proyek" });
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    const [first, second] = items as [HTMLElement, HTMLElement];
    expect(first).toHaveTextContent("FIFO");
    expect(first).toHaveTextContent("Template: cocotb dasar");
    expect(first).toHaveTextContent("4 file");
    expect(second).toHaveTextContent("Dari soal: Counter 4-bit");
    expect(within(first).getByRole("link", { name: "FIFO" })).toHaveAttribute(
      "href",
      "/workspace/2",
    );
  });

  it("says so when there are no projects", async () => {
    renderList({ "GET /api/projects": () => [] });
    expect(await screen.findByText(/Belum ada proyek/)).toBeInTheDocument();
  });

  it("creates a project from a template and opens it", async () => {
    const fetch = renderList({
      "POST /api/projects": () => Response.json(detail(7, "Counterku"), { status: 201 }),
      "GET /api/projects/7": () => detail(7, "Counterku"),
    });

    await userEvent.type(await screen.findByLabelText("Nama proyek"), "Counterku");
    await userEvent.selectOptions(screen.getByLabelText("Mulai dari"), "template:cocotb-basic");
    await userEvent.click(screen.getByRole("button", { name: "Buat proyek" }));

    expect(await screen.findByRole("heading", { name: "Counterku" })).toBeInTheDocument();
    expect(await bodyOf(fetch, "POST", "/api/projects")).toEqual({
      name: "Counterku",
      template: "cocotb-basic",
    });
  });

  it("can copy an exercise", async () => {
    const fetch = renderList({
      "POST /api/projects": () => Response.json(detail(8, "Mux"), { status: 201 }),
      "GET /api/projects/8": () => detail(8, "Mux"),
    });

    await userEvent.type(await screen.findByLabelText("Nama proyek"), "Mux");
    // Exercises are grouped by topic, in curriculum order.
    const groups = within(screen.getByLabelText("Mulai dari")).getAllByRole("group");
    expect(groups.map((g) => g.getAttribute("label"))).toEqual([
      "Salin dari soal: Kombinasional",
      "Salin dari soal: Sekuensial",
    ]);
    await userEvent.selectOptions(screen.getByLabelText("Mulai dari"), "exercise:mux-2to1");
    await userEvent.click(screen.getByRole("button", { name: "Buat proyek" }));

    await screen.findByRole("heading", { name: "Mux" });
    expect(await bodyOf(fetch, "POST", "/api/projects")).toEqual({
      name: "Mux",
      exercise_id: "mux-2to1",
    });
  });

  it("shows the backend's reason when creating fails", async () => {
    renderList({
      "POST /api/projects": () =>
        Response.json({ detail: "Template tidak ditemukan." }, { status: 404 }),
    });

    await userEvent.type(await screen.findByLabelText("Nama proyek"), "X");
    await userEvent.click(screen.getByRole("button", { name: "Buat proyek" }));

    expect(await screen.findByText("Template tidak ditemukan.")).toBeInTheDocument();
  });

  it("deletes a project after confirmation", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    let deleted = false;
    const fetch = renderList({
      "GET /api/projects": () =>
        deleted ? [project({ id: 1, name: "Latihan counter" })] : [
          project({ id: 2, name: "FIFO" }),
          project({ id: 1, name: "Latihan counter" }),
        ],
      "DELETE /api/projects/2": () => {
        deleted = true;
        return new Response(null, { status: 204 });
      },
    });

    await userEvent.click(await screen.findByRole("button", { name: "Hapus proyek FIFO" }));

    expect(confirm).toHaveBeenCalledWith(expect.stringContaining("FIFO"));
    await waitFor(() => expect(screen.queryByText("FIFO")).not.toBeInTheDocument());
    expect(fetch.mock.calls.some(([r]) => r.method === "DELETE")).toBe(true);
  });

  it("keeps the project when deletion is not confirmed", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const fetch = renderList();

    await userEvent.click(await screen.findByRole("button", { name: "Hapus proyek FIFO" }));

    expect(fetch.mock.calls.some(([r]) => r.method === "DELETE")).toBe(false);
  });
});
