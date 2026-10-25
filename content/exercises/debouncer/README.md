# Debouncer tombol

Tombol mekanis "memantul": saat ditekan, sinyalnya berganti 0/1 beberapa kali sebelum
stabil. Debouncer hanya meneruskan perubahan yang bertahan cukup lama. Buat modul `debounce`:

| Port    | Arah   | Lebar | Keterangan |
|---------|--------|-------|------------|
| `clk`   | input  | 1     | clock, aktif di sisi naik |
| `rst`   | input  | 1     | reset sinkron, aktif tinggi: `clean = 0` |
| `btn`   | input  | 1     | sinyal tombol mentah (bisa memantul) |
| `clean` | output | 1     | sinyal tombol yang sudah stabil |

Aturan: `clean` berubah menjadi nilai `btn` pada sisi naik clock ke-**4 berturut-turut**
di mana `btn` berbeda dari `clean`. Kalau di tengah jalan `btn` kembali sama dengan `clean`,
hitungan mulai dari awal.

Contoh, dengan `clean = 0`: `btn` = `1 1 0 1 1 1 1` membuat `clean` menjadi 1 tepat pada
bit ketujuh (hitungan diulang karena ada `0` di bit ketiga).
