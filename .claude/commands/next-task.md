---
description: Ambil task berikutnya dari fase aktif dan kerjakan sampai selesai
---

1. Baca `docs/ROADMAP.md` dan tentukan fase aktif (fase pertama yang belum `[x]`). Tandai `[~]` jika masih `[ ]`.
2. Buka `docs/phases/` untuk fase itu. Ambil task pertama yang belum selesai.
3. Sebelum menulis kode, ringkas dalam 3–5 baris apa yang akan dibuat, file mana yang disentuh, dan bagaimana mengujinya. Jika task bergantung pada CLI atau format file tool EDA, cek dulu `--help`/dokumentasi versi yang dipin.
4. Implementasikan dengan test. Jalankan pemeriksaan yang relevan (`make check` jika sudah tersedia).
5. Jika semua hijau: centang task, commit, dan laporkan singkat apa yang selesai dan apa yang perlu dicek manual oleh pemilik (mis. tampilan UI, board fisik).
6. Jika terhalang (tool berperilaku beda dari dokumen, butuh keputusan pemilik): berhenti, jelaskan masalahnya, dan usulkan pilihan.

$ARGUMENTS
