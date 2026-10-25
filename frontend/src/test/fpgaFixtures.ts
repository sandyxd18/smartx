import type { Board, FpgaResult } from "../api/client";

export const TANG: Board = {
  id: "tang-nano-9k",
  name: "Sipeed Tang Nano 9K",
  family: "gowin",
  device: "GW1NR-LV9QN88PC6/I5",
  clock_port: "clk",
  clock_pin: "52",
  clock_mhz: 27,
  constraints_format: "cst",
  constraints_template: 'IO_LOC "clk" 52;\n',
  flash_command: ["openFPGALoader", "-b", "tangnano9k"],
};

/** A build that packed but missed its 300 MHz target (numbers from a real run). */
export const MISSED_TIMING: FpgaResult = {
  status: "ok",
  board: "tang-nano-9k",
  top: "blinky",
  freq_mhz: 300,
  stages: [
    {
      id: "synth",
      title: "Synthesize",
      status: "ok",
      seconds: 0.86,
      log_url: "/api/runs/f1/files/build/yosys.log",
    },
    {
      id: "pnr",
      title: "Place & Route",
      status: "ok",
      seconds: 0.49,
      log_url: "/api/runs/f1/files/build/nextpnr.log",
    },
    { id: "pack", title: "Pack", status: "ok", seconds: 2.73, log_url: null },
  ],
  error: null,
  diagnostics: [],
  versions: { yosys: "Yosys 0.70+219" },
  bitstream_url: "/api/runs/f1/files/build/bitstream.fs",
  report_url: "/api/runs/f1/files/build/report.json",
  stat_url: "/api/runs/f1/files/build/stat.txt",
  warnings: [
    {
      kind: "latch",
      signal: "led",
      module: "blinky",
      file: "src/blinky.v",
      line: 10,
      message: "Latch terbentuk untuk `led`: beri nilai default.",
    },
    {
      kind: "multi_driven",
      signal: "x",
      module: "blinky",
      file: null,
      line: null,
      message: "`x` diberi nilai dari lebih dari satu tempat.",
    },
  ],
  utilization: [
    { label: "LUT", types: ["LUT4"], used: 43, available: 8640, percent: 0.5 },
    { label: "FF", types: ["DFF"], used: 31, available: 6480, percent: 0.5 },
  ],
  clocks: [
    {
      net: "clk_IBUF_I_O",
      name: "clk",
      achieved_mhz: 159.08,
      target_mhz: 300,
      met: false,
    },
  ],
  timing_met: false,
  critical_paths: [
    {
      from_clock: "posedge clk",
      to_clock: "posedge clk",
      delay_ns: 6.29,
      logic_ns: 3.7,
      routing_ns: 2.59,
      steps: [
        {
          type: "clk-to-q",
          delay_ns: 0.46,
          total_ns: 0.46,
          name: "count_DFFR_Q_4.Q",
          file: null,
          line: null,
        },
        {
          type: "routing",
          delay_ns: 0.33,
          total_ns: 0.78,
          name: "count[24]",
          file: "src/blinky.v",
          line: 6,
        },
      ],
    },
  ],
};
