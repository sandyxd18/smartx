import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { FpgaResult, ProjectRun } from "../api/client";
import type { ProjectRunState } from "../hooks/useProjectRun";
import { MISSED_TIMING } from "../test/fpgaFixtures";
import { FpgaReport, FpgaSummary } from "./FpgaReport";

function state(
  overrides: Partial<ProjectRunState> = {},
  fpga?: FpgaResult,
): ProjectRunState {
  const run: ProjectRun = {
    id: "f1",
    project_id: 1,
    kind: "fpga",
    status: "succeeded",
    params: {},
    result: null,
    tool_versions: null,
    created_at: "2026-10-25T10:00:00Z",
    started_at: null,
    finished_at: null,
    exit_code: 0,
    error: null,
    lint: null,
    sim: null,
    fpga: fpga ?? MISSED_TIMING,
  };
  return {
    run,
    running: false,
    status: "succeeded",
    lines: [],
    error: null,
    ...overrides,
  };
}

describe("FpgaReport", () => {
  it("marks missed timing in red and opens the critical path", async () => {
    const onOpenSource = vi.fn();
    render(<FpgaReport fpga={state()} onOpenSource={onOpenSource} />);

    const timing = screen.getByRole("table", { name: "Timing" });
    const row = within(timing).getByText("clk").closest("tr")!;
    expect(row).toHaveClass("text-red-700");
    expect(within(row).getByText("Gagal")).toBeInTheDocument();
    expect(row).toHaveTextContent("159,08 MHz");
    expect(row).toHaveTextContent("300 MHz");
    expect(screen.getByText(/Timing tidak tercapai/)).toBeInTheDocument();

    // A design that misses timing shows its critical path without a click.
    const path = screen.getByRole("table", { name: "Jalur kritis" });
    expect(path).toBeVisible();
    expect(path.closest("details")).toHaveAttribute("open");
    expect(
      screen.getByText(/6,29 ns \(3,70 ns logika, 2,59 ns routing\)/),
    ).toBeInTheDocument();
    await userEvent.click(
      within(path).getByRole("button", { name: "src/blinky.v:6" }),
    );
    expect(onOpenSource).toHaveBeenCalledWith("src/blinky.v", 6);
  });

  it("shows resources, warnings, the stages and the bitstream", async () => {
    const onOpenSource = vi.fn();
    render(<FpgaReport fpga={state()} onOpenSource={onOpenSource} />);

    const resources = screen.getByRole("table", { name: "Resource" });
    expect(within(resources).getByText("LUT").closest("tr")).toHaveTextContent(
      "438640",
    );
    expect(screen.getByLabelText("Synthesize: berhasil")).toHaveTextContent(
      "0,9 dtk",
    );
    expect(screen.getByLabelText("Pack: berhasil")).toBeInTheDocument();

    const warnings = screen.getByRole("region", {
      name: "Peringatan sintesis",
    });
    expect(warnings).toHaveTextContent("Peringatan sintesis (2)");
    expect(warnings).toHaveTextContent("Latch terbentuk untuk led: beri nilai");
    // Backticks in the message mark code.
    expect(
      within(warnings).getByText("led", { selector: "code" }),
    ).toBeInTheDocument();
    await userEvent.click(
      within(warnings).getByRole("button", { name: "src/blinky.v:10" }),
    );
    expect(onOpenSource).toHaveBeenCalledWith("src/blinky.v", 10);

    const download = screen.getByRole("link", { name: "Unduh bitstream" });
    expect(download).toHaveAttribute("href", MISSED_TIMING.bitstream_url);
    expect(download).toHaveAttribute("download", "blinky-tang-nano-9k.fs");
  });

  it("keeps the critical path folded when timing is met", () => {
    const met: FpgaResult = {
      ...MISSED_TIMING,
      timing_met: true,
      clocks: [{ ...MISSED_TIMING.clocks[0]!, target_mhz: 27, met: true }],
    };
    render(<FpgaReport fpga={state({}, met)} onOpenSource={vi.fn()} />);

    expect(screen.getByText("Tercapai")).toHaveClass("text-green-700");
    expect(
      screen.getByRole("table", { name: "Jalur kritis" }).closest("details"),
    ).not.toHaveAttribute("open");
    expect(screen.queryByText(/Timing tidak tercapai/)).not.toBeInTheDocument();
  });

  it("names the failed stage and its first error", () => {
    const failed: FpgaResult = {
      ...MISSED_TIMING,
      status: "failed",
      stages: [
        { id: "synth", title: "Synthesize", status: "ok", seconds: 0.8 },
        { id: "pnr", title: "Place & Route", status: "failed", seconds: 0.1 },
        { id: "pack", title: "Pack", status: "skipped" },
      ],
      error: "Unconstrained IO:led_OBUF_O",
      bitstream_url: null,
      utilization: [],
      clocks: [],
      timing_met: null,
      critical_paths: [],
      warnings: [],
    };
    render(<FpgaReport fpga={state({}, failed)} onOpenSource={vi.fn()} />);

    expect(screen.getByText("Place & Route gagal:")).toBeInTheDocument();
    expect(screen.getByText("Unconstrained IO:led_OBUF_O")).toBeInTheDocument();
    expect(screen.getByLabelText("Pack: dilewati")).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Unduh bitstream" }),
    ).not.toBeInTheDocument();
  });

  it("follows the stages while the build runs", () => {
    const lines = [
      "==> Synthesize",
      "<== Synthesize: ok (0.86 s)",
      "==> Place & Route",
    ];
    render(
      <FpgaReport
        fpga={state({ running: true, status: "running", lines, run: null })}
        onOpenSource={vi.fn()}
      />,
    );

    expect(screen.getByLabelText("Synthesize: berhasil")).toBeInTheDocument();
    expect(
      screen.getByLabelText("Place & Route: berjalan"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Pack: belum")).toBeInTheDocument();
  });
});

describe("FpgaSummary", () => {
  it.each([
    [state({ run: null, status: null }), "Klik Build"],
    [state({ running: true, status: "running", run: null }), "Build berjalan…"],
    [state(), "Bitstream jadi · timing tidak tercapai · tang-nano-9k"],
    [
      state({ error: "Bagian 'fpga' belum ada di smartx.yaml." }),
      "Bagian 'fpga' belum ada",
    ],
  ])("%#", (fpga, text) => {
    render(<FpgaSummary fpga={fpga} />);
    expect(document.body).toHaveTextContent(text);
  });
});
