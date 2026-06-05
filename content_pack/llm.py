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
