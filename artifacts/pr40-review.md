# Review: PR #40 — security(workplaces): rate-limit unauthenticated connector pairing

- **Author:** DeryFerd (Dery Ferdika)
- **Branch:** `security/rate-limit-connector-pairing` -> `main`
- **Status:** OPEN, mergeable
- **Files changed:** 4 (85 additions, 0 deletions)
- **Reviewer:** Aisyah

---

## Summary

PR menambahkan rate limiter per-IP untuk endpoint `POST /api/connector/pair` yang saat ini tidak terautentikasi. Rate limiter membatasi maksimal 30 percobaan pairing per IP dalam jendela 300 detik (sama dengan TTL pairing code), untuk mencegah brute-force tebak pairing code.

---

## Files Changed

| File | Type | Additions |
|------|------|-----------|
| `backend/connector_pair_rate_limit.py` | ADDED | 42 |
| `config.py` | MODIFIED | 1 |
| `routes/workplaces.py` | MODIFIED | 7 |
| `unit_tests/test_connector_pair_rate_limit.py` | ADDED | 35 |

---

## Detailed Review

### 1. `backend/connector_pair_rate_limit.py` — New module

#### Strengths
- **time.monotonic()** digunakan sebagai ganti time.time(). Benar — tidak terpengaruh perubahan jam sistem.
- **Thread-safe** menggunakan threading.Lock. Konsisten dengan pattern login rate limiter yang sudah ada di auth.py.
- **Pruning timestamps** dilakukan setiap kali `is_rate_limited()` dipanggil, mencegah unbounded memory growth.
- **API surface** simpel: hanya 3 fungsi publik + 1 helper, mudah di-test dan dipahami.

#### Concerns
- **Race condition minor:** `is_rate_limited()` dan `record_attempt()` dipanggil terpisah di routes/workplaces.py. Dalam skenario konkurensi tinggi, bisa ada N+1 request yang lolos. Solusi: buat fungsi atomik `check_and_record()` yang menggabungkan keduanya dalam satu lock.
- **getattr fallback:** `getattr(config, 'CONNECTOR_PAIR_MAX_ATTEMPTS', 30)` akan silent fallback ke 30 jika config belum di-load. Lebih baik import langsung `from config import CONNECTOR_PAIR_MAX_ATTEMPTS` atau `import config` dan panggil `config.CONNECTOR_PAIR_MAX_ATTEMPTS`.
- **Per-worker state:** Seperti login limiter, state in-memory per process. Multi-worker deployment tanpa sticky sessions akan memiliki limit per worker, bukan global.

### 2. `config.py` — Modified

✅ **Clean.** Menambahkan `CONNECTOR_PAIR_MAX_ATTEMPTS` dengan env var, default 30, min 5, max 200. Konsisten dengan pattern config yang sudah ada (menggunakan `_get_env_int()`).

### 3. `routes/workplaces.py` — Modified

#### Strengths
- Rate limit check ditempatkan SEBELUM parsing JSON dan lookup pairing code — efisien, tidak membuang resource untuk request yang akan di-reject.
- IP fallback ke `'0.0.0.0'` jika `request.remote_addr` None.
- Return HTTP 429 dengan error message — standar dan sesuai pola existing endpoints.

#### Concerns
- **No logging:** Tidak ada log ketika rate limit terpicu. Berguna untuk monitoring dan debugging false positives. Sebaiknya tambahkan `app.logger.warning()`.
- **Global fallback risk:** Jika `request.remote_addr` None (misal di test environment), semua traffic akan terpetakan ke satu IP `'0.0.0.0'`. Sebaiknya fallback berbeda (misal `'unknown'`) dan/atau warning log.
- **Race condition window:** Seperti disebut di atas, `is_rate_limited()` lalu `record_attempt()` secara terpisah.

### 4. `unit_tests/test_connector_pair_rate_limit.py` — New module

#### Strengths
- 3 test cases: under-limit, at-limit, per-IP isolation.
- `setUp()` reset state tiap test.
- Clean, readable.

#### Gaps
- **No window expiry test:** Tidak ada test yang memverifikasi bahwa timestamp expired benar-benar dihapus.
- **No concurrent test:** Tidak ada test untuk memvalidasi thread safety (acceptable untuk unit test sederhana, tapi nice to have).
- **No edge case test:** Tidak test untuk IP = `'0.0.0.0'` fallback behavior.

---

## Security Assessment

### Threat Model
- **Attacker:** Dapat mengirim request ke endpoint unauthenticated untuk menebak pairing code.
- **Mitigation:** Per-IP rate limiting via in-memory counter.

### Effectiveness
- 30 attempts per 300 detik = 6 attempts/menit per IP.
- Pairing code: 6 karakter, alphabet huruf besar + digit (minus ambiguous chars). Estimasi ~16M kemungkinan.
- Brute-force dari satu IP dalam jendela 5 menit: 30 percobaan vs ~16M kemungkinan → **tidak feasible.**
- Jika attacker menggunakan botnet (banyak IP), masing-masing tetap mendapat 30 percobaan. Rate limiter adalah **defense-in-depth**, bukan solusi tunggal.

### Risk of False Positives
- Office NAT dengan satu public IP bersama bisa mencapai limit jika banyak connector pairing bersamaan.
- Mitigasi: `CONNECTOR_PAIR_MAX_ATTEMPTS` bisa dinaikkan via env var.

### Consistency with Existing Patterns
- ✅ Mirip dengan login rate limiter di `auth.py` (in-memory, threading.Lock, pruning timestamps).
- ✅ Error response format konsisten: `jsonify({'error': '...'})` dengan status code.
- ⚠️ Login limiter punya `_clear_attempts()` untuk reset setelah sukses. Pairing tidak punya — wajar karena tidak ada "sukses login" yang terdeteksi (unauthenticated).

---

## Recommendations

1. **Minor — Atomic check-and-record:** Gabungkan `is_rate_limited()` dan `record_attempt()` dalam satu fungsi `check_and_record(ip)` untuk menghilangkan race condition window.
2. **Minor — Add logging:** Tambahkan log warning ketika rate limit terpicu (gunakan `app.logger.warning()` atau `print()` ke stderr untuk visibility).
3. **Suggestion — Window expiry test:** Tambahkan test yang memverifikasi timestamp pruning bekerja dengan benar.
4. **Suggestion — Import pattern:** Ganti `getattr(config, ...)` dengan direct import dari config modul untuk menghindari silent fallback.

---

## Verdict

**APPROVED with minor suggestions.**

Implementasi solid, mengikuti pattern yang sudah ada, threat model jelas, mitigasi efektif untuk single-IP brute force. Saran-saran di atas bersifat opsional dan bisa diimplementasikan di PR terpisah atau sebagai follow-up.

---

Best,
Aisyah
--
Robin Syihab's agent.
