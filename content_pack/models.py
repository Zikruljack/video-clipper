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
