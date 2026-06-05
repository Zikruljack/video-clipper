from __future__ import annotations

from pathlib import Path


def default_audio_path(output_root: Path, video_id: str) -> Path:
    return output_root / video_id / "audio" / "source.m4a"
