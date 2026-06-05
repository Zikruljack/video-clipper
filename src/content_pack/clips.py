from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Protocol

from src.content_pack.models import SelectedClip


class RangeClipper(Protocol):
    def download_range_clip(self, url: str, start: float, end: float, output_path: Path) -> None:
        ...


class ClipAssetExporter:
    def __init__(self, clipper: RangeClipper) -> None:
        self.clipper = clipper

    def export(self, url: str, clips: list[SelectedClip], output_dir: Path) -> list[SelectedClip]:
        clips_dir = output_dir / "clips"
        clips_dir.mkdir(parents=True, exist_ok=True)
        updated: list[SelectedClip] = []
        for clip in clips:
            output_path = clips_dir / f"{clip.clip_id}.mp4"
            self.clipper.download_range_clip(url, clip.source_start, clip.source_end, output_path)
            updated.append(replace(clip, local_path=output_path))
        return updated
