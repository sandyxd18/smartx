import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import type {
  ConfigRead,
  LintResult,
  ProjectConfig,
  ProjectDetail,
  ProjectEntry,
  ProjectRun,
} from "../api/client";
import { routes } from "../routes";
import { FakeEventSource } from "../test/fakeEventSource";
import { mockFetch } from "../test/mockFetch";

vi.mock("../components/CodeEditor", async () => ({
  CodeEditor: (await import("../test/fakeCodeEditor")).FakeCodeEditor,
}));

// Lazy route: load it once up front so the first test does not time out on a busy machine.
beforeAll(async () => {
  await import("./ProjectPage");
});

afterEach(() => {
  vi.restoreAllMocks();
});

const BASE = "/api/projects/1";

function detail(entries: ProjectEntry[]): ProjectDetail {
  return {
    id: 1,
    name: "FIFO",
    kind: "sandbox",
    source: "template:cocotb-basic",
    created_at: "2026-10-25T10:00:00Z",
    updated_at: "2026-10-25T10:00:00Z",
    file_count: entries.filter((e) => e.kind === "file").length,
    entries,
  };
}

const ENTRIES: ProjectEntry[] = [
  { path: "smartx.yaml", kind: "file" },
  { path: "src", kind: "dir" },
  { path: "src/counter.v", kind: "file" },
  { path: "test", kind: "dir" },
  { path: "test/test_counter.py", kind: "file" },
];

const CONTENT: Record<string, string> = {
  "smartx.yaml": "top: counter\n",
  "src/counter.v": "module counter;\nendmodule\n",
  "test/test_counter.py": "import cocotb\n",
};

function file(path: string) {
  return { path, content: CONTENT[path] ?? "", updated_at: "2026-10-25T10:00:00Z" };
}

/** A tiny in-memory backend; `log` records "METHOD path" in request order. */
function renderProject(extra: Parameters<typeof mockFetch>[0] = {}) {
  let entries = [...ENTRIES];
  const log: string[] = [];
  const saved: Record<string, string> = {};
  const fileRoutes: Parameters<typeof mockFetch>[0] = {};
  for (const path of Object.keys(CONTENT)) {
    fileRoutes[`GET ${BASE}/files/${path}`] = () => file(path);
    fileRoutes[`PUT ${BASE}/files/${path}`] = async (req: Request) => {
      saved[path] = ((await req.json()) as { content: string }).content;
      return { ...file(path), content: saved[path] };
    };
  }
  const routesTable: Parameters<typeof mockFetch>[0] = {
    [`GET ${BASE}`]: () => detail(entries),
    ...fileRoutes,
    ...extra,
  };
  const fetch = mockFetch(
    Object.fromEntries(
      Object.entries(routesTable).map(([key, handler]) => [
        key,
        (req: Request) => {
          log.push(key);
          return handler(req);
        },
      ]),
    ),
  );
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/workspace/1"] })} />);
  return {
    fetch,
    log,
    saved,
    setEntries: (next: ProjectEntry[]) => {
      entries = next;
    },
  };
}

async function openFile(name: string) {
  await userEvent.click(await screen.findByRole("button", { name }));
  return screen.findByLabelText<HTMLTextAreaElement>("Editor kode");
}

