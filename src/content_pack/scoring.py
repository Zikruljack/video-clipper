from __future__ import annotations

from dataclasses import replace

from src.content_pack.models import CandidateMoment


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
        scores.update({"heatmap_score": heatmap_score, "theme_score": theme_score, "story_score": story_score, "edit_score": edit_score, "diversity_penalty": 0.0, "final_score": final_score})
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
