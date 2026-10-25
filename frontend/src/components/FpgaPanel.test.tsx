import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ConfigRead, ProjectConfig } from "../api/client";
import { TANG } from "../test/fpgaFixtures";
import { mockFetch } from "../test/mockFetch";
import { FpgaPanel, type FpgaPanelProps } from "./FpgaPanel";

afterEach(() => {
  vi.restoreAllMocks();
});

const BASE = "/api/projects/1";
const SIM: ProjectConfig = {
  top: "blinky",
  sources: ["src/**/*.v"],
  tests: [],
  simulator: "icarus",
  parameters: {},
  defines: {},
};

function read(config: ProjectConfig | null): ConfigRead {
  return {
    text: "top: blinky\n",
    config,
    problems: [],
    sources: ["src/blinky.v"],
  };
}

/** smartx.yaml held in memory: GET returns what the last PUT stored. */
function setup(
  initial: ProjectConfig | null,
  overrides: Partial<FpgaPanelProps> = {},
) {
  let config = initial;
  const puts: ProjectConfig[] = [];
  const posts: { path: string; content: string }[] = [];
  const fetch = mockFetch({
    "GET /api/boards": () => [TANG],
    [`GET ${BASE}/config`]: () => read(config),
    [`PUT ${BASE}/config`]: async (req: Request) => {
      config = (await req.json()) as ProjectConfig;
      puts.push(config);
      return { ...read(config), text: "# baru\n" };
    },
    [`POST ${BASE}/files`]: async (req: Request) => {
      const body = (await req.json()) as { path: string; content: string };
      posts.push(body);
      return Response.json({ ...body, updated_at: "" }, { status: 201 });
    },
  });
  const props: FpgaPanelProps = {
    projectId: 1,
    files: ["smartx.yaml", "src/blinky.v"],
    settle: vi.fn(() => Promise.resolve()),
    onConfigSaved: vi.fn(),
    onFileCreated: vi.fn(() => Promise.resolve()),
    onOpenFile: vi.fn(),
    ...overrides,
  };
  render(<FpgaPanel {...props} />);
  return { fetch, props, puts, posts };
}

describe("FpgaPanel", () => {
  it("picking a board creates its constraint file and saves the fpga section", async () => {
    const { props, puts, posts } = setup(SIM);

    await userEvent.selectOptions(
      await screen.findByRole("combobox", { name: "Board" }),
      "tang-nano-9k",
    );

    await waitFor(() =>
      expect(props.onOpenFile).toHaveBeenCalledWith(
        "constraints/tang-nano-9k.cst",
      ),
    );
    expect(posts).toEqual([
      {
        path: "constraints/tang-nano-9k.cst",
        content: TANG.constraints_template,
      },
    ]);
    // The rest of smartx.yaml is kept; pending edits were stored first.
    expect(puts).toEqual([
      {
        ...SIM,
        fpga: {
          board: "tang-nano-9k",
          constraints: "constraints/tang-nano-9k.cst",
          parameters: {},
          defines: {},
        },
      },
    ]);
    expect(props.settle).toHaveBeenCalled();
    expect(props.onFileCreated).toHaveBeenCalled();
    expect(props.onConfigSaved).toHaveBeenCalledWith("# baru\n");
    expect(
      screen.getByText(/GW1NR-LV9QN88PC6\/I5 · clock 27 MHz/),
    ).toBeInTheDocument();
  });

  it("keeps an existing constraint file", async () => {
    const { posts, puts } = setup(SIM, {
      files: ["smartx.yaml", "constraints/tang-nano-9k.cst"],
    });

    await userEvent.selectOptions(
      await screen.findByRole("combobox", { name: "Board" }),
      "tang-nano-9k",
    );

    await waitFor(() => expect(puts).toHaveLength(1));
    expect(posts).toEqual([]);
  });

  it("keeps build-only parameters when the board is picked again", async () => {
    const fpga = {
      board: "tang-nano-9k",
      constraints: "constraints/tang-nano-9k.cst",
      parameters: { HALF_PERIOD: 13500000 },
      defines: { BOARD: 1 },
      freq_mhz: 50,
    };
    const { puts } = setup(
      { ...SIM, fpga },
      { files: ["constraints/tang-nano-9k.cst"] },
    );

    await userEvent.selectOptions(
      await screen.findByRole("combobox", { name: "Board" }),
      "tang-nano-9k",
    );

    await waitFor(() => expect(puts).toHaveLength(1));
    expect(puts[0]?.fpga).toEqual({
      board: "tang-nano-9k",
      constraints: "constraints/tang-nano-9k.cst",
      parameters: { HALF_PERIOD: 13500000 },
      defines: { BOARD: 1 },
    });
  });

  it("saves the target clock, and an empty field means the board clock", async () => {
    const fpga = {
      board: "tang-nano-9k",
      constraints: "constraints/tang-nano-9k.cst",
      parameters: {},
      defines: {},
    };
    const { puts } = setup(
      { ...SIM, fpga },
      { files: ["constraints/tang-nano-9k.cst"] },
    );

    const freq = await screen.findByRole("textbox", {
      name: "Target clock (MHz)",
    });
    expect(freq).toHaveAttribute("placeholder", "27 (clock board)");
    await userEvent.type(freq, "50,5{Enter}");
    await waitFor(() =>
      expect(puts.at(-1)?.fpga).toEqual({ ...fpga, freq_mhz: 50.5 }),
    );

    await userEvent.clear(freq);
    await userEvent.tab();
    await waitFor(() =>
      expect(puts.at(-1)?.fpga).toEqual({ ...fpga, freq_mhz: null }),
    );

    await userEvent.type(freq, "0{Enter}");
    expect(
      await screen.findByText(/Target clock harus angka MHz/),
    ).toBeInTheDocument();
    expect(puts).toHaveLength(2);
  });

  it("offers the board template when the constraint file is missing", async () => {
    const fpga = {
      board: "tang-nano-9k",
      constraints: "pins/board.cst",
      parameters: {},
      defines: {},
    };
    const { props, posts } = setup({ ...SIM, fpga });

    expect(
      await screen.findByText("File constraint belum ada di proyek."),
    ).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Buat dari template board" }),
    );

    await waitFor(() =>
      expect(props.onOpenFile).toHaveBeenCalledWith("pins/board.cst"),
    );
    expect(posts).toEqual([
      { path: "pins/board.cst", content: TANG.constraints_template },
    ]);
  });

  it("asks to fix smartx.yaml first when it does not parse", async () => {
    setup(null);

    expect(
      await screen.findByText(
        "smartx.yaml belum valid. Perbaiki dulu di editor.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Board" })).toBeDisabled();
  });
});
