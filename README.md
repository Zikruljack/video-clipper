# Video Clipper

CLI Python untuk membuat clip dan content pack dari video YouTube panjang. Tool ini memakai heatmap/`most replayed` YouTube, `yt-dlp`, FFmpeg, transcript `faster-whisper`, dan scoring hybrid untuk membantu kreator menemukan momen terbaik.

## Fitur

- Deteksi banyak peak heatmap per video.
- Download clip MP4 per peak tanpa download video penuh.
- Content pack untuk satu video panjang:
  - transcript full SRT/JSON
  - candidate moments
  - timeline editor-ready
  - script bilingual Indonesia/English
  - editor notes
  - optional `clipNN.mp4` export
- CLI-first, siap dikembangkan ke Web UI.
- Offline planner default; OpenAI planner akan ditambahkan setelah API key siap.

## Instalasi

```bash
python3 -m pip install -r requirements.txt
```

FFmpeg wajib tersedia di `PATH`.

Debian/Ubuntu:

```bash
sudo apt-get install ffmpeg
```

AlmaLinux/RHEL:

```bash
sudo dnf install -y python3 python3-pip ffmpeg
```

## Quick Start

### 1. Clip langsung dari heatmap

```bash
python3 heatmap_pipeline.py --url "https://www.youtube.com/watch?v=VIDEO_ID"
```

Output default:

```text
clips/<video_id>_<title>_peak01.mp4
clips/<video_id>_<title>_peak02.mp4
```

Lebih sensitif agar clip lebih banyak:

```bash
python3 heatmap_pipeline.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --k 1.0
```

### 2. Content pack dari satu video panjang

```bash
python3 heatmap_pipeline.py content-pack \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --theme "kelucuan si Bagus" \
  --formats top_n,shorts_pack \
  --languages id,en \
  --top-n 5
```

Jika `--audio-file` tidak diberikan, audio akan diunduh otomatis ke folder content pack.

### 3. Export clip assets dalam content pack

```bash
python3 heatmap_pipeline.py content-pack \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --theme "best funny moments" \
  --formats top_n \
  --export-clips
```

## Content Pack Output

```text
content_packs/<video_id>/
  content_pack.json
  timeline.json
  editor_notes.md
  script_id.md
  script_en.md
  audio/source.m4a
  clips/clip01.mp4
  clips/clip02.mp4
  transcripts/full.srt
  transcripts/full.json
  metadata/candidates.json
```

Output ini ditujukan untuk editor manual atau AI video-maker agent.

## Cheap Dry Run

Gunakan fixture transcript dan peaks agar tidak perlu download/transcribe saat test murah.

```bash
python3 heatmap_pipeline.py content-pack \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --audio-file "unused.m4a" \
  --transcript-json "transcript_fixture.json" \
  --peaks-json "peaks_fixture.json" \
  --theme "kelucuan si Bagus"
```

## Whisper Options

Default transcriber memakai `faster-whisper` jika `--transcript-json` tidak diberikan.

```bash
python3 heatmap_pipeline.py content-pack \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --theme "best moments" \
  --whisper-model small \
  --whisper-device cpu \
  --whisper-compute-type int8
```

Rekomendasi murah CPU: `small` + `cpu` + `int8`.

## Environment

Copy contoh env untuk local secret dan konfigurasi AI masa depan.

```bash
cp .env.example .env
```

`OPENAI_API_KEY` masih opsional. Versi sekarang memakai offline planner untuk ranking/script sederhana.

## Project Structure

```text
src/
  heatmap_pipeline.py      # main CLI implementation
  content_pack/            # content-pack services and exporters
heatmap_pipeline.py        # root CLI wrapper for compatibility
tests/                     # unittest suite
docs/superpowers/          # design specs and implementation plans
clips/                     # generated direct clip outputs, ignored except .gitkeep
content_packs/             # generated content packs, ignored except .gitkeep
```

## Cara Kerja

### Heatmap clipping

1. Ambil metadata YouTube via `yt-dlp` tanpa download video penuh.
2. Baca heatmap/`most replayed`.
3. Hitung threshold statistik:

```text
threshold = mean + (k * stddev)
```

