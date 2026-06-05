import unittest
from src.content_pack.llm import OfflineContentPlanner
from src.content_pack.models import CandidateMoment, TranscriptSegment

class ContentPackLlmTests(unittest.TestCase):
    def test_offline_planner_generates_bilingual_clip_copy(self):
        candidate = CandidateMoment("cand001", 0, 30, 10, 0.8, [TranscriptSegment(1, 2, "Bagus jatuh lucu", "id")], {"final_score": 0.9})
        clips = OfflineContentPlanner().plan_clips([candidate], format_name="top_n", languages=["id", "en"])
        self.assertEqual(len(clips), 1)
        self.assertEqual(clips[0].clip_id, "clip01")
        self.assertEqual(clips[0].format_name, "top_n")
        self.assertIn("Bagus", clips[0].narration_id)
        self.assertIn("Bagus", clips[0].narration_en)

if __name__ == "__main__":
    unittest.main()
