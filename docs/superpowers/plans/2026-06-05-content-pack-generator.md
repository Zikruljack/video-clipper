# Content Pack Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI-first content pack generator that converts one long YouTube video into transcript, hybrid-ranked clips, bilingual scripts, timeline, and editor-ready metadata.

**Architecture:** Add focused modules around the existing heatmap pipeline instead of growing one large file. Core services are CLI-independent so a future Web UI can call the same orchestration code. MVP supports deterministic local components plus an optional LLM adapter interface with a cheap offline fallback for tests and dry runs.

**Tech Stack:** Python 3, `unittest`, `yt-dlp`, optional `faster-whisper`, optional OpenAI-compatible reasoning provider, JSON/Markdown/SRT exports.

---

## File Structure

- Create `content_pack/__init__.py`: package exports.
- Create `content_pack/models.py`: dataclasses for transcript segments, candidates, selected clips, scripts, pack metadata.
- Create `content_pack/srt.py`: SRT formatting/parsing helpers.
- Create `content_pack/transcriber.py`: `faster-whisper` wrapper plus deterministic transcript fixture loader.
- Create `content_pack/candidates.py`: merge heatmap peaks and transcript context into candidate moments.
- Create `content_pack/scoring.py`: hybrid score, diversity filtering, format-aware selection.
- Create `content_pack/llm.py`: provider interface, offline fallback, optional OpenAI adapter stub.
- Create `content_pack/exporter.py`: write folder structure, JSON, Markdown, SRT, clip exports.
- Create `content_pack/orchestrator.py`: end-to-end content pack workflow.
- Modify `heatmap_pipeline.py`: add `content-pack` subcommand while preserving existing URL clipping CLI.
- Test `tests/test_content_pack_*.py`: focused unit tests for each module.
- Modify `README.md`: add CLI usage and output structure.

---

### Task 1: Core Models

**Files:**
- Create: `content_pack/__init__.py`
- Create: `content_pack/models.py`
- Test: `tests/test_content_pack_models.py`

- [ ] **Step 1: Write failing model serialization tests**

Create `tests/test_content_pack_models.py`:

```python
import unittest

from content_pack.models import CandidateMoment, TranscriptSegment


class ContentPackModelTests(unittest.TestCase):
    def test_transcript_segment_serializes_to_dict(self):
        segment = TranscriptSegment(start=1.25, end=4.5, text="Halo world", language="mixed")

        self.assertEqual(
            segment.to_dict(),
            {"start": 1.25, "end": 4.5, "text": "Halo world", "language": "mixed"},
        )

    def test_candidate_moment_serializes_scores_and_transcript(self):
        candidate = CandidateMoment(
            candidate_id="cand001",
            source_start=10.0,
            source_end=40.0,
            peak_timestamp=22.0,
            heatmap_value=0.9,
            transcript=[TranscriptSegment(start=11.0, end=13.0, text="Lucu sekali", language="id")],
            scores={"heatmap_score": 1.0, "theme_score": 0.8},
        )

        payload = candidate.to_dict()

        self.assertEqual(payload["candidate_id"], "cand001")
        self.assertEqual(payload["source_start"], 10.0)
        self.assertEqual(payload["source_end"], 40.0)
        self.assertEqual(payload["transcript"][0]["text"], "Lucu sekali")
        self.assertEqual(payload["scores"]["theme_score"], 0.8)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_content_pack_models
```

Expected: FAIL with `ModuleNotFoundError: No module named 'content_pack'`.

- [ ] **Step 3: Implement models**

Create `content_pack/__init__.py`:

```python
"""Content pack generation package."""
```

Create `content_pack/models.py`:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str
    language: str = "mixed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CandidateMoment:
    candidate_id: str
    source_start: float
    source_end: float
    peak_timestamp: float | None
    heatmap_value: float | None
    transcript: list[TranscriptSegment]
    scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["transcript"] = [segment.to_dict() for segment in self.transcript]
        return payload


@dataclass(frozen=True)
class SelectedClip:
    clip_id: str
    format_name: str
    rank: int
    source_start: float
    source_end: float
    candidate_id: str
    title_id: str
    title_en: str
    narration_id: str
    narration_en: str
    scores: dict[str, float]
    local_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["local_path"] = str(self.local_path) if self.local_path else None
        return payload


@dataclass(frozen=True)
class ContentPack:
    video_id: str
    source_url: str
    title: str | None
    theme: str | None
    formats: list[str]
    languages: list[str]
    clips: list[SelectedClip]
    candidates: list[CandidateMoment]
    output_dir: Path

    def to_dict(self) -> dict[str, Any]:
        return {
            "video_id": self.video_id,
            "source_url": self.source_url,
            "title": self.title,
            "theme": self.theme,
            "formats": self.formats,
            "languages": self.languages,
            "clips": [clip.to_dict() for clip in self.clips],
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "output_dir": str(self.output_dir),
        }
```

- [ ] **Step 4: Run model tests**

Run:

```bash
python3 -m unittest tests.test_content_pack_models
```

Expected: PASS with `Ran 2 tests`.

- [ ] **Step 5: Commit**

Run only if this directory is a git worktree:

```bash
git add content_pack/__init__.py content_pack/models.py tests/test_content_pack_models.py
git commit -m "feat: add content pack core models"
```

---

### Task 2: SRT Utilities

**Files:**
- Create: `content_pack/srt.py`
- Test: `tests/test_content_pack_srt.py`

- [ ] **Step 1: Write failing SRT tests**

Create `tests/test_content_pack_srt.py`:

```python
import unittest

