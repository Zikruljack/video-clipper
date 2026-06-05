import tempfile
import unittest
from pathlib import Path
from src.content_pack.llm import OfflineContentPlanner
from src.content_pack.models import TranscriptSegment
from src.content_pack.orchestrator import ContentPackOrchestrator
from src.heatmap_pipeline import PeakResult

class StaticTranscriber:
    def transcribe(self, audio_path: Path):
        return [TranscriptSegment(40, 44, "Bagus lucu sekali", "id")]

class StaticHeatmapExtractor:
    def find_peaks(self, url: str):
        return [PeakResult(url, "abc123", "Demo Video", 50, 0.9, 0.2, 0.1, 0.35, 120)]

class ContentPackOrchestratorTests(unittest.TestCase):
    def test_orchestrator_generates_pack_and_exports_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = ContentPackOrchestrator(StaticTranscriber(), StaticHeatmapExtractor(), OfflineContentPlanner(), Path(tmpdir))
            pack = orchestrator.generate("https://www.youtube.com/watch?v=abc123", Path("unused.m4a"), "lucu", ["top_n"], ["id", "en"], 1)
            self.assertEqual(pack.video_id, "abc123")
            self.assertEqual(len(pack.clips), 1)
            self.assertTrue((Path(tmpdir) / "abc123" / "content_pack.json").exists())

if __name__ == "__main__":
    unittest.main()
