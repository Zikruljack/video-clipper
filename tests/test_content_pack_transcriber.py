import json
import tempfile
import unittest
from pathlib import Path

from src.content_pack.transcriber import FasterWhisperTranscriber, JsonTranscriptLoader


class ContentPackTranscriberTests(unittest.TestCase):
    def test_json_transcript_loader_reads_segments(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "transcript.json"
            path.write_text(json.dumps([{"start": 0, "end": 2.5, "text": "Halo", "language": "id"}, {"start": 3, "end": 4, "text": "hello", "language": "en"}]), encoding="utf-8")
            segments = JsonTranscriptLoader(path).transcribe(Path("unused.m4a"))
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].text, "Halo")
        self.assertEqual(segments[1].language, "en")

    def test_faster_whisper_transcriber_stores_runtime_options(self):
        transcriber = FasterWhisperTranscriber(model_size="small", device="cpu", compute_type="int8")
        self.assertEqual(transcriber.model_size, "small")
        self.assertEqual(transcriber.device, "cpu")
        self.assertEqual(transcriber.compute_type, "int8")


if __name__ == "__main__":
    unittest.main()
