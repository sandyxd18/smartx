import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ConfigRead, ProjectConfig } from "../api/client";
import { mockFetch } from "../test/mockFetch";
import { ConfigEditor, type ConfigEditorProps } from "./ConfigEditor";

vi.mock("./CodeEditor", async () => ({
  CodeEditor: (await import("../test/fakeCodeEditor")).FakeCodeEditor,
}));

afterEach(() => {
  vi.restoreAllMocks();
});

const BASE = "/api/projects/1/config";

const CONFIG: ProjectConfig = {
  top: "counter",
  sources: ["src/**/*.v"],
  tests: ["test/test_counter.py"],
  simulator: "icarus",
  parameters: { WIDTH: 8 },
  defines: {},
};

const TEXT = "top: counter\nsources:\n- src/**/*.v\ntests:\n- test/test_counter.py\n";

function read(overrides: Partial<ConfigRead> = {}): ConfigRead {
  return { text: TEXT, config: CONFIG, problems: [], sources: ["src/counter.v"], ...overrides };
}

function setup(
  routes: Parameters<typeof mockFetch>[0] = {},
  overrides: Partial<ConfigEditorProps> = {},
) {
  const fetch = mockFetch({ [`POST ${BASE}/check`]: () => read(), ...routes });
  const props: ConfigEditorProps = {
    projectId: 1,
    text: TEXT,
    pyFiles: ["test/test_counter.py", "test/test_other.py"],
    onEdit: vi.fn(),
    onSaved: vi.fn(),
    settleText: vi.fn(() => Promise.resolve()),
    registerSettle: vi.fn(),
    ...overrides,
  };
  render(<ConfigEditor {...props} />);
  return { fetch, props };
}

/** A PUT /config handler that records each body and answers like the backend. */
function recordPuts(sent: ProjectConfig[], text = TEXT) {
  return async (req: Request) => {
    const body = (await req.json()) as ProjectConfig;
    sent.push(body);
    return read({ text, config: body });
  };
}

describe("ConfigEditor", () => {
  it("starts in the form with the parsed config and the matched files", async () => {
    setup();

    expect(await screen.findByLabelText("Modul top")).toHaveValue("counter");
    expect(screen.getByRole("radio", { name: "Icarus" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "test/test_counter.py" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "test/test_other.py" })).not.toBeChecked();
    expect(screen.getByText(/src\/counter\.v/)).toBeInTheDocument();
    expect(screen.getByLabelText("Nama parameter 1")).toHaveValue("WIDTH");
    expect(screen.getByLabelText("Nilai parameter 1")).toHaveValue("8");
  });

  it("saves form changes as a whole config and hands the new YAML back", async () => {
    const saved = "# baru\ntop: counter\nsimulator: verilator\n";
    const sent: ProjectConfig[] = [];
    const { props } = setup({ [`PUT ${BASE}`]: recordPuts(sent, saved) });

    await userEvent.click(await screen.findByRole("radio", { name: "Verilator" }));
    await userEvent.click(screen.getByRole("checkbox", { name: "test/test_other.py" }));

    await waitFor(() => expect(props.onSaved).toHaveBeenCalledWith(saved), { timeout: 3000 });
    expect(sent.at(-1)).toEqual({
      ...CONFIG,
      simulator: "verilator",
      tests: ["test/test_counter.py", "test/test_other.py"],
    });
    // The YAML mode must not save on top of the form's save.
    expect(props.settleText).toHaveBeenCalled();
  });

  it("keeps the fpga section, which the form does not edit", async () => {
    const fpga = {
      board: "tang-nano-9k",
      constraints: "constraints/tang-nano-9k.cst",
      parameters: { HALF_PERIOD: 13500000 },
      defines: {},
    };
    const sent: ProjectConfig[] = [];
    setup({
      [`POST ${BASE}/check`]: () => read({ config: { ...CONFIG, fpga } }),
      [`PUT ${BASE}`]: recordPuts(sent),
    });

    await userEvent.click(await screen.findByRole("radio", { name: "Verilator" }));

    await waitFor(() => expect(sent.at(-1)?.simulator).toBe("verilator"), { timeout: 3000 });
    expect(sent.at(-1)?.fpga).toEqual(fpga);
  });

  it("turns numeric parameter values into numbers and keeps the rest as text", async () => {
    const sent: ProjectConfig[] = [];
    setup({ [`PUT ${BASE}`]: recordPuts(sent) });

    await userEvent.click(await screen.findByRole("button", { name: "Tambah define" }));
    // The new row is ready to type into.
    expect(screen.getByLabelText("Nama define 1")).toHaveFocus();
    await userEvent.keyboard("INIT");
    await userEvent.type(screen.getByLabelText("Nilai define 1"), "8'hFF");
    const value = screen.getByLabelText("Nilai parameter 1");
    await userEvent.clear(value);
    await userEvent.type(value, "-16");

    await waitFor(
      () => {
        expect(sent.at(-1)?.parameters).toEqual({ WIDTH: -16 });
        expect(sent.at(-1)?.defines).toEqual({ INIT: "8'hFF" });
      },
      { timeout: 3000 },
    );
  });

  it("focuses a newly added source pattern", async () => {
    setup();
    await userEvent.click(await screen.findByRole("button", { name: "Tambah pola" }));
    expect(screen.getByLabelText("Pola sumber 2")).toHaveFocus();
  });

  it("shows why the form could not be saved", async () => {
    setup({
      [`PUT ${BASE}`]: () =>
        Response.json(
          { detail: [{ msg: "Value error, '9x' bukan identifier Verilog yang valid", loc: [] }] },
          { status: 422 },
        ),
    });

    const top = await screen.findByLabelText("Modul top");
    await userEvent.clear(top);
    await userEvent.type(top, "9x");

    expect(
      await screen.findByText(/'9x' bukan identifier Verilog/, {}, { timeout: 3000 }),
    ).toBeInTheDocument();
  });

  it("switches to YAML and marks problems in the editor", async () => {
    const { props } = setup({
      [`POST ${BASE}/check`]: () =>
        read({
          problems: [
            { severity: "warning", message: "Pola 'rtl/*.v' tidak cocok.", line: 3 },
            { severity: "warning", message: "Belum ada test.", line: null },
          ],
        }),
    });

    await userEvent.click(await screen.findByRole("tab", { name: "YAML" }));

    const editor = await screen.findByLabelText("Editor kode");
    expect(editor).toHaveValue(TEXT);
    expect(editor).toHaveAttribute("data-language", "yaml");
    await userEvent.type(editor, "#");
    expect(props.onEdit).toHaveBeenCalledWith(`${TEXT}#`);

    const problems = await screen.findByRole("list", { name: "Masalah konfigurasi" });
    expect(within(problems).getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByRole("list", { name: "Penanda editor" })).toHaveTextContent(
      "warning 3: Pola 'rtl/*.v' tidak cocok.",
    );
  });

  it("opens YAML when the file has errors, and keeps the form closed until fixed", async () => {
    setup({
      [`POST ${BASE}/check`]: () =>
        read({
          config: null,
          problems: [{ severity: "error", message: "YAML tidak valid: x", line: 2 }],
        }),
    });

    expect(await screen.findByLabelText("Editor kode")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Form" }));

    expect(screen.getByText(/Perbaiki error di mode YAML/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Modul top")).not.toBeInTheDocument();
  });

  it("lets the page wait for a pending form save", async () => {
    const { props } = setup();
    await screen.findByLabelText("Modul top");
    expect(props.registerSettle).toHaveBeenCalledWith(expect.any(Function));
  });
});
