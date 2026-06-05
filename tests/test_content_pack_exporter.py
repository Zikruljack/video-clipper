import json
import tempfile
import unittest
from pathlib import Path
from content_pack.exporter import ContentPackExporter
from content_pack.models import CandidateMoment, ContentPack, SelectedClip, TranscriptSegment

class ContentPackExporterTests(unittest.TestCase):
    def test_exporter_writes_pack_json_scripts_timeline_and_transcript(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "abc123"
            transcript = [TranscriptSegment(0, 1, "Halo", "id")]
            candidate = CandidateMoment("cand001", 0, 30, 10, 0.8, transcript, {"final_score": 0.9})
            clip = SelectedClip("clip01", "top_n", 1, 0, 30, "cand001", "Momen #1", "Moment #1", "Narasi ID", "Narration EN", {"final_score": 0.9})
            pack = ContentPack("abc123", "https://www.youtube.com/watch?v=abc123", "Demo", "lucu", ["top_n"], ["id", "en"], [clip], [candidate], output_dir)
            ContentPackExporter().export(pack, transcript)
            self.assertTrue((output_dir / "content_pack.json").exists())
            self.assertTrue((output_dir / "timeline.json").exists())
            self.assertTrue((output_dir / "script_id.md").exists())
            self.assertTrue((output_dir / "script_en.md").exists())
            self.assertTrue((output_dir / "editor_notes.md").exists())
            self.assertTrue((output_dir / "transcripts" / "full.srt").exists())
            payload = json.loads((output_dir / "content_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["clips"][0]["clip_id"], "clip01")

if __name__ == "__main__":
    unittest.main()
