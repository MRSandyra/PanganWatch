# Owner actions — Databricks Free Edition end-to-end runbook

Panduan ini untuk pemilik workspace. Ikuti secara berurutan dari repository lokal hingga bukti cloud. Jangan memakai layanan berbayar, object storage eksternal, atau hasil simulasi untuk melewati suatu langkah.

> **Status aktual (2026-11-11): `CLOUD_PARTIAL`.** Snapshot, manifest, schema, Bronze, Silver, DQ, Gold, source-replay reconciliation, SQL, definisi job, dan dashboard telah dieksekusi di Databricks Free Edition. Job `panganwatch_batch` menyelesaikan sembilan task dengan sukses. Mapping HDX/WFP yang dipakai adalah: hanya `National Average` menjadi kode provinsi BPS `00`; wilayah atau komoditas tanpa crosswalk tetap tercatat di governance dan tidak dipaksakan ke Silver. Source replay telah lulus, tetapi itu bukan perbandingan row-level terhadap database legacy lokal; legacy parity masih `NOT_EXECUTED`. Rincian bukti ada di [`evidence/cloud-run-20261111.md`](evidence/cloud-run-20261111.md).

## Alur untuk pemula

```text
Daftar Free Edition → kenali workspace → validasi repository lokal → login CLI OAuth
→ preflight Unity Catalog → buat snapshot + manifest → upload Volume → Bronze proof
→ lengkapi & uji Silver/DQ/Gold → rekonsiliasi → Lakeflow Job → dashboard → evidence
```

Di setiap checkpoint, hanya hasil yang benar-benar Anda lihat atau jalankan yang boleh dicatat sebagai `PASSED`. Jika hasil berbeda, berhenti pada langkah itu, simpan error yang sudah disamarkan, dan gunakan status `FAILED`, `NOT_EXECUTED`, atau `BLOCKED_BY_PLATFORM` sesuai keadaan nyata.

## Sebelum langkah 0: daftar workspace pertama Anda

1. Buka halaman resmi [Databricks Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition) menggunakan browser.
2. Pilih **Free Edition**. Jangan memilih **Free trial**, AWS Marketplace, opsi upgrade, atau opsi yang meminta kartu kredit/akun AWS, Azure, atau Google Cloud. Free Trial bukan target proyek ini karena dapat berubah menjadi layanan berbayar.
3. Daftar dengan email pribadi, ikuti verifikasi email/identitas, lalu masuk ke workspace serverless yang dibuat Databricks.
4. Salin hanya **workspace host** dari address bar, contoh `https://dbc-xxxxxxxx.cloud.databricks.com`. Jangan salin browser cookie, URL yang berisi parameter otorisasi, token OAuth, atau personal access token ke repository, file `.env`, maupun chat.
5. Pastikan sidebar workspace memiliki setidaknya **Catalog**, **Workspace**, **SQL** atau **SQL Editor**, dan **Jobs & Pipelines**. Menu **Dashboards** mungkin tergantung entitlement. Jika menu atau compute tidak ada, jangan menebak bahwa fitur tersedia—catat sebagai hasil preflight.

Free Edition menggunakan serverless compute dan fair-use quota. Bila kuota habis, stop eksekusi dan tunggu reset; jangan upgrade akun atau memakai cloud resource lain. Lihat [batas resmi Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations).

## 0. Lindungi platform lokal

1. Buka PowerShell di root project dan periksa perubahan:

   ```powershell
   Set-Location 'D:\My Life\Projects\panganwatch'
   git status --short
   git branch --show-current
   ```

2. Repository ini menggunakan branch `main` langsung. Pastikan `git branch --show-current` menampilkan `main`; jangan membuat branch baru kecuali kebijakan repository berubah. Jangan menjalankan `git reset`, menghapus perubahan pengguna, atau `docker compose down -v`.
3. MongoDB, PostgreSQL, Airflow, dbt, dan Kafka yang ada adalah baseline dan harus tetap aktif. Kafka streaming sengaja tidak masuk MVP batch Databricks.
4. Saat akses package tersedia, pulihkan environment dan jalankan validasi:

   ```powershell
   uv sync --frozen
   uv run pytest -q databricks/tests tests/unit
   uv run ruff check databricks scripts/export_frozen_snapshot.py scripts/generate_snapshot_manifest.py scripts/prepare_databricks_upload.py scripts/compare_local_cloud.py
   uv run ruff format --check databricks scripts/export_frozen_snapshot.py scripts/generate_snapshot_manifest.py scripts/prepare_databricks_upload.py scripts/compare_local_cloud.py
   ```

   Jika download dependency gagal, catat error yang sudah disanitasi sebagai `NOT_EXECUTED` di `docs/migration/11-test-execution.md`; itu bukan test pass.

