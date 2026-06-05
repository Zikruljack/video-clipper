import unittest

from src.content_pack.models import CandidateMoment, TranscriptSegment


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
