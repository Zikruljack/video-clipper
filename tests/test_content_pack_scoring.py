import unittest
from src.content_pack.models import CandidateMoment, TranscriptSegment
from src.content_pack.scoring import HybridScorer

class ContentPackScoringTests(unittest.TestCase):
    def candidate(self, candidate_id, start, heatmap, text):
        return CandidateMoment(candidate_id, start, start + 30, start + 15, heatmap, [TranscriptSegment(start, start + 2, text, "id")], {"heatmap_score": heatmap})

    def test_scores_theme_matches_higher_than_unrelated(self):
        scorer = HybridScorer(theme="kelucuan bagus")
        related = self.candidate("cand001", 0, 0.5, "Bagus bikin semua orang tertawa lucu sekali")
        unrelated = self.candidate("cand002", 100, 1.0, "Dia sedang memasak nasi")
        scored = scorer.score_candidates([related, unrelated])
        self.assertGreater(scored[0].scores["theme_score"], scored[1].scores["theme_score"])

    def test_select_top_applies_diversity_distance(self):
        scorer = HybridScorer(theme="lucu", min_distance_seconds=60)
        candidates = [self.candidate("cand001", 0, 1.0, "lucu"), self.candidate("cand002", 20, 0.9, "lucu"), self.candidate("cand003", 120, 0.8, "lucu")]
        selected = scorer.select_top(candidates, top_n=2)
        self.assertEqual([candidate.candidate_id for candidate in selected], ["cand001", "cand003"])

if __name__ == "__main__":
    unittest.main()