describe("ProjectPage", () => {
  it("shows the project and its file tree", async () => {
    renderProject();

    expect(await screen.findByRole("heading", { name: "FIFO" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "counter.v" })).toBeInTheDocument();
    expect(screen.getByText(/Pilih file/)).toBeInTheDocument();
  });

  it("explains a missing project", async () => {
    mockFetch({ [`GET ${BASE}`]: () => Response.json({ detail: "x" }, { status: 404 }) });
    render(
      <RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/workspace/1"] })} />,
    );
    expect(await screen.findByText("Proyek tidak ditemukan.")).toBeInTheDocument();
  });

  it("opens a file with the right language and saves edits", async () => {
    const { saved } = renderProject();

    const editor = await openFile("counter.v");
    expect(editor).toHaveValue(CONTENT["src/counter.v"]);
    expect(editor).toHaveAttribute("data-language", "verilog");

    await userEvent.type(editor, "// x");

    await waitFor(() => expect(saved["src/counter.v"]).toBe(`${CONTENT["src/counter.v"]}// x`), {
      timeout: 3000,
    });
    expect(await screen.findByText("Tersimpan")).toBeInTheDocument();
  });

  it("saves the open file before switching to another one", async () => {
    const { log, saved } = renderProject();
    const editor = await openFile("counter.v");
    await userEvent.type(editor, "!");

    // Right away, before the 1-second autosave.
    const next = await openFile("test_counter.py");

    expect(next).toHaveAttribute("data-language", "python");
    await waitFor(() => expect(next).toHaveValue(CONTENT["test/test_counter.py"]));
    expect(saved["src/counter.v"]).toBe(`${CONTENT["src/counter.v"]}!`);
    expect(log.indexOf(`PUT ${BASE}/files/src/counter.v`)).toBeLessThan(
      log.indexOf(`GET ${BASE}/files/test/test_counter.py`),
    );
  });

  it("creates a file in the selected folder and opens it", async () => {
    let body: unknown = null;
    const env = renderProject({
      [`POST ${BASE}/files`]: async (req: Request) => {
        body = await req.json();
        env.setEntries([...ENTRIES, { path: "src/fifo.v", kind: "file" }]);
        return Response.json(
          { path: "src/fifo.v", content: "", updated_at: "2026-10-25T10:00:00Z" },
          { status: 201 },
        );
      },
      [`GET ${BASE}/files/src/fifo.v`]: () => ({
        path: "src/fifo.v",
        content: "",
        updated_at: "2026-10-25T10:00:00Z",
      }),
    });

    await userEvent.click(await screen.findByRole("button", { name: "▾ src" }));
    await userEvent.click(screen.getByRole("button", { name: "File baru" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Nama file baru" }), "fifo.v{Enter}");

    await waitFor(() => expect(body).toEqual({ path: "src/fifo.v", content: "" }));
    expect(await screen.findByRole("button", { name: "fifo.v" })).toHaveAttribute(
      "aria-current",
      "true",
    );
    expect(await screen.findByLabelText("Editor kode")).toHaveValue("");
  });

  it("shows why a name was refused and keeps the input", async () => {
    renderProject({
      [`POST ${BASE}/files`]: () =>
        Response.json({ detail: "File 'src/counter.v' sudah ada." }, { status: 409 }),
    });

    await userEvent.click(await screen.findByRole("button", { name: "▾ src" }));
    await userEvent.click(screen.getByRole("button", { name: "File baru" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Nama file baru" }), "counter.v{Enter}");

    expect(await screen.findByText("File 'src/counter.v' sudah ada.")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Nama file baru" })).toBeInTheDocument();
  });

  it("deletes the open file without saving it again afterwards", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const env = renderProject({
      [`DELETE ${BASE}/files/src/counter.v`]: () => {
        env.setEntries(ENTRIES.filter((e) => e.path !== "src/counter.v"));
        return new Response(null, { status: 204 });
      },
    });
    const editor = await openFile("counter.v");
    await userEvent.type(editor, "!");

    await userEvent.click(screen.getByRole("button", { name: "Hapus src/counter.v" }));

    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "counter.v" })).not.toBeInTheDocument(),
    );
    expect(screen.queryByLabelText("Editor kode")).not.toBeInTheDocument();
    // Past the 1-second autosave delay: a pending edit must not recreate the file.
    await new Promise((resolve) => setTimeout(resolve, 1300));
    const del = env.log.indexOf(`DELETE ${BASE}/files/src/counter.v`);
    expect(del).toBeGreaterThan(-1);
    expect(env.log.slice(del).some((k) => k.startsWith("PUT"))).toBe(false);
  });

  it("follows the open file when its folder is renamed", async () => {
    let body: unknown = null;
    const renamed: ProjectEntry[] = ENTRIES.map((e) => ({
      ...e,
      path: e.path.replace(/^src/, "rtl"),
    }));
    const env = renderProject({
      [`POST ${BASE}/move`]: async (req: Request) => {
        body = await req.json();
        env.setEntries(renamed);
        return detail(renamed);
      },
      [`PUT ${BASE}/files/rtl/counter.v`]: async (req: Request) => {
        env.saved["rtl/counter.v"] = ((await req.json()) as { content: string }).content;
        return file("src/counter.v");
      },
    });
    const editor = await openFile("counter.v");

    await userEvent.click(screen.getByRole("button", { name: "Ganti nama src" }));
    const input = screen.getByRole("textbox", { name: "Nama baru" });
    await userEvent.clear(input);
    await userEvent.type(input, "rtl{Enter}");

    await waitFor(() => expect(body).toEqual({ from_path: "src", to_path: "rtl" }));
    await screen.findByRole("button", { name: "▾ rtl" });
    await userEvent.type(editor, "?");
    await waitFor(() => expect(env.saved["rtl/counter.v"]).toBe(`${CONTENT["src/counter.v"]}?`), {
      timeout: 3000,
    });
  });

  describe("smartx.yaml", () => {
    const config: ProjectConfig = {
      top: "counter",
      sources: ["src/**/*.v"],
      tests: ["test/test_counter.py"],
      simulator: "icarus",
      parameters: {},
      defines: {},
    };
    const configRead = (overrides: Partial<ConfigRead> = {}): ConfigRead => ({
      text: CONTENT["smartx.yaml"] ?? "",
      config,
      problems: [],
      sources: ["src/counter.v"],
      ...overrides,
    });

    it("opens as a form, offering the project's Python files as tests", async () => {
      renderProject({ [`POST ${BASE}/config/check`]: () => configRead() });

      await userEvent.click(await screen.findByRole("button", { name: "smartx.yaml" }));

      expect(await screen.findByLabelText("Modul top")).toHaveValue("counter");
      expect(screen.getByRole("checkbox", { name: "test/test_counter.py" })).toBeChecked();
    });

    it("saves a pending form change before another file opens", async () => {
      const env = renderProject({
        [`POST ${BASE}/config/check`]: () => configRead(),
        [`PUT ${BASE}/config`]: async (req: Request) =>
          configRead({ config: (await req.json()) as ProjectConfig }),
      });
      await userEvent.click(await screen.findByRole("button", { name: "smartx.yaml" }));
      await userEvent.click(await screen.findByRole("radio", { name: "Verilator" }));

      await openFile("counter.v");

      const put = env.log.indexOf(`PUT ${BASE}/config`);
      expect(put).toBeGreaterThan(-1);
      expect(put).toBeLessThan(env.log.indexOf(`GET ${BASE}/files/src/counter.v`));
    });
  });

  describe("lint", () => {
    const LINT: LintResult = {
      errors: 1,
      warnings: 1,
      diagnostics: [
        {
          file: "src/counter.v",
          line: 1,
          col: 8,
          end_col: 15,
          severity: "warning",
          code: "UNUSEDSIGNAL",
          message: "Sinyal tidak dipakai (Verilator UNUSEDSIGNAL: Signal is not used: 'x')",
        },
        {
          file: "test/test_counter.py",
          line: 2,
          col: 1,
          end_col: 5,
          severity: "error",
          code: null,
          message: "Verilator: syntax error",
        },
      ],
    };

    function projectRun(overrides: Partial<ProjectRun> = {}): ProjectRun {
      return {
        id: "r1",
        project_id: 1,
        kind: "lint",
        status: "queued",
        params: {},
        result: null,
        tool_versions: null,
        created_at: "2026-10-25T10:00:00Z",
        started_at: null,
        finished_at: null,
        exit_code: null,
        error: null,
        lint: null,
        ...overrides,
      };
    }

    function lintRoutes(final: Partial<ProjectRun> = { status: "succeeded", lint: LINT }) {
      return {
        [`POST ${BASE}/runs`]: () => Response.json(projectRun(), { status: 201 }),
        [`GET ${BASE}/runs/r1`]: () => projectRun(final),
      };
    }

    async function lintToEnd(status = "succeeded") {
      await userEvent.click(await screen.findByRole("button", { name: "Lint" }));
      const source = await waitFor(() => FakeEventSource.last());
      expect(source.url).toBe("/api/runs/r1/events");
      source.emit("status", { status: "running" });
      expect(await screen.findByText("Lint berjalan…")).toBeInTheDocument();
      source.emit("status", { status });
    }

    it("lists problems per file and marks the open file", async () => {
      const env = renderProject(lintRoutes());
      await openFile("counter.v");

      await lintToEnd();

      const panel = await screen.findByRole("region", { name: "Problems" });
      expect(await within(panel).findByText("1 error, 1 warning")).toBeInTheDocument();
      expect(within(panel).getByText("src/counter.v")).toBeInTheDocument();
      expect(within(panel).getByText("test/test_counter.py")).toBeInTheDocument();
      expect(screen.getByRole("list", { name: "Penanda editor" })).toHaveTextContent(
        "warning 1: Sinyal tidak dipakai",
      );
      // Only the open file's problems are markers.
      expect(screen.getByRole("list", { name: "Penanda editor" })).not.toHaveTextContent("syntax");
      expect(
        await env.fetch.mock.calls.find(([r]) => r.method === "POST")![0].clone().json(),
      ).toEqual({ kind: "lint" });
    });

    it("opens the file of a problem", async () => {
      renderProject(lintRoutes());
      await screen.findByRole("heading", { name: "FIFO" });

      await lintToEnd();
      await userEvent.click(await screen.findByRole("button", { name: /2:1 Verilator: syntax error/ }));

      const editor = await screen.findByLabelText("Editor kode");
      await waitFor(() => expect(editor).toHaveValue(CONTENT["test/test_counter.py"]));
      expect(screen.getByRole("list", { name: "Penanda editor" })).toHaveTextContent(
        "error 2: Verilator: syntax error",
      );
    });

    it("says so when there is nothing to fix", async () => {
      renderProject(lintRoutes({ status: "succeeded", lint: { errors: 0, warnings: 0, diagnostics: [] } }));
      await lintToEnd();
      expect(await screen.findByText("Tidak ada masalah.")).toBeInTheDocument();
    });

    it("explains a refused or failed lint", async () => {
      renderProject({
        [`POST ${BASE}/runs`]: () =>
          Response.json({ detail: "smartx.yaml belum valid (baris 2): x" }, { status: 422 }),
      });
      await userEvent.click(await screen.findByRole("button", { name: "Lint" }));
      expect(await screen.findByText("smartx.yaml belum valid (baris 2): x")).toBeInTheDocument();
    });

    it("shows the error of a run that did not finish", async () => {
      renderProject(lintRoutes({ status: "timeout", error: "Melebihi batas waktu 60 detik." }));
      await lintToEnd("timeout");
      expect(await screen.findByText(/Melebihi batas waktu 60 detik/)).toBeInTheDocument();
    });

    it("saves pending edits before linting", async () => {
      const env = renderProject(lintRoutes());
      const editor = await openFile("counter.v");
      await userEvent.type(editor, "!");

      await lintToEnd();

      const put = env.log.indexOf(`PUT ${BASE}/files/src/counter.v`);
      expect(put).toBeGreaterThan(-1);
      expect(put).toBeLessThan(env.log.indexOf(`POST ${BASE}/runs`));
    });
  });
});