## 1. Buat atau verifikasi workspace Free Edition

1. Jika Anda telah menyelesaikan bagian sebelumnya, workspace sudah ada. Konfirmasi sekali lagi bahwa workspace tersebut benar-benar **Free Edition**; jangan memulai paid trial atau menambahkan billing.
2. Salin hanya host workspace, contohnya `https://<workspace-host>`. Jangan pernah menyalin token OAuth, browser cookie, PAT, atau kredensial ke chat, Git, `.env.example`, CI, atau dokumentasi.
3. Instal Databricks CLI resmi bila belum ada. Di PowerShell/Command Prompt baru, jalankan:

   ```powershell
   winget search databricks
   winget install Databricks.DatabricksCLI
   databricks version
   ```

   Dokumentasi Databricks menyarankan CLI `0.205.0` atau lebih baru pada Windows. Jangan menginstal package Python bernama `databricks-cli` sebagai pengganti CLI resmi yang lama.

4. Login interaktif OAuth:

   ```powershell
   databricks auth login --host 'https://<workspace-host>'
   databricks current-user me
   databricks auth profiles
   ```

5. Browser akan membuka flow login. Selesaikan di browser lalu kembali ke terminal. OAuth user-to-machine pada CLI modern menyimpan token di Windows Credential Manager, bukan di repository. Rujukan: [instal CLI](https://docs.databricks.com/aws/en/dev-tools/cli/install) dan [autentikasi CLI](https://docs.databricks.com/aws/en/dev-tools/cli/authentication).
6. Jika login gagal, simpan error setelah menghapus string mirip token; periksa host pada browser. Gunakan UI browser sebagai fallback. Jangan membuat token sebagai workaround kecuali secara eksplisit didukung Free Edition dan kebijakan keamanan project.

## 2. Preflight workspace

1. Pada notebook Databricks dengan serverless compute yang tersedia, jalankan query read-only berikut:

   ```sql
   SELECT current_user(), current_catalog(), current_schema();
   SHOW CATALOGS;
   SHOW SCHEMAS IN <chosen_catalog>;
   ```

2. Pilih katalog yang memang Anda memiliki izin. Jangan mengasumsikan nama `main`. Konfigurasikan hanya katalog itu dalam session notebook:

   ```python
   import os
   os.environ["PANGANWATCH_CATALOG"] = "<chosen_catalog>"
   ```

3. Import/paste `databricks/notebooks/00_preflight.py` dan jalankan. Ia hanya boleh membuat objek berikut:

   ```text
   <catalog>.pw_landing
   <catalog>.pw_bronze
   <catalog>.pw_silver
   <catalog>.pw_gold
   <catalog>.pw_governance
   <catalog>.pw_landing.snapshots
   ```

4. Di Catalog Explorer, pastikan schema dan Unity Catalog Volume tersebut benar-benar ada. Pastikan pula serverless notebook, SQL warehouse, Jobs/Lakeflow, dan AI/BI Dashboard tersedia.
5. Buat `docs/migration/evidence/preflight-YYYYMMDD.json` dengan format berikut (host harus disamarkan):

   ```json
   {
     "test_name": "workspace_preflight",
     "execution_time_utc": "<UTC timestamp>",
     "environment": "Databricks Free Edition",
     "workspace_identifier_redacted": "<redacted host>",
     "snapshot_id": null,
     "command_or_query": "SELECT current_user(), current_catalog(), current_schema()",
     "run_id_if_available": null,
     "expected_result": "Authorized catalog and project-only schema/volume creation",
     "actual_result": "<actual observed result>",
     "status": "PASSED",
     "error_if_any": null
   }
   ```

6. Bila salah satu capability wajib tidak tersedia, gunakan status `BLOCKED_BY_PLATFORM`, perbarui `01-workspace-preflight.md`, dan jangan membuat pengganti berbayar.

## 3. Freeze satu input yang diizinkan

1. Gunakan source extract mentah yang mempunyai provenance jelas, dengan urutan prioritas:

   1. Raw file asli atau payload Bronze lokal yang bersesuaian.
   2. Snapshot raw immutable yang sudah ada.
   3. Raw file baru dari sumber yang diizinkan.
   4. Silver extract hanya untuk parity yang diberi label `SILVER_TO_GOLD_ONLY`.

2. Jangan bandingkan API yang baru direfresh dengan angka historis README. Angka 20.864 harga dan metrik lainnya adalah baseline historis, bukan target otomatis.
3. Periksa lisensi terlebih dahulu:

   | Source | `source_name` | Ketentuan |
   |---|---|---|
   | HDX/WFP Food Prices | `hdx_wfp` | CC BY-IGO; simpan attribution dan URL |
   | Open-Meteo Archive | `open_meteo` | CC BY 4.0; patuhi ketentuan free/non-commercial |
   | BPS WebAPI | `bps` | jangan upload/distribusikan sebelum terms diverifikasi |

4. Buat immutable snapshot. Folder tujuan diabaikan Git dan script menolak overwrite:

   ```powershell
   python scripts/export_frozen_snapshot.py '<path-to-raw-file>' `
     --source-name hdx_wfp `
     --source-url 'https://data.humdata.org/dataset/wfp-food-prices-for-indonesia' `
     --license CC-BY-IGO `
     --destination 'data/migration/snapshots/hdx_wfp'
   ```

5. Catat `snapshot_id` yang dicetak, lalu validasi file dan manifest:

   ```powershell
   python scripts/prepare_databricks_upload.py `
     'data/migration/snapshots/hdx_wfp/<file>' `
     'data/migration/snapshots/hdx_wfp/<file>.manifest.json' `
     --catalog workspace
   ```

   Ganti `workspace` bila preflight Anda menghasilkan nama catalog lain. Script akan mencetak target upload aktual `/Volumes/<catalog>/pw_landing/snapshots`.

6. Manifest valid memuat snapshot ID, URL/lisensi, schema version, periode, fetch UTC, format/nama file, record count, dan SHA-256. Jika checksum mismatch, jangan edit snapshot: buat snapshot baru.

## 4. Hasil baseline lokal yang fair

1. Jalankan transform legacy dengan source file frozen yang sama; simpan command, date range, mapping version, dan kondisi database sebagai evidence.
2. Export hasil lokal pada grain business key yang sama dengan tabel cloud. Untuk harga, key-nya:

   ```text
   tanggal, kode_provinsi_bps, kode_kabkota_bps, komoditas_id, jenis_pasar, source
   ```

3. Jangan menyebut Silver extract sebagai parity raw-to-Silver. Jika raw replay tidak memungkinkan, tulis dengan jelas bahwa test hanya Silver-to-Gold.

## 5. Upload snapshot ke Unity Catalog Volume

1. Buka `<catalog>.pw_landing.snapshots` pada Catalog Explorer.
2. Upload source file dan `*.manifest.json` tanpa mengubah byte atau nama file ke:

   ```text
   /Volumes/<catalog>/pw_landing/snapshots/<snapshot_id>/
   ```

3. Cocokkan ukuran file dan nama dengan manifest lokal, lalu buat evidence upload dengan snapshot ID dan volume path aktual.
4. Jangan upload `.env`, BPS API key, dump database unrelated, data personal, atau data restricted.

## 6. Buat Git folder Databricks — klik dan command persis

Bagian ini **wajib** sebelum menjalankan notebook Bronze atau berikutnya. Jangan mengunggah hanya satu file notebook karena folder `databricks/src/` juga dibutuhkan.

### 6A. Push branch lokal ke GitHub

Jika belum punya repository GitHub, lakukan ini di browser terlebih dahulu:

1. Buka `https://github.com` dan login.
2. Klik ikon **+** di kanan atas → **New repository**.
3. Isi **Repository name**: `panganwatch`.
4. Pilih **Private** bila repository belum siap dipublikasikan; pilih **Public** hanya bila semua source dan dokumentasi memang aman dibaca umum.
5. Jangan centang **Add a README file**, **Add .gitignore**, atau **Choose a license** karena proyek lokal sudah memilikinya.
6. Klik **Create repository**.
7. Salin URL HTTPS pada halaman berikutnya. Bentuknya `https://github.com/<USERNAME_ANDA>/panganwatch.git`.

Lalu buka PowerShell pada komputer lokal dan jalankan perintah ini **satu baris demi satu baris**. Ganti placeholder sebelum menekan Enter:

```powershell
Set-Location 'D:\My Life\Projects\panganwatch'
git switch main
git status --short
git diff --check
git add .gitignore README.md databricks docs/migration scripts .github/workflows/databricks-ci.yml
git status --short
git commit -m 'Add Databricks Free Edition migration foundation'
git remote -v
```

Jika `git remote -v` tidak menampilkan `origin`, tambahkan remote baru berikut **sekali saja**:

```powershell
git remote add origin 'https://github.com/<USERNAME_ANDA>/panganwatch.git'
git push -u origin main
```

Jika `origin` sudah ada dan memang menunjuk ke repository yang benar, **jangan** jalankan `git remote add`; cukup jalankan:

```powershell
git push -u origin main
```

Jika GitHub meminta autentikasi, selesaikan browser/device login yang ditampilkan Git. Jangan menempelkan GitHub token ke terminal history, dokumentasi, atau file proyek. Sebelum `git add`, periksa `git status`; jangan commit `.env`, `data/migration/snapshots/`, atau file lain yang tidak Anda kenali.

### 6B. Hubungkan akun GitHub ke Databricks

1. Kembali ke **Databricks workspace** di browser.
2. Klik ikon profil/avatar Anda di pojok kanan atas.
3. Klik **Settings**.
4. Klik tab **Linked accounts**.
5. Klik **Add Git credential**.
6. Pada **Provider**, pilih **GitHub**.
7. Pilih **Link Git account**, lalu klik **Link**.
8. Browser membuka halaman GitHub. Login bila diminta, lalu klik **Authorize Databricks**.
9. Buka halaman instalasi aplikasi Databricks GitHub bila diminta. Pilih akun GitHub Anda → pilih **Only select repositories** → centang hanya repository `panganwatch` → klik **Install**.
10. Kembali ke Databricks dan pastikan credential GitHub muncul sebagai linked account.

Databricks menyarankan GitHub App/OAuth ini untuk GitHub hosted; gunakan PAT GitHub hanya bila OAuth App tidak tersedia. [Instruksi resmi GitHub credential](https://docs.databricks.com/aws/en/repos/get-access-tokens-from-git-provider) menjelaskan alur tersebut.

### 6C. Clone menjadi Git folder di workspace

1. Pada sidebar kiri Databricks, klik **Workspace**.
2. Buka folder pengguna Anda, biasanya **Users** → `<email-Anda>`. Jika folder ini tidak tampak, pilih lokasi workspace personal yang Anda miliki akses tulisnya.
3. Klik tombol **Create** pada area Workspace. Pada sebagian UI tombolnya adalah **Create** di kanan atas; pada UI lain berupa ikon **+**.
4. Klik **Git folder**. Jangan memilih “Folder” biasa dan jangan memilih “Import”.
5. Isi dialog **Create Git folder** seperti ini:

   | Field UI | Isi |
   |---|---|
   | Git repository URL | `https://github.com/<USERNAME_ANDA>/panganwatch.git` |
   | Git provider | `GitHub` |
   | Git folder name | `panganwatch` |
   | Branch | `main` jika field branch ditampilkan; bila tidak, clone dahulu lalu pastikan branch aktif adalah `main` |
   | Sparse checkout | Biarkan nonaktif / default |

6. Klik **Create Git folder** dan tunggu clone selesai.
7. Di Workspace, buka folder `panganwatch` → `databricks` → `notebooks` → `00_preflight.py`.
8. Pastikan indikator branch/Git di dekat nama folder/notebook menampilkan `main`, lalu pilih **Pull** saat ingin mengambil commit terbaru. Jangan memilih **Reset**.
9. Pastikan struktur ini terlihat sebelum menjalankan notebook:

   ```text
   panganwatch/
     databricks/
       src/config.py
       src/bronze.py
       notebooks/00_preflight.py
       notebooks/01_bronze.py
   ```

10. Jalankan cell pertama pada `00_preflight.py`. Jika masih muncul `ModuleNotFoundError`, jangan install package apa pun: buka Git folder tersebut, lakukan **Pull**, lalu pastikan `databricks/src/config.py` benar-benar terlihat pada tree Workspace.

Databricks mendokumentasikan urutan **Workspace → Create → Git folder → repository URL/provider/folder name → Create Git folder**. Git folder memerlukan akses `CAN MANAGE` pada folder induknya dan credential Git yang sudah dikonfigurasi. [Rujukan Git folder resmi](https://docs.databricks.com/aws/en/repos/git-operations-with-repos/).

## 7. Konfigurasi dan eksekusi pipeline

1. Pilihan yang direkomendasikan adalah Git folder. Push `main` ke remote Git Anda setelah meninjau perubahan lokal, lalu di Databricks pilih **Workspace → Create → Git folder**, masukkan URL remote, dan pilih branch `main`. Git folder menyimpan notebook dan `databricks/src/` pada satu lokasi yang dapat direproduksi. Jika repository private, atur credential Git hanya di UI Databricks; jangan pernah masukkan credential Git ke repo.
2. Jika belum punya remote Git, Anda boleh mengimpor `00_preflight.py` untuk preflight manual saja. Jangan mencoba menjalankan keseluruhan workflow dari upload file acak: notebook lain perlu modul di `databricks/src/`. Buat remote Git sebelum Bronze/Silver deployment penuh.
3. Setelah Git folder dibuat, buka `databricks/notebooks/00_preflight.py` dari folder itu. Notebook akan menambahkan folder proyek ke Python path dan mengimpor `src.config` secara lokal.
4. Review `migration.yml`, `table_mapping.yml`, dan `quality_mapping.yml`. Ubah hanya nilai yang benar-benar merepresentasikan workspace/snapshot aktual; jangan hardcode URL personal atau credential.
5. Jalankan `00_preflight.py`, lalu `01_bronze.py`, dengan path manifest dan file yang diupload. Bronze harus mempunyai `_snapshot_id`, `_source_sha256`, `_source_url`, `_ingested_at`.
6. Jalankan `02_reference.py` dahulu untuk memuat CSV referensi yang sudah di-commit (`ref_provinsi`, `ref_komoditas`, dan alias HDX) ke `<catalog>.pw_reference`. Lalu jalankan `02_silver.py` dengan catalog dan run ID. Pada perbaikan pertama dari mapping provisional, set widget `rebuild_hdx_wfp` ke `true`; notebook hanya menghapus dan membangun ulang baris `source = 'hdx_wfp'` dari snapshot yang sama, lalu menyimpan nilai tanpa alias ke `<catalog>.pw_governance.hdx_wfp_unmapped_geography`. Setelah itu set kembali `false` untuk run biasa.
7. Untuk menjalankan mart Gold yang melibatkan cuaca, buat dulu snapshot Open-Meteo dengan rentang yang sama dengan WFP. Gunakan `02_weather_silver.py` setelah Bronze Open-Meteo tersedia. Open-Meteo Historical API menerima beberapa koordinat, interval tanggal, dan agregasi daily; gunakan model `era5` agar data multi-dekade konsisten. Simpan atribusi Open-Meteo/ERA5 serta lisensi CC BY 4.0 pada manifest/evidence.
8. Setelah `harga_pangan` dan `cuaca_harian` tersedia, jalankan `03_quality.py` dengan catalog dan run ID batch yang sama. Ia mengevaluasi rule harga dan cuaca dari `config/dq_rules.yml`, menulis hasil ke `pw_governance.dq_results`, menulis kegagalan error ke `pw_governance.quarantine`, dan memblokir Gold bila ada error. `HP-012` dan `HP-014` tetap warning.
8. Jalankan `04_gold.py` hanya jika DQ gate tidak punya error. Validasi staging sebelum publish menggantikan Gold PanganWatch.
9. Jalankan `05_reconciliation.py` setelah Gold. Ia melakukan **SOURCE_REPLAY**: membangun ulang expected Silver dari Bronze snapshot dan referensi committed lalu membandingkan record contract field dengan tabel Silver pada toleransi nol. Hasil ringkasan berada di `<catalog>.pw_governance.reconciliation_results`. Ini membuktikan replay cloud, bukan klaim parity terhadap database legacy lokal; gunakan `compare_local_cloud.py` hanya setelah export legacy yang benar-benar se-grain tersedia.

### Jika muncul `ModuleNotFoundError: No module named 'databricks.src'`

Jangan menginstal package bernama `databricks` atau `databricks.src`. Nama `databricks` sudah dipakai package bawaan runtime, sehingga import lama berbenturan dengan package proyek.

1. Pastikan Anda membuka notebook dari Git folder yang berisi **seluruh** repository, bukan file `00_preflight.py` yang diimpor sendirian.
2. Pastikan struktur di Workspace/Git folder tetap `.../databricks/notebooks/00_preflight.py` dan `.../databricks/src/config.py`.
3. Pull branch `main` yang berisi perbaikan import ini, lalu buka ulang notebook. Notebook sekarang menurunkan path Git folder secara otomatis dan memakai `from src.config import ...`.
4. Bila Anda belum memakai Git folder, gunakan preflight SQL pada langkah 2 terlebih dahulu. Jangan menjalankan Bronze/Silver sampai seluruh folder `databricks/src/` tersedia pada runtime.

## 8. Buat Lakeflow Job manual

Lakukan bagian ini **hanya** setelah setiap notebook sudah berhasil jika dijalankan sendiri. Definisi YAML di repository adalah referensi; YAML tersebut belum otomatis menciptakan job.

1. Di sidebar kiri, klik **Jobs & Pipelines**.
2. Klik **Create** → **Job**.
3. Pada task pertama, klik tile **Notebook**. Jika tile tidak ada, klik **Add another task type**, cari `Notebook`, lalu pilih.
4. Isi **Task name**: `validate_workspace`.
5. Klik field **Path** → navigasikan ke Git folder `panganwatch/databricks/notebooks/00_preflight.py` → pilih notebook tersebut.
6. Pada bagian **Compute**, pilih **Serverless** bila opsi ini tersedia. Jangan membuat classic cluster atau memilih cloud compute berbayar.
7. Pada panel **Job details** → **Parameters**, tambahkan parameter job berikut. Nilai ini otomatis diteruskan ke Notebook tasks; jangan masukkan token atau secret.

   | Name | Value |
   |---|---|
   | `catalog` | `workspace` |
   | `wfp_manifest_path` | `/Volumes/workspace/pw_landing/snapshots/hdx_wfp/wfp_food_prices_idn.csv.manifest.json` |
   | `wfp_snapshot_path` | `/Volumes/workspace/pw_landing/snapshots/hdx_wfp/wfp_food_prices_idn.csv` |
   | `weather_manifest_path` | `/Volumes/workspace/pw_landing/snapshots/open_meteo/open_meteo_era5_20070115_20260615.jsonl.manifest.json` |
   | `weather_snapshot_path` | `/Volumes/workspace/pw_landing/snapshots/open_meteo/open_meteo_era5_20070115_20260615.jsonl` |
8. Klik **Save task**. Job baru biasanya bernama `New Job <tanggal waktu>`; klik namanya di halaman job dan ubah menjadi `panganwatch_batch`.
9. Klik **Add task** dan ulangi proses untuk tiap task berikut. Pilih path notebook yang sesuai, lalu pada panel dependency pilih task pendahulunya:

   ```text
   validate_workspace → {load_reference, load_wfp_bronze, load_weather_bronze}
   → {build_wfp_silver, build_weather_silver} → run_quality → build_gold → reconcile_and_record
   ```

   | Task name | Notebook path | Depends on |
   |---|---|---|
   | `validate_workspace` | `databricks/notebooks/00_preflight.py` | — |
   | `load_reference` | `databricks/notebooks/02_reference.py` | `validate_workspace` |
   | `load_wfp_bronze` | `databricks/notebooks/01_bronze.py` | `validate_workspace` |
   | `load_weather_bronze` | `databricks/notebooks/01_bronze.py` | `validate_workspace` |
   | `build_wfp_silver` | `databricks/notebooks/02_silver.py` | `load_reference`, `load_wfp_bronze` |
   | `build_weather_silver` | `databricks/notebooks/02_weather_silver.py` | `load_weather_bronze` |
   | `run_quality` | `databricks/notebooks/03_quality.py` | `build_wfp_silver`, `build_weather_silver` |
   | `build_gold` | `databricks/notebooks/04_gold.py` | `run_quality` |
   | `reconcile_and_record` | `databricks/notebooks/05_reconciliation.py` | `build_gold` |

10. Buka panel **Job details**. Set **Max concurrent runs** ke `1`.
11. Jangan isi Schedule/Trigger; defaultnya manual. Untuk retry, pilih hanya error sementara platform/API. Jangan retry otomatis ketika DQ error atau manifest tidak valid.
12. Pada task `load_wfp_bronze`, masukkan task parameters `snapshot_manifest_path = {{job.parameters.wfp_manifest_path}}` dan `local_file_path = {{job.parameters.wfp_snapshot_path}}`. Pada `load_weather_bronze`, gunakan parameter yang sama tetapi dengan `weather_manifest_path` dan `weather_snapshot_path`. Pada `build_wfp_silver`, set `rebuild_hdx_wfp = false` serta `run_id = job_{{job.run_id}}`. Pada `build_weather_silver`, `run_quality`, `build_gold`, dan `reconcile_and_record`, set `run_id = job_{{job.run_id}}`. Semua task menerima `catalog` dari job parameter. Jangan mengetik token/secret pada parameter job.
13. Klik **Run now** hanya sekali untuk snapshot yang telah diverifikasi. Klik nama run untuk melihat log setiap task.
14. Simpan URL job, run ID, waktu mulai/selesai, task result, log tersanitasi, serta screenshot nyata. Jika salah satu task gagal, downstream task harus tidak berjalan.

Jobs UI resmi mengikuti pola **Jobs & Pipelines → Create → Job → Notebook → Task name → Path → Save task**; schedule boleh dibiarkan kosong agar job manual. [Referensi Lakeflow Jobs](https://docs.databricks.com/aws/en/jobs/configure-job).

## 9. Verifikasi cloud dan idempotency

Jalankan query berikut pada Databricks SQL:

```sql
SELECT COUNT(*) AS rows,
       COUNT(DISTINCT concat_ws('|', tanggal, kode_provinsi_bps,
         coalesce(kode_kabkota_bps, ''), komoditas_id, jenis_pasar, source)) AS distinct_keys
FROM <catalog>.pw_silver.harga_pangan;

SELECT rule_id, severity, rows_checked, rows_failed, pass_rate
FROM <catalog>.pw_governance.dq_results
WHERE run_id = '<run_id>'
ORDER BY rule_id;

SELECT COUNT(*) AS quarantined
FROM <catalog>.pw_governance.quarantine
WHERE run_id = '<run_id>';
```

Rerun snapshot yang sama sekali lagi. Jumlah logical business key Bronze/Silver/Gold tidak boleh naik. Jika berubah, tandai `FAILED`, hentikan publication, dan investigasi.

## 10. Rekonsiliasi local versus cloud

1. Export cloud table/mart ke JSON atau JSONL pada grain yang sama dengan export lokal.
2. Jalankan:

   ```powershell
   python scripts/compare_local_cloud.py '<local.jsonl>' '<cloud.jsonl>' `
     --keys 'tanggal,kode_provinsi_bps,kode_kabkota_bps,komoditas_id,jenis_pasar,source' `
     --output 'docs/migration/evidence/reconciliation-<snapshot_id>.json'
   ```

3. Count, key, date, dan kategori harus exact. Decimal harus sesuai presisi source. Statistik float membutuhkan toleransi kecil yang terdokumentasi.
4. Mismatch adalah finding yang harus disimpan (`OPEN`, `EXPLAINED`, atau `RESOLVED`), bukan dihapus. Jangan mengklaim parity bila masih ada mismatch material tanpa penjelasan.

## 11. Buat dashboard Databricks SQL / AI-BI

Jangan mulai dashboard sebelum query Gold dan rekonsiliasi benar-benar lulus. Dashboard membutuhkan SQL entitlement dan akses **CAN USE** ke SQL warehouse.

1. Di sidebar klik **SQL** atau **SQL Editor**.
2. Buat query baru, pilih SQL warehouse serverless yang tersedia, lalu jalankan query Gold terverifikasi. Simpan query dengan nama yang jelas, misalnya `pw_dashboard_coverage`.
3. Di sidebar klik **New** → **Dashboard**.
4. Dashboard baru membuka tab **Data**. Klik **Add dataset** atau tombol sejenis, pilih **New dataset from SQL**, lalu paste query Gold yang telah Anda uji di langkah 2. Klik **Run**, periksa tabel hasil, lalu beri nama dataset yang jelas.
5. Klik tab **Canvas** atau halaman `Untitled page`. Klik **Add a visualization**, pilih dataset, pilih tipe chart, lalu isi axis/metric dari hasil query.
6. Klik **Add a filter** untuk filter `bulan/periode`, `kode_provinsi_bps`, dan `komoditas_id` bila field tersedia. Jangan menawarkan filter yang tidak ada pada dataset.
7. Label setiap visual dengan unit dan cakupan nyata, termasuk periode data. Tambahkan text widget untuk caveat 34/38 provinsi, komoditas tidak lengkap, dan “correlation, not causation” pada bagian cuaca.
8. Dashboard wajib mencakup:

   - Executive Overview: coverage, periode terbaru, price trend, coverage provinsi/komoditas.
   - Regional Price Disparity: commodity/province comparison, median deviation, period filter.
   - Weather and Food Prices: association/lag, sample size, dan teks “correlation, not causation”.
   - Inflation Comparison: cakupan geography/periode dan caveat source.
   - Data Quality: rule outcome, coverage gap, freshness, quarantine/incident.

9. Cocokkan nilai setiap KPI dashboard dengan hasil SQL yang sama. Jangan memakai placeholder, angka README historis yang tidak berasal dari query cloud, atau klaim cakupan lengkap.
10. Klik **Publish** di kanan atas → pilih **Share with data permissions** → klik **Publish**. Tambahkan hanya pengguna/grup yang memang perlu melihatnya; jangan membuka akses publik.
11. Klik **Copy link**, buka link di tab baru untuk memeriksa dashboard published, lalu simpan screenshot asli (tanpa informasi sensitif) dalam `docs/migration/evidence/`.

UI dashboard resmi dimulai dari **New → Dashboard** dan menyimpan draft di workspace user. [Tutorial dashboard Databricks](https://docs.databricks.com/aws/en/dashboards/tutorials/create-dashboard) menjelaskan prerequisite warehouse dan publishing.

## 12. Evidence, status, dan sign-off

1. Buat satu evidence record per cloud action dengan field di `docs/migration/evidence/README.md`.
2. Perbarui `01-workspace-preflight.md`, `04-implementation-log.md`, `06-parity-report.md`, `07-data-quality-report.md`, `08-cost-and-limitations.md`, `10-final-verification.md`, dan `11-test-execution.md` dengan hasil aktual saja.
3. Gunakan status secara tepat:

   | Status | Arti |
   |---|---|
   | `NOT_EXECUTED` | test/action belum dijalankan |
   | `BLOCKED_BY_PLATFORM` | access, quota, atau fitur Free Edition menghalangi |
   | `CLOUD_PARTIAL` | beberapa komponen cloud nyata berhasil, namun verifikasi wajib belum lengkap |
   | `CLOUD_VERIFIED` | Bronze/Silver/Gold/DQ/reconciliation/Lakeflow yang diwajibkan benar-benar pass |
   | `PORTFOLIO_READY` | cloud verification, dashboard nyata, screenshot, dan dokumentasi lengkap |

4. Jangan memberi label `CLOUD_VERIFIED` atau `PORTFOLIO_READY` dari notebook yang belum dieksekusi, simulasi lokal, atau desain dashboard.

## 13. Cleanup project-only (opsional)

Lakukan hanya setelah evidence disimpan dan owner menyetujui. Hapus satu objek PanganWatch yang sudah dikonfirmasi pada satu waktu; jangan menghapus catalog/workspace atau volume legacy:

```sql
DROP TABLE IF EXISTS <catalog>.pw_gold.mart_inflasi_vs_harga;
```

Hapus folder volume `<snapshot_id>` hanya setelah retention review. Jangan menjalankan recursive cleanup terhadap root catalog, data workspace lain, atau Docker volume legacy.