from content_pack.models import TranscriptSegment
from content_pack.srt import format_srt_timestamp, segments_to_srt


class ContentPackSrtTests(unittest.TestCase):
    def test_format_srt_timestamp_uses_hours_minutes_seconds_millis(self):
        self.assertEqual(format_srt_timestamp(3661.234), "01:01:01,234")

    def test_segments_to_srt_exports_numbered_blocks(self):
        srt = segments_to_srt([
            TranscriptSegment(start=0.0, end=1.5, text="Halo", language="id"),
            TranscriptSegment(start=2.0, end=3.25, text="World", language="en"),
        ])

        self.assertEqual(
            srt,
            "1\n00:00:00,000 --> 00:00:01,500\nHalo\n\n2\n00:00:02,000 --> 00:00:03,250\nWorld\n",
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_content_pack_srt
```

Expected: FAIL with `ModuleNotFoundError: No module named 'content_pack.srt'`.

- [ ] **Step 3: Implement SRT utilities**

Create `content_pack/srt.py`:

```python
from __future__ import annotations

from content_pack.models import TranscriptSegment


def format_srt_timestamp(seconds: float) -> str:
    milliseconds_total = int(round(seconds * 1000))
    hours, remainder = divmod(milliseconds_total, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{milliseconds:03d}"


def segments_to_srt(segments: list[TranscriptSegment]) -> str:
    blocks: list[str] = []
    for index, segment in enumerate(segments, start=1):
        blocks.append(
            f"{index}\n"
            f"{format_srt_timestamp(segment.start)} --> {format_srt_timestamp(segment.end)}\n"
            f"{segment.text}\n"
        )
    return "\n".join(blocks)
```

- [ ] **Step 4: Run SRT tests**

Run:

```bash
python3 -m unittest tests.test_content_pack_srt
```

Expected: PASS with `Ran 2 tests`.

- [ ] **Step 5: Commit**

Run only if this directory is a git worktree:

```bash
git add content_pack/srt.py tests/test_content_pack_srt.py
git commit -m "feat: add content pack srt utilities"
```

---

### Task 3: Transcript Loader And Faster-Whisper Wrapper

**Files:**
- Create: `content_pack/transcriber.py`
- Test: `tests/test_content_pack_transcriber.py`

- [ ] **Step 1: Write failing transcriber tests**

Create `tests/test_content_pack_transcriber.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from content_pack.transcriber import JsonTranscriptLoader


class ContentPackTranscriberTests(unittest.TestCase):
    def test_json_transcript_loader_reads_segments(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "transcript.json"
            path.write_text(
                json.dumps([
                    {"start": 0, "end": 2.5, "text": "Halo", "language": "id"},
                    {"start": 3, "end": 4, "text": "hello", "language": "en"},
                ]),
                encoding="utf-8",
            )

            segments = JsonTranscriptLoader(path).transcribe(Path("unused.m4a"))

        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].text, "Halo")
        self.assertEqual(segments[1].language, "en")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_content_pack_transcriber
```

Expected: FAIL with `ModuleNotFoundError: No module named 'content_pack.transcriber'`.

- [ ] **Step 3: Implement transcriber interfaces**

Create `content_pack/transcriber.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from content_pack.models import TranscriptSegment


class Transcriber(Protocol):
    def transcribe(self, audio_path: Path) -> list[TranscriptSegment]:
        ...


class JsonTranscriptLoader:
    def __init__(self, transcript_path: Path) -> None:
        self.transcript_path = transcript_path

    def transcribe(self, audio_path: Path) -> list[TranscriptSegment]:
        payload = json.loads(self.transcript_path.read_text(encoding="utf-8"))
        return [
            TranscriptSegment(
                start=float(item["start"]),
                end=float(item["end"]),
                text=str(item["text"]),
                language=str(item.get("language", "mixed")),
            )
            for item in payload
        ]


class FasterWhisperTranscriber:
    def __init__(self, model_size: str = "medium", device: str = "auto", compute_type: str = "default") -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

    def transcribe(self, audio_path: Path) -> list[TranscriptSegment]:
        try:
            from faster_whisper import WhisperModel
        except ModuleNotFoundError as exc:
            raise RuntimeError("faster-whisper belum terpasang. Jalankan: python3 -m pip install faster-whisper") from exc

        model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        raw_segments, _info = model.transcribe(str(audio_path), vad_filter=True)
        return [
            TranscriptSegment(
                start=float(segment.start),
                end=float(segment.end),
                text=segment.text.strip(),
                language="mixed",
            )
            for segment in raw_segments
            if segment.text.strip()
        ]
```

- [ ] **Step 4: Run transcriber tests**

Run:

```bash
python3 -m unittest tests.test_content_pack_transcriber
```

Expected: PASS with `Ran 1 test`.

- [ ] **Step 5: Commit**

Run only if this directory is a git worktree:

```bash
git add content_pack/transcriber.py tests/test_content_pack_transcriber.py
git commit -m "feat: add content pack transcriber interface"
```

---

### Task 4: Candidate Builder

**Files:**
- Create: `content_pack/candidates.py`
- Test: `tests/test_content_pack_candidates.py`

- [ ] **Step 1: Write failing candidate tests**

Create `tests/test_content_pack_candidates.py`:

```python
import unittest

from content_pack.candidates import CandidateBuilder
from content_pack.models import TranscriptSegment
from heatmap_pipeline import PeakResult


class ContentPackCandidateTests(unittest.TestCase):
    def test_builder_creates_candidate_with_nearby_transcript(self):
        peak = PeakResult(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="demo",
            timestamp=50.0,
            value=0.9,
            mean=0.2,
            stddev=0.1,
            threshold=0.35,
            duration=120.0,
        )
        transcript = [
            TranscriptSegment(start=5.0, end=7.0, text="too early", language="en"),
            TranscriptSegment(start=42.0, end=45.0, text="setup", language="id"),
            TranscriptSegment(start=55.0, end=58.0, text="payoff", language="id"),
        ]

        candidates = CandidateBuilder(pre_seconds=10, post_seconds=15).from_peaks([peak], transcript)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].candidate_id, "cand001")
        self.assertEqual(candidates[0].source_start, 40.0)
        self.assertEqual(candidates[0].source_end, 65.0)
        self.assertEqual([segment.text for segment in candidates[0].transcript], ["setup", "payoff"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_content_pack_candidates
```

Expected: FAIL with `ModuleNotFoundError: No module named 'content_pack.candidates'`.

- [ ] **Step 3: Implement candidate builder**

Create `content_pack/candidates.py`:

```python
from __future__ import annotations

from content_pack.models import CandidateMoment, TranscriptSegment
from heatmap_pipeline import PeakResult


class CandidateBuilder:
    def __init__(self, pre_seconds: float = 10.0, post_seconds: float = 15.0) -> None:
        self.pre_seconds = pre_seconds
        self.post_seconds = post_seconds

    def from_peaks(self, peaks: list[PeakResult], transcript: list[TranscriptSegment]) -> list[CandidateMoment]:
        candidates: list[CandidateMoment] = []
        for index, peak in enumerate(peaks, start=1):
            source_start = max(0.0, peak.timestamp - self.pre_seconds)
            source_end = peak.timestamp + self.post_seconds
            if peak.duration is not None:
                source_end = min(peak.duration, source_end)
            nearby_segments = [
                segment
                for segment in transcript
                if segment.end >= source_start and segment.start <= source_end
            ]
            candidates.append(
                CandidateMoment(
                    candidate_id=f"cand{index:03d}",
                    source_start=source_start,
                    source_end=source_end,
                    peak_timestamp=peak.timestamp,
                    heatmap_value=peak.value,
                    transcript=nearby_segments,
                    scores={"heatmap_score": peak.value},
                )
            )
        return candidates
```

- [ ] **Step 4: Run candidate tests**

Run:

```bash
python3 -m unittest tests.test_content_pack_candidates
```

Expected: PASS with `Ran 1 test`.

- [ ] **Step 5: Commit**

Run only if this directory is a git worktree:

```bash
git add content_pack/candidates.py tests/test_content_pack_candidates.py
git commit -m "feat: build content pack candidates from heatmap peaks"
```

---

### Task 5: Hybrid Scoring And Selection

**Files:**
- Create: `content_pack/scoring.py`
- Test: `tests/test_content_pack_scoring.py`

- [ ] **Step 1: Write failing scoring tests**

Create `tests/test_content_pack_scoring.py`:

```python
import unittest

from content_pack.models import CandidateMoment, TranscriptSegment
from content_pack.scoring import HybridScorer


class ContentPackScoringTests(unittest.TestCase):
    def candidate(self, candidate_id, start, heatmap, text):
        return CandidateMoment(
            candidate_id=candidate_id,
            source_start=start,
            source_end=start + 30,
            peak_timestamp=start + 15,
            heatmap_value=heatmap,
            transcript=[TranscriptSegment(start=start, end=start + 2, text=text, language="id")],
            scores={"heatmap_score": heatmap},
        )

    def test_scores_theme_matches_higher_than_unrelated(self):
        scorer = HybridScorer(theme="kelucuan bagus")
        related = self.candidate("cand001", 0, 0.5, "Bagus bikin semua orang tertawa lucu sekali")
        unrelated = self.candidate("cand002", 100, 1.0, "Dia sedang memasak nasi")

        scored = scorer.score_candidates([related, unrelated])

        self.assertGreater(scored[0].scores["theme_score"], scored[1].scores["theme_score"])

    def test_select_top_applies_diversity_distance(self):
        scorer = HybridScorer(theme="lucu", min_distance_seconds=60)
        candidates = [
            self.candidate("cand001", 0, 1.0, "lucu"),
            self.candidate("cand002", 20, 0.9, "lucu"),
            self.candidate("cand003", 120, 0.8, "lucu"),
        ]

        selected = scorer.select_top(candidates, top_n=2)

        self.assertEqual([candidate.candidate_id for candidate in selected], ["cand001", "cand003"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_content_pack_scoring
```

Expected: FAIL with `ModuleNotFoundError: No module named 'content_pack.scoring'`.

- [ ] **Step 3: Implement hybrid scorer**

Create `content_pack/scoring.py`:

```python
from __future__ import annotations

from dataclasses import replace

from content_pack.models import CandidateMoment


class HybridScorer:
    def __init__(self, theme: str | None = None, min_distance_seconds: float = 60.0) -> None:
        self.theme = theme or ""
        self.min_distance_seconds = min_distance_seconds

    def score_candidates(self, candidates: list[CandidateMoment]) -> list[CandidateMoment]:
        scored = [self.score_candidate(candidate) for candidate in candidates]
        return sorted(scored, key=lambda candidate: candidate.scores["final_score"], reverse=True)

    def score_candidate(self, candidate: CandidateMoment) -> CandidateMoment:
        transcript_text = " ".join(segment.text for segment in candidate.transcript).lower()
        theme_terms = [term for term in self.theme.lower().split() if term]
        theme_hits = sum(1 for term in theme_terms if term in transcript_text)
        theme_score = theme_hits / len(theme_terms) if theme_terms else 0.5
        heatmap_score = float(candidate.heatmap_value or candidate.scores.get("heatmap_score", 0.0))
        story_score = min(1.0, len(candidate.transcript) / 3)
        duration = candidate.source_end - candidate.source_start
        edit_score = 1.0 if 20 <= duration <= 90 else 0.5
        final_score = (heatmap_score * 0.35) + (theme_score * 0.35) + (story_score * 0.2) + (edit_score * 0.1)
        scores = dict(candidate.scores)
        scores.update(
            {
                "heatmap_score": heatmap_score,
                "theme_score": theme_score,
                "story_score": story_score,
                "edit_score": edit_score,
                "diversity_penalty": 0.0,
                "final_score": final_score,
            }
        )
        return replace(candidate, scores=scores)

    def select_top(self, candidates: list[CandidateMoment], top_n: int) -> list[CandidateMoment]:
        selected: list[CandidateMoment] = []
        for candidate in self.score_candidates(candidates):
            if self.is_too_close(candidate, selected):
                continue
            selected.append(candidate)
            if len(selected) == top_n:
                break
        return selected

    def is_too_close(self, candidate: CandidateMoment, selected: list[CandidateMoment]) -> bool:
        candidate_center = (candidate.source_start + candidate.source_end) / 2
        for selected_candidate in selected:
            selected_center = (selected_candidate.source_start + selected_candidate.source_end) / 2
            if abs(candidate_center - selected_center) < self.min_distance_seconds:
                return True
        return False
```

- [ ] **Step 4: Run scoring tests**

Run:

```bash
python3 -m unittest tests.test_content_pack_scoring
```

Expected: PASS with `Ran 2 tests`.

- [ ] **Step 5: Commit**

Run only if this directory is a git worktree:

```bash
git add content_pack/scoring.py tests/test_content_pack_scoring.py
git commit -m "feat: add hybrid content scoring"
```

---

### Task 6: LLM Planner Fallback

**Files:**
- Create: `content_pack/llm.py`
- Test: `tests/test_content_pack_llm.py`

- [ ] **Step 1: Write failing LLM fallback tests**

Create `tests/test_content_pack_llm.py`:

```python
import unittest

from content_pack.llm import OfflineContentPlanner
from content_pack.models import CandidateMoment, TranscriptSegment


class ContentPackLlmTests(unittest.TestCase):
    def test_offline_planner_generates_bilingual_clip_copy(self):
        candidate = CandidateMoment(
            candidate_id="cand001",
            source_start=0,
            source_end=30,
            peak_timestamp=10,
            heatmap_value=0.8,
            transcript=[TranscriptSegment(start=1, end=2, text="Bagus jatuh lucu", language="id")],
            scores={"final_score": 0.9},
        )

        clips = OfflineContentPlanner().plan_clips([candidate], format_name="top_n", languages=["id", "en"])

        self.assertEqual(len(clips), 1)
        self.assertEqual(clips[0].clip_id, "clip01")
        self.assertEqual(clips[0].format_name, "top_n")
        self.assertIn("Bagus", clips[0].narration_id)
        self.assertIn("Bagus", clips[0].narration_en)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_content_pack_llm
```

Expected: FAIL with `ModuleNotFoundError: No module named 'content_pack.llm'`.

- [ ] **Step 3: Implement LLM planner interface and offline fallback**

Create `content_pack/llm.py`:

```python
from __future__ import annotations

from typing import Protocol

from content_pack.models import CandidateMoment, SelectedClip


class ContentPlanner(Protocol):
    def plan_clips(self, candidates: list[CandidateMoment], format_name: str, languages: list[str]) -> list[SelectedClip]:
        ...


class OfflineContentPlanner:
    def plan_clips(self, candidates: list[CandidateMoment], format_name: str, languages: list[str]) -> list[SelectedClip]:
        clips: list[SelectedClip] = []
        for index, candidate in enumerate(candidates, start=1):
            transcript_text = " ".join(segment.text for segment in candidate.transcript).strip()
            if not transcript_text:
                transcript_text = "Momen menarik tanpa dialog jelas."
            clips.append(
                SelectedClip(
                    clip_id=f"clip{index:02d}",
                    format_name=format_name,
                    rank=index,
                    source_start=candidate.source_start,
                    source_end=candidate.source_end,
                    candidate_id=candidate.candidate_id,
                    title_id=f"Momen #{index}",
                    title_en=f"Moment #{index}",
                    narration_id=f"Momen ini menonjol: {transcript_text}",
                    narration_en=f"This moment stands out: {transcript_text}",
                    scores=candidate.scores,
                )
            )
        return clips
```

- [ ] **Step 4: Run LLM tests**

Run:

```bash
python3 -m unittest tests.test_content_pack_llm
```

Expected: PASS with `Ran 1 test`.

- [ ] **Step 5: Commit**

Run only if this directory is a git worktree:

```bash
git add content_pack/llm.py tests/test_content_pack_llm.py
git commit -m "feat: add offline content planner"
```

---

### Task 7: Exporter

**Files:**
- Create: `content_pack/exporter.py`
- Test: `tests/test_content_pack_exporter.py`

- [ ] **Step 1: Write failing exporter tests**

Create `tests/test_content_pack_exporter.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from content_pack.exporter import ContentPackExporter
from content_pack.models import CandidateMoment, ContentPack, SelectedClip, TranscriptSegment


class ContentPackExporterTests(unittest.TestCase):
    def test_exporter_writes_pack_json_scripts_timeline_and_transcript(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "abc123"
            transcript = [TranscriptSegment(start=0, end=1, text="Halo", language="id")]
            candidate = CandidateMoment("cand001", 0, 30, 10, 0.8, transcript, {"final_score": 0.9})
            clip = SelectedClip(
                clip_id="clip01",
                format_name="top_n",
                rank=1,
                source_start=0,
                source_end=30,
                candidate_id="cand001",
                title_id="Momen #1",
                title_en="Moment #1",
                narration_id="Narasi ID",
                narration_en="Narration EN",
                scores={"final_score": 0.9},
            )
            pack = ContentPack(
                video_id="abc123",
                source_url="https://www.youtube.com/watch?v=abc123",
                title="Demo",
                theme="lucu",
                formats=["top_n"],
                languages=["id", "en"],
                clips=[clip],
                candidates=[candidate],
                output_dir=output_dir,
            )

            ContentPackExporter().export(pack, transcript)

            self.assertTrue((output_dir / "content_pack.json").exists())
            self.assertTrue((output_dir / "timeline.json").exists())
            self.assertTrue((output_dir / "script_id.md").exists())
            self.assertTrue((output_dir / "script_en.md").exists())
            self.assertTrue((output_dir / "editor_notes.md").exists())
            self.assertTrue((output_dir / "transcripts" / "full.srt").exists())
            payload = json.loads((output_dir / "content_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["clips"][0]["clip_id"], "clip01")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_content_pack_exporter
```

Expected: FAIL with `ModuleNotFoundError: No module named 'content_pack.exporter'`.

- [ ] **Step 3: Implement exporter**

Create `content_pack/exporter.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from content_pack.models import ContentPack, TranscriptSegment
from content_pack.srt import segments_to_srt


class ContentPackExporter:
    def export(self, pack: ContentPack, transcript: list[TranscriptSegment]) -> None:
        pack.output_dir.mkdir(parents=True, exist_ok=True)
        (pack.output_dir / "clips").mkdir(exist_ok=True)
        transcripts_dir = pack.output_dir / "transcripts"
        transcripts_dir.mkdir(exist_ok=True)
        metadata_dir = pack.output_dir / "metadata"
        metadata_dir.mkdir(exist_ok=True)

        self.write_json(pack.output_dir / "content_pack.json", pack.to_dict())
        self.write_json(pack.output_dir / "timeline.json", self.timeline_payload(pack))
        self.write_json(metadata_dir / "candidates.json", [candidate.to_dict() for candidate in pack.candidates])
        self.write_json(transcripts_dir / "full.json", [segment.to_dict() for segment in transcript])
        (transcripts_dir / "full.srt").write_text(segments_to_srt(transcript), encoding="utf-8")
        (pack.output_dir / "script_id.md").write_text(self.script_markdown(pack, "id"), encoding="utf-8")
        (pack.output_dir / "script_en.md").write_text(self.script_markdown(pack, "en"), encoding="utf-8")
        (pack.output_dir / "editor_notes.md").write_text(self.editor_notes(pack), encoding="utf-8")

    def write_json(self, path: Path, payload: object) -> None:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def timeline_payload(self, pack: ContentPack) -> dict[str, object]:
        return {
            "video_id": pack.video_id,
            "theme": pack.theme,
            "clips": [
                {
                    "clip_id": clip.clip_id,
                    "rank": clip.rank,
                    "source_start": clip.source_start,
                    "source_end": clip.source_end,
                    "local_path": str(clip.local_path) if clip.local_path else None,
                    "narration_id": clip.narration_id,
                    "narration_en": clip.narration_en,
                }
                for clip in pack.clips
            ],
        }

    def script_markdown(self, pack: ContentPack, language: str) -> str:
        lines = [f"# {pack.title or pack.video_id}", "", f"Theme: {pack.theme or 'auto'}", ""]
        for clip in pack.clips:
            title = clip.title_id if language == "id" else clip.title_en
            narration = clip.narration_id if language == "id" else clip.narration_en
            lines.extend([f"## {clip.clip_id}: {title}", "", narration, ""])
        return "\n".join(lines)

    def editor_notes(self, pack: ContentPack) -> str:
        lines = [f"# Editor Notes: {pack.title or pack.video_id}", ""]
        for clip in pack.clips:
            lines.append(f"- {clip.clip_id}: {clip.source_start:.3f}-{clip.source_end:.3f}, score={clip.scores.get('final_score', 0):.3f}")
        return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run exporter tests**

Run:

```bash
python3 -m unittest tests.test_content_pack_exporter
```

Expected: PASS with `Ran 1 test`.

- [ ] **Step 5: Commit**

Run only if this directory is a git worktree:

```bash
git add content_pack/exporter.py tests/test_content_pack_exporter.py
git commit -m "feat: export content pack artifacts"
```

---

### Task 8: Orchestrator

**Files:**
- Create: `content_pack/orchestrator.py`
- Test: `tests/test_content_pack_orchestrator.py`

- [ ] **Step 1: Write failing orchestrator test**

Create `tests/test_content_pack_orchestrator.py`:

```python
import tempfile
import unittest
from pathlib import Path

from content_pack.llm import OfflineContentPlanner
from content_pack.models import TranscriptSegment
from content_pack.orchestrator import ContentPackOrchestrator
from content_pack.transcriber import Transcriber
from heatmap_pipeline import PeakResult


class StaticTranscriber:
    def transcribe(self, audio_path: Path) -> list[TranscriptSegment]:
        return [TranscriptSegment(start=40, end=44, text="Bagus lucu sekali", language="id")]


class StaticHeatmapExtractor:
    def find_peaks(self, url: str):
        return [
            PeakResult(
                url=url,
                video_id="abc123",
                title="Demo Video",
                timestamp=50,
                value=0.9,
                mean=0.2,
                stddev=0.1,
                threshold=0.35,
                duration=120,
            )
        ]


class ContentPackOrchestratorTests(unittest.TestCase):
    def test_orchestrator_generates_pack_and_exports_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = ContentPackOrchestrator(
                transcriber=StaticTranscriber(),
                heatmap_extractor=StaticHeatmapExtractor(),
                planner=OfflineContentPlanner(),
                output_root=Path(tmpdir),
            )

            pack = orchestrator.generate(
                url="https://www.youtube.com/watch?v=abc123",
                audio_path=Path("unused.m4a"),
                theme="lucu",
                formats=["top_n"],
                languages=["id", "en"],
                top_n=1,
            )

            self.assertEqual(pack.video_id, "abc123")
            self.assertEqual(len(pack.clips), 1)
            self.assertTrue((Path(tmpdir) / "abc123" / "content_pack.json").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_content_pack_orchestrator
```

Expected: FAIL with `ModuleNotFoundError: No module named 'content_pack.orchestrator'`.

- [ ] **Step 3: Implement orchestrator**

Create `content_pack/orchestrator.py`:

```python
from __future__ import annotations

from pathlib import Path

from content_pack.candidates import CandidateBuilder
from content_pack.exporter import ContentPackExporter
from content_pack.llm import ContentPlanner, OfflineContentPlanner
from content_pack.models import ContentPack
from content_pack.scoring import HybridScorer
from content_pack.transcriber import Transcriber
from heatmap_pipeline import HeatmapExtractor, PipelineConfig


class ContentPackOrchestrator:
    def __init__(
        self,
        transcriber: Transcriber,
        heatmap_extractor: object | None = None,
        planner: ContentPlanner | None = None,
        output_root: Path = Path("content_packs"),
        exporter: ContentPackExporter | None = None,
    ) -> None:
        self.transcriber = transcriber
        self.heatmap_extractor = heatmap_extractor or HeatmapExtractor(PipelineConfig())
        self.planner = planner or OfflineContentPlanner()
        self.output_root = output_root
        self.exporter = exporter or ContentPackExporter()

    def generate(
        self,
        url: str,
        audio_path: Path,
        theme: str | None,
        formats: list[str],
        languages: list[str],
        top_n: int,
    ) -> ContentPack:
        transcript = self.transcriber.transcribe(audio_path)
        peaks = self.heatmap_extractor.find_peaks(url)
        candidates = CandidateBuilder().from_peaks(peaks, transcript)
        selected_candidates = HybridScorer(theme=theme).select_top(candidates, top_n=top_n)

        clips = []
        for format_name in formats:
            clips.extend(self.planner.plan_clips(selected_candidates, format_name=format_name, languages=languages))

        video_id = peaks[0].video_id if peaks and peaks[0].video_id else "unknown_video"
        title = peaks[0].title if peaks else None
        output_dir = self.output_root / video_id
        pack = ContentPack(
            video_id=video_id,
            source_url=url,
            title=title,
            theme=theme,
            formats=formats,
            languages=languages,
            clips=clips,
            candidates=candidates,
            output_dir=output_dir,
        )
        self.exporter.export(pack, transcript)
        return pack
```

- [ ] **Step 4: Run orchestrator tests**

Run:

```bash
python3 -m unittest tests.test_content_pack_orchestrator
```

Expected: PASS with `Ran 1 test`.

- [ ] **Step 5: Commit**

Run only if this directory is a git worktree:

```bash
git add content_pack/orchestrator.py tests/test_content_pack_orchestrator.py
git commit -m "feat: orchestrate content pack generation"
```

---

### Task 9: CLI Subcommand Skeleton

**Files:**
- Modify: `heatmap_pipeline.py`
- Test: `tests/test_heatmap_pipeline.py`

- [ ] **Step 1: Write failing CLI parser test**

Append to `tests/test_heatmap_pipeline.py` inside `HeatmapPipelineTests`:

```python
    def test_content_pack_subcommand_parses_arguments(self):
        parser = build_parser()

        args = parser.parse_args([
            "content-pack",
            "--url",
            "https://www.youtube.com/watch?v=abc123",
            "--audio-file",
            "audio.m4a",
            "--theme",
            "lucu",
            "--formats",
            "top_n,shorts_pack",
            "--languages",
            "id,en",
            "--top-n",
            "3",
        ])

        self.assertEqual(args.command, "content-pack")
        self.assertEqual(args.audio_file, "audio.m4a")
        self.assertEqual(args.formats, "top_n,shorts_pack")
        self.assertEqual(args.languages, "id,en")
        self.assertEqual(args.top_n, 3)
```

Also update the import line in `tests/test_heatmap_pipeline.py`:

```python
from heatmap_pipeline import HeatmapExtractor, HeatmapPoint, PeakResult, PipelineConfig, VideoClipper, build_parser, is_youtube_url
```

- [ ] **Step 2: Run parser test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_heatmap_pipeline.HeatmapPipelineTests.test_content_pack_subcommand_parses_arguments
```

Expected: FAIL because the parser does not support `content-pack`.

- [ ] **Step 3: Refactor parser to support subcommands while preserving old behavior**

Modify `build_parser()` in `heatmap_pipeline.py` to use subparsers and keep old clipping command compatible enough for direct options:

```python
def add_clip_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--url", action="append", help="YouTube URL. Bisa dipakai berulang.")
    parser.add_argument("--input-file", help="File teks berisi URL per baris.")
    parser.add_argument("--output-dir", default="clips")
    parser.add_argument("--k", type=float, default=1.5)
    parser.add_argument("--pre", type=float, default=10.0)
    parser.add_argument("--post", type=float, default=15.0)
    parser.add_argument("--base-delay", type=float, default=3.0)
    parser.add_argument("--jitter", type=float, default=4.0)
    parser.add_argument("--json", action="store_true", help="Cetak hasil JSON untuk dashboard/automation.")


def add_content_pack_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--url", required=True, help="YouTube URL sumber.")
    parser.add_argument("--audio-file", required=True, help="Path audio full video untuk transkripsi.")
    parser.add_argument("--theme", help="Tema konten. Jika kosong, mode discovery dapat ditambahkan nanti.")
    parser.add_argument("--formats", default="best_moments,shorts_pack")
    parser.add_argument("--languages", default="id,en")
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--output-dir", default="content_packs")
    parser.add_argument("--transcript-json", help="Fixture transcript JSON untuk dry run/test murah.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="YouTube heatmap automated clipping CLI")
    subparsers = parser.add_subparsers(dest="command")

    clip_parser = subparsers.add_parser("clip", help="Download heatmap-based clips.")
    add_clip_arguments(clip_parser)

    content_pack_parser = subparsers.add_parser("content-pack", help="Generate editor-ready content pack.")
    add_content_pack_arguments(content_pack_parser)

    add_clip_arguments(parser)
    return parser
```

- [ ] **Step 4: Update imports and main dispatch**

In `main()`, after parsing args, add:

```python
    if args.command == "content-pack":
        return run_content_pack_command(args)
```

Before existing `main()`, add:

```python
def comma_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def run_content_pack_command(args: argparse.Namespace) -> int:
    from content_pack.llm import OfflineContentPlanner
    from content_pack.orchestrator import ContentPackOrchestrator
    from content_pack.transcriber import FasterWhisperTranscriber, JsonTranscriptLoader

    transcriber = JsonTranscriptLoader(Path(args.transcript_json)) if args.transcript_json else FasterWhisperTranscriber()
    orchestrator = ContentPackOrchestrator(
        transcriber=transcriber,
        output_root=Path(args.output_dir),
        planner=OfflineContentPlanner(),
    )
    pack = orchestrator.generate(
        url=args.url,
        audio_path=Path(args.audio_file),
        theme=args.theme,
        formats=comma_list(args.formats),
        languages=comma_list(args.languages),
        top_n=args.top_n,
    )
    print(json.dumps(pack.to_dict(), indent=2, ensure_ascii=False))
    return 0
```

Also make old default clipping work by setting command when omitted:

```python
    if not hasattr(args, "command") or args.command is None:
        args.command = "clip"
```

- [ ] **Step 5: Run CLI parser test**

Run:

```bash
python3 -m unittest tests.test_heatmap_pipeline.HeatmapPipelineTests.test_content_pack_subcommand_parses_arguments
```

Expected: PASS.

- [ ] **Step 6: Run all current tests**

Run:

```bash
python3 -m unittest tests.test_heatmap_pipeline
```

Expected: PASS for existing heatmap tests.

- [ ] **Step 7: Commit**

Run only if this directory is a git worktree:

```bash
git add heatmap_pipeline.py tests/test_heatmap_pipeline.py
git commit -m "feat: add content pack cli subcommand"
```

---

### Task 10: Audio Extraction Command Support

**Files:**
- Create: `content_pack/audio.py`
- Modify: `content_pack/orchestrator.py`
- Modify: `heatmap_pipeline.py`
- Test: `tests/test_content_pack_audio.py`

- [ ] **Step 1: Write failing audio option tests**

Create `tests/test_content_pack_audio.py`:

```python
import unittest
from pathlib import Path

from content_pack.audio import default_audio_path


class ContentPackAudioTests(unittest.TestCase):
    def test_default_audio_path_uses_video_id(self):
        self.assertEqual(default_audio_path(Path("content_packs"), "abc123"), Path("content_packs") / "abc123" / "audio" / "source.m4a")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_content_pack_audio
```

Expected: FAIL with `ModuleNotFoundError: No module named 'content_pack.audio'`.

- [ ] **Step 3: Implement audio helper**

Create `content_pack/audio.py`:

```python
from __future__ import annotations

from pathlib import Path


def default_audio_path(output_root: Path, video_id: str) -> Path:
    return output_root / video_id / "audio" / "source.m4a"
```

- [ ] **Step 4: Run audio tests**

Run:

```bash
python3 -m unittest tests.test_content_pack_audio
```

Expected: PASS with `Ran 1 test`.

- [ ] **Step 5: Defer actual audio download for MVP CLI dry-run path**

Keep `--audio-file` required for MVP. Do not add network audio extraction yet. This avoids duplicating `yt-dlp` logic before the pack pipeline is proven.

- [ ] **Step 6: Commit**

Run only if this directory is a git worktree:

```bash
git add content_pack/audio.py tests/test_content_pack_audio.py
git commit -m "feat: add content pack audio path helper"
```

---

### Task 11: README Update

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add content pack CLI docs**

Append this section to `README.md`:

```markdown
## Content Pack Generator MVP

The `content-pack` subcommand generates editor-ready assets for one long YouTube video. It is CLI-first and designed so a future Web UI or AI video-maker agent can consume the same JSON output.

Example dry run with a transcript fixture:

```bash
python3 heatmap_pipeline.py content-pack \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --audio-file "audio/source.m4a" \
  --transcript-json "transcript_fixture.json" \
  --theme "kelucuan si Bagus" \
  --formats top_n,shorts_pack \
  --languages id,en \
  --top-n 5
```

Default output:

```text
content_packs/<video_id>/
  content_pack.json
  timeline.json
  editor_notes.md
  script_id.md
  script_en.md
  transcripts/full.srt
  transcripts/full.json
  metadata/candidates.json
```

MVP notes:

- Full audio transcription uses `faster-whisper` when `--transcript-json` is not provided.
- Reasoning uses an offline planner first; cloud LLM integration can be added behind the planner interface.
- Final video rendering is intentionally out of scope. The output is meant for manual editors or AI video-maker agents.
```

- [ ] **Step 2: Check README renders as plain Markdown**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
text = Path('README.md').read_text(encoding='utf-8')
assert '## Content Pack Generator MVP' in text
assert text.count('```') % 2 == 0
print('README content-pack docs OK')
PY
```

Expected: prints `README content-pack docs OK`.

- [ ] **Step 3: Commit**

Run only if this directory is a git worktree:

```bash
git add README.md
git commit -m "docs: document content pack generator"
```

---

### Task 12: End-To-End Dry Run Test

**Files:**
- Create: `tests/test_content_pack_e2e.py`

- [ ] **Step 1: Write E2E dry-run test**

Create `tests/test_content_pack_e2e.py`:

```python
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ContentPackE2ETests(unittest.TestCase):
    def test_cli_content_pack_with_transcript_fixture_exports_pack(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            transcript_path = root / "transcript.json"
            transcript_path.write_text(
                json.dumps([
                    {"start": 700, "end": 704, "text": "Bagus melakukan hal lucu", "language": "id"},
                    {"start": 718, "end": 722, "text": "semua orang tertawa", "language": "id"},
                ]),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "heatmap_pipeline.py",
                    "content-pack",
                    "--url",
                    "https://www.youtube.com/watch?v=YFy2KbsM4ys",
                    "--audio-file",
                    "unused.m4a",
                    "--transcript-json",
                    str(transcript_path),
                    "--theme",
                    "lucu bagus",
                    "--formats",
                    "top_n",
                    "--languages",
                    "id,en",
                    "--top-n",
                    "1",
                    "--output-dir",
                    str(root / "packs"),
                ],
                cwd=Path.cwd(),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["video_id"], "YFy2KbsM4ys")
            self.assertEqual(len(payload["clips"]), 1)
            self.assertTrue((root / "packs" / "YFy2KbsM4ys" / "content_pack.json").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run E2E test**

Run:

```bash
python3 -m unittest tests.test_content_pack_e2e
```

Expected: PASS. This test will hit YouTube metadata. If network or YouTube challenge blocks it, mark the result as environment-blocked and validate via orchestrator unit test instead.

- [ ] **Step 3: Run all tests**

Run:

```bash
python3 -m unittest discover tests
```

Expected: PASS for unit tests. E2E may be environment-dependent.

- [ ] **Step 4: Commit**

Run only if this directory is a git worktree and E2E is stable in this environment:

```bash
git add tests/test_content_pack_e2e.py
git commit -m "test: add content pack cli dry run"
```

---

## Self-Review

Spec coverage:

- CLI-first: Task 9.
- Web UI-ready core separation: Tasks 1-8.
- Local transcription: Task 3.
- Hybrid heatmap + transcript candidates: Tasks 4-5.
- Pluggable formats: Tasks 6, 8, 9.
- Bilingual scripts: Tasks 6-8.
- Editor-ready files: Task 7.
- Output folder schema: Task 7.
- README docs: Task 11.
- End-to-end dry run: Task 12.

Known MVP limitation:

- Actual full audio download is not implemented in this plan. The first CLI requires `--audio-file` or `--transcript-json`. This is intentional to keep MVP testable and avoid adding network-heavy behavior before the content pack core is stable.

Placeholder scan:

- No placeholder instructions are used.
- Steps include exact files, code, commands, and expected results.

Type consistency:

- `TranscriptSegment`, `CandidateMoment`, `SelectedClip`, and `ContentPack` are defined before use.
- `ContentPlanner.plan_clips()` signature is consistent across planner and orchestrator.
- `ContentPackExporter.export(pack, transcript)` signature is consistent across exporter and orchestrator.
