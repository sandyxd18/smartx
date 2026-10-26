# smartx-flash

Loads a bitstream built by SmartX onto an FPGA board. The script runs on the computer the board is plugged into, not in a container, because USB access from Docker is unreliable (DECISIONS D09). It takes the bitstream from the SmartX backend and calls `openFPGALoader` with the arguments from the board profile.

## Requirements

- Python 3.8 or newer. The script only uses the standard library, so there is nothing to `pip install`.
- `openFPGALoader` on the `PATH` (see below).
- The SmartX backend running (`make dev`), unless you only want to see the command.

## Installing openFPGALoader

The commands below come from the [openFPGALoader installation guide](https://trabucayre.github.io/openFPGALoader/guide/install.html).

| System | Command |
|---|---|
| Debian / Ubuntu | `sudo apt install openfpgaloader` |
| Arch Linux | `sudo pacman -S openfpgaloader` |
| Fedora | `sudo dnf copr enable mobicarte/openFPGALoader`, then `sudo dnf install openFPGALoader` |
| macOS (Homebrew) | `brew install openfpgaloader` |
| Windows (MSYS2) | `pacman -S mingw-w64-ucrt-x86_64-openFPGALoader`, then add `C:\msys64\ucrt64\bin` to the `PATH` |

An alternative on every system: OSS CAD Suite for the host also contains `openFPGALoader`. The arguments in the board profiles were checked with `openFPGALoader` v1.2.0 from the OSS CAD Suite pinned in the toolchain image.

### Linux: udev rules

Without udev rules, only root may open the board's USB adapter. Get `99-openfpgaloader.rules` from the [openFPGALoader repository](https://github.com/trabucayre/openFPGALoader), then:

```bash
grep -w plugdev /etc/group || sudo groupadd --system plugdev
sudo cp 99-openfpgaloader.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
sudo usermod -a $USER -G plugdev
```

If you would rather not use the `plugdev` group, use `70-openfpgaloader.rules` and the `dialout` group with the same steps.

Then unplug and replug the board, and log out and back in so the new group takes effect. `id $USER` must list `plugdev` (or `dialout`).

### Windows: USB driver

The official openFPGALoader guide does not cover Windows drivers. If the board is not found even though it is plugged in, the JTAG interface's driver usually has to be replaced with WinUSB using [Zadig](https://zadig.akeo.ie/). Pick interface 0 of the board; the other interface is the UART. This step has not been tested with a board in this project yet.

## Usage

The project id is in the address of the project page (`/workspace/3` means project 3). The FPGA tab also shows the full command for the run being viewed.

```bash
python tools/flash/smartx-flash --project 3
```

This loads the newest FPGA build of project 3 that produced a bitstream. Other examples:

```bash
python tools/flash/smartx-flash --run 0261944555be4fb0a28cfa49943c52c6
python tools/flash/smartx-flash --file blinky.fs --board tang-nano-9k
python tools/flash/smartx-flash --project 3 --flash
python tools/flash/smartx-flash --project 3 --dry-run
python tools/flash/smartx-flash --project 3 -- --verbose
```

In order: a specific run, a local file, writing to the board's flash permanently, only showing the command, and passing extra arguments on to openFPGALoader.

- **SRAM or flash.** Without `--flash`, the bitstream goes into SRAM: fast, but gone when the board is unplugged. That suits trying things out. With `--flash`, the design stays after the board is unplugged.
- **Backend address.** The default is `http://127.0.0.1:8000`. Change it with `--api` or the `SMARTX_API` variable.
- **Timing not met.** If the build missed its target clock, the script warns but still loads the bitstream.

The script's own messages are in Indonesian, like the rest of the SmartX user interface.

## When it fails

- **`unable to open ftdi device: -3 (device not found)`:** openFPGALoader cannot find the board. Check the cable (it must be a data cable, not a charge-only cable), then check the udev rules (Linux) or the driver (Windows) above.
- **`openFPGALoader tidak ditemukan di PATH`:** install it first, see the table above.
- **`Backend SmartX tidak bisa dihubungi`:** run `make dev`. The script needs the backend for `--file` too, because the board arguments are read from the board profile. Without the backend, call openFPGALoader directly with the arguments in the Boards table below, for example `openFPGALoader -b tangnano9k blinky.fs`.

## Boards

| Board | openFPGALoader arguments | Bitstream |
|---|---|---|
| Sipeed Tang Nano 9K (`tang-nano-9k`) | `-b tangnano9k` | `.fs` |
| Terasic DE1-SoC (`de1-soc`) | `-b de1Soc` | `.rbf` |

### DE1-SoC

The DE1-SoC is programmed through its on-board USB-Blaster II (the "USB BLASTER" port, not the "USB UART" one). Things to know, none of them tried on a board yet:

- **Probe firmware.** openFPGALoader has a `--probe-firmware` option for the USB-Blaster II (see `openFPGALoader --help`). The firmware file comes with a Quartus installation and cannot be shipped with SmartX. If openFPGALoader does not find the board, pass that file on: `python tools/flash/smartx-flash --project 3 -- --probe-firmware <path to the firmware file>`. On a lab computer where Quartus has already talked to the board since it was plugged in, the firmware may already be loaded.
- **Use SRAM.** Load without `--flash`. Writing the board's configuration flash has not been checked for the DE1-SoC.
- **The bitstream is experimental.** It comes from nextpnr-mistral, whose Cyclone V support is experimental (DECISIONS D46). If loading succeeds but the design does not run, try the `fpga-de1-soc-blinky` example first, and note what happened.
