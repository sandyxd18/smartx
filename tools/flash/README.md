# smartx-flash

Memuat bitstream hasil Build SmartX ke board FPGA. Skrip ini dijalankan di komputer tempat board tercolok, bukan di container, karena akses USB dari Docker tidak andal (DECISIONS D09). Skrip mengambil bitstream dari backend SmartX lalu memanggil `openFPGALoader` dengan argumen dari profil board.

## Yang dibutuhkan

- Python 3.8 atau lebih baru. Skrip hanya memakai pustaka standar, jadi tidak ada yang perlu di-`pip install`.
- `openFPGALoader` di `PATH` (lihat di bawah).
- Backend SmartX berjalan (`make dev`), kecuali kalau Anda hanya ingin melihat perintahnya.

## Memasang openFPGALoader

Perintah di bawah ini dari [panduan instalasi openFPGALoader](https://trabucayre.github.io/openFPGALoader/guide/install.html).

| Sistem | Perintah |
|---|---|
| Debian / Ubuntu | `sudo apt install openfpgaloader` |
| Arch Linux | `sudo pacman -S openfpgaloader` |
| Fedora | `sudo dnf copr enable mobicarte/openFPGALoader` lalu `sudo dnf install openFPGALoader` |
| macOS (Homebrew) | `brew install openfpgaloader` |
| Windows (MSYS2) | `pacman -S mingw-w64-ucrt-x86_64-openFPGALoader`, lalu tambahkan `C:\msys64\ucrt64\bin` ke `PATH` |

Alternatif di semua sistem: OSS CAD Suite untuk host juga berisi `openFPGALoader`. Argumen di profil board dicek dengan `openFPGALoader` v1.2.0 dari OSS CAD Suite yang dipin di image toolchain.

### Linux: aturan udev

Tanpa aturan udev, hanya root yang boleh membuka adaptor USB board. Ambil `99-openfpgaloader.rules` dari [repo openFPGALoader](https://github.com/trabucayre/openFPGALoader), lalu:

```bash
grep -w plugdev /etc/group || sudo groupadd --system plugdev
sudo cp 99-openfpgaloader.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
sudo usermod -a $USER -G plugdev
```

Kalau tidak ingin memakai grup `plugdev`, pakai `70-openfpgaloader.rules` dan grup `dialout` dengan langkah yang sama.

Setelah itu cabut lalu colokkan lagi board-nya, kemudian logout dan login lagi agar grup baru berlaku. `id $USER` harus menampilkan `plugdev` (atau `dialout`).

### Windows: driver USB

Panduan resmi openFPGALoader tidak membahas driver Windows. Kalau board tidak ditemukan padahal sudah tercolok, biasanya driver interface JTAG perlu diganti ke WinUSB dengan [Zadig](https://zadig.akeo.ie/). Pilih interface 0 dari board; interface lainnya adalah UART. Langkah ini belum diuji dengan board di proyek ini.

## Pemakaian

ID proyek ada di alamat halaman proyek (`/workspace/3` berarti proyek 3). Tab FPGA juga menampilkan perintah lengkap untuk run yang sedang dibuka.

```bash
python tools/flash/smartx-flash --project 3
```

Perintah di atas memuat build FPGA terakhir proyek 3 yang menghasilkan bitstream. Contoh lain:

```bash
python tools/flash/smartx-flash --run 0261944555be4fb0a28cfa49943c52c6
python tools/flash/smartx-flash --file blinky.fs --board tang-nano-9k
python tools/flash/smartx-flash --project 3 --flash
python tools/flash/smartx-flash --project 3 --dry-run
python tools/flash/smartx-flash --project 3 -- --verbose
```

Urutannya: run tertentu, file lokal, menulis permanen ke flash board, hanya menampilkan perintah, dan meneruskan argumen tambahan ke openFPGALoader.

- **SRAM atau flash.** Tanpa `--flash`, bitstream masuk ke SRAM: cepat, tetapi hilang saat board dicabut. Ini cocok selama mencoba-coba. Dengan `--flash`, desain tetap ada setelah board dicabut.
- **Alamat backend.** Bawaannya `http://127.0.0.1:8000`. Ganti dengan `--api` atau variabel `SMARTX_API`.
- **Timing tidak tercapai.** Kalau build tidak mencapai target clock, skrip memberi peringatan tetapi tetap memuat bitstream.

## Kalau gagal

- **`unable to open ftdi device: -3 (device not found)`:** openFPGALoader tidak menemukan board. Periksa kabel (harus kabel data, bukan kabel charge saja), lalu periksa aturan udev (Linux) atau driver (Windows) di atas.
- **`openFPGALoader tidak ditemukan di PATH`:** pasang dulu, lihat tabel di atas.
- **`Backend SmartX tidak bisa dihubungi`:** jalankan `make dev`. Skrip butuh backend juga untuk `--file`, karena argumen board dibaca dari profil board. Tanpa backend, panggil openFPGALoader langsung dengan argumen di tabel Board di bawah, misalnya `openFPGALoader -b tangnano9k blinky.fs`.

## Board

| Board | Argumen openFPGALoader | Bitstream |
|---|---|---|
| Sipeed Tang Nano 9K (`tang-nano-9k`) | `-b tangnano9k` | `.fs` |
