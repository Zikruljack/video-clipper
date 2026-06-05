from __future__ import annotations

import json
from pathlib import Path

from src.heatmap_pipeline import PeakResult


class JsonPeakLoader:
    def __init__(self, peaks_path: Path) -> None:
        self.peaks_path = peaks_path

    def find_peaks(self, url: str) -> list[PeakResult]:
        payload = json.loads(self.peaks_path.read_text(encoding="utf-8"))
        return [
            PeakResult(
                url=url,
                video_id=item.get("video_id"),
                title=item.get("title"),
                timestamp=float(item["timestamp"]),
                value=float(item["value"]),
                mean=float(item.get("mean", 0.0)),
                stddev=float(item.get("stddev", 0.0)),
                threshold=float(item.get("threshold", 0.0)),
                duration=float(item["duration"]) if item.get("duration") is not None else None,
            )
            for item in payload
        ]
