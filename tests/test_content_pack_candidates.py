import unittest
from content_pack.candidates import CandidateBuilder
from content_pack.models import TranscriptSegment
from heatmap_pipeline import PeakResult

class ContentPackCandidateTests(unittest.TestCase):
    def test_builder_creates_candidate_with_nearby_transcript(self):
        peak = PeakResult("https://www.youtube.com/watch?v=abc123", "abc123", "demo", 50.0, 0.9, 0.2, 0.1, 0.35, 120.0)
        transcript = [TranscriptSegment(5.0, 7.0, "too early", "en"), TranscriptSegment(42.0, 45.0, "setup", "id"), TranscriptSegment(55.0, 58.0, "payoff", "id")]
        candidates = CandidateBuilder(pre_seconds=10, post_seconds=15).from_peaks([peak], transcript)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].candidate_id, "cand001")
        self.assertEqual(candidates[0].source_start, 40.0)
        self.assertEqual(candidates[0].source_end, 65.0)
        self.assertEqual([segment.text for segment in candidates[0].transcript], ["setup", "payoff"])

if __name__ == "__main__":
    unittest.main()
