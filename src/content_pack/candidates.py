from __future__ import annotations

from src.content_pack.models import CandidateMoment, TranscriptSegment
from src.heatmap_pipeline import PeakResult


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
            nearby_segments = [segment for segment in transcript if segment.end >= source_start and segment.start <= source_end]
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
