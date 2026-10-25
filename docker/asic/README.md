# Image ASIC (Fase 5)

Image heavy untuk LibreLane + PDK tidak dibangun di repo ini. Default: `hpretl/iic-osic-tools` dengan tag yang dipin di `.env` (`ASIC_IMAGE`).

Sebelum Fase 5 dimulai:
1. Pilih tag terbaru yang stabil dan pin di `.env`.
2. Cek versi LibreLane dan lokasi PDK di dalam image, catat di `docs/notes/asic-manual-run.md`.
3. Jika versi LibreLane tidak cocok dengan kebutuhan shuttle Tiny Tapeout yang dituju, pakai metode instalasi resmi LibreLane dan perbarui `DECISIONS.md` (D07).