4. Semua titik heatmap di atas threshold menjadi candidate clip.
5. Tambahkan buffer `--pre` dan `--post`.
6. Download section via `yt-dlp` + FFmpeg stream copy.

### Kenapa memakai heatmap?

Heatmap YouTube/`most replayed` adalah sinyal perilaku penonton. Titik yang sering diputar ulang biasanya berisi momen penting, lucu, mengejutkan, informatif, atau punya payoff. Karena itu heatmap dipakai sebagai sinyal awal untuk menemukan kandidat clip dari video panjang.

Pipeline tidak hanya mengambil nilai tertinggi absolut karena satu spike bisa saja noise atau artefak metadata. Sistem memakai threshold statistik agar semua momen yang cukup menonjol ikut diambil.

### Rumus peak detection

Untuk seluruh nilai intensitas heatmap:

```text
values = [V1, V2, V3, ..., Vn]
```

Hitung rata-rata:

```text
mean = sum(values) / len(values)
```

Hitung simpangan baku populasi:

```text
stddev = sqrt(sum((value - mean)^2) / len(values))
```

Threshold:

```text
threshold = mean + (k * stddev)
```

Titik heatmap dianggap peak jika:

```text
value >= threshold
```

Makna `k`:

- `k < 1.5`: lebih sensitif, clip lebih banyak, risiko false positive lebih tinggi.
- `k = 1.5`: default seimbang.
- `k > 1.5`: lebih konservatif, hanya spike kuat yang lolos.

Jika beberapa titik lolos threshold, semua kandidat diambil dan diurutkan berdasarkan intensitas. Output diberi suffix `peakNN` agar clip dari video yang sama tidak saling overwrite.

### Buffer clip

Setiap peak timestamp `T` diberi konteks sebelum dan sesudah momen:

```text
start = max(0, T - pre)
end = min(duration, T + post)
```

Default:

- `pre = 10` detik
- `post = 15` detik

Buffer penting karena FFmpeg stream copy tidak frame-perfect dan pemotongan mengikuti keyframe terdekat. Tanpa buffer, konteks atau punchline bisa terpotong.

### Content pack

1. Download audio full video atau pakai `--audio-file`.
2. Transcribe full audio via `faster-whisper` atau fixture JSON.
3. Ambil heatmap peaks.
4. Gabungkan heatmap windows + transcript context.
5. Score candidate dengan hybrid scoring:
   - heatmap score
   - theme relevance
   - story/context score
   - editability
   - diversity filtering
6. Export JSON, timeline, scripts, transcript, notes, dan optional clips.

## CLI Reference

### Clip mode

```bash
python3 heatmap_pipeline.py [options]
```

Options penting:

- `--url URL`: YouTube URL, bisa dipakai berulang.
- `--input-file PATH`: file berisi URL per baris.
- `--output-dir clips`: folder output.
- `--k 1.5`: sensitivitas peak detector.
- `--pre 10`: detik sebelum peak.
- `--post 15`: detik setelah peak.
- `--json`: print hasil JSON.

### Content-pack mode

```bash
python3 heatmap_pipeline.py content-pack [options]
```

Options penting:

- `--url URL`: YouTube URL sumber.
- `--theme TEXT`: tema konten.
- `--formats top_n,shorts_pack`: format output.
- `--languages id,en`: bahasa script.
- `--top-n 5`: jumlah selected moments.
- `--audio-file PATH`: pakai audio lokal.
- `--transcript-json PATH`: fixture transcript.
- `--peaks-json PATH`: fixture peaks.
- `--export-clips`: export `clipNN.mp4`.
- `--whisper-model medium`: model `faster-whisper`.
- `--whisper-device auto`: device transkripsi.
- `--whisper-compute-type default`: compute type.

## Testing

```bash
python3 -m unittest discover tests
```

## Catatan

- Tidak semua video YouTube punya heatmap.
- Stream copy tidak frame-perfect; pemotongan mengikuti keyframe.
- YouTube dapat memunculkan challenge/rate limit; gunakan delay/jitter untuk batch besar.
- Folder `clips/` dan `content_packs/` sengaja di-ignore, hanya `.gitkeep` yang masuk git.
