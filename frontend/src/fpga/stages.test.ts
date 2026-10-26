import { describe, expect, it } from "vitest";
import { MISSED_TIMING } from "../test/fpgaFixtures";
import { liveStages, resultStages } from "./stages";

const status = (stages: ReturnType<typeof liveStages>) =>
  stages.map((s) => [s.title, s.status, s.seconds]);

describe("liveStages", () => {
  it("follows the markers build.py prints", () => {
    expect(status(liveStages([]))).toEqual([
      ["Synthesize", "pending", null],
      ["Place & Route", "pending", null],
      ["Pack", "pending", null],
    ]);

    const lines = [
      "==> Synthesize",
      "Warning: Latch inferred for signal ...",
      "<== Synthesize: ok (0.86 s)",
      "==> Place & Route",
    ];
    expect(status(liveStages(lines))).toEqual([
      ["Synthesize", "ok", 0.86],
      ["Place & Route", "running", null],
      ["Pack", "pending", null],
    ]);

    lines.push(
      "ERROR: Unconstrained IO:led_OBUF_O",
      "<== Place & Route: failed (0.13 s)",
    );
    expect(status(liveStages(lines))[1]).toEqual([
      "Place & Route",
      "failed",
      0.13,
    ]);
  });
});

describe("resultStages", () => {
  it("keeps the log of each stage", () => {
    const stages = resultStages(MISSED_TIMING);
    expect(stages.map((s) => s.logUrl)).toEqual([
      "/api/runs/f1/files/build/yosys.log",
      "/api/runs/f1/files/build/nextpnr.log",
      null,
    ]);
    expect(stages[2]?.seconds).toBe(2.73);
  });
});

describe("liveStages with a stage plan", () => {
  it("shows only the stages the build announced", () => {
    // A board without a packer (DE1-SoC): nextpnr writes the bitstream.
    const lines = ["stages: Synthesize | Place & Route", "==> Synthesize"];
    expect(status(liveStages(lines))).toEqual([
      ["Synthesize", "running", null],
      ["Place & Route", "pending", null],
    ]);
  });
});
