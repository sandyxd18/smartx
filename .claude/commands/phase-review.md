---
description: Periksa apakah fase aktif sudah memenuhi semua kriteria selesai
---

1. Tentukan fase aktif dari `docs/ROADMAP.md` (atau fase yang disebut di argumen).
2. Untuk setiap butir di bagian "Kriteria selesai" file fase itu, kumpulkan bukti: jalankan perintah/test terkait dan kutip hasilnya. Butir yang hanya bisa dicek manusia (UI, hardware) ditandai "perlu dicek manual" beserta langkah ceknya.
3. Jalankan `make check`.
4. Laporkan tabel: kriteria, status (terbukti / gagal / perlu dicek manual), bukti.
5. Jangan menandai fase `[x]` di ROADMAP kecuali semua kriteria terbukti atau sudah dikonfirmasi pemilik.

$ARGUMENTS
