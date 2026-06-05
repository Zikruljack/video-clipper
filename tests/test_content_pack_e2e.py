import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ContentPackE2ETests(unittest.TestCase):
    def test_cli_content_pack_with_transcript_fixture_exports_pack(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            transcript_path = root / "transcript.json"
            transcript_path.write_text(
                json.dumps([
                    {"start": 700, "end": 704, "text": "Bagus melakukan hal lucu", "language": "id"},
                    {"start": 718, "end": 722, "text": "semua orang tertawa", "language": "id"},
                ]),
                encoding="utf-8",
            )
            peaks_path = root / "peaks.json"
            peaks_path.write_text(
                json.dumps([
                    {"video_id": "YFy2KbsM4ys", "title": "Demo", "timestamp": 718, "value": 1.0, "duration": 1295}
                ]),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "heatmap_pipeline.py",
                    "content-pack",
                    "--url",
                    "https://www.youtube.com/watch?v=YFy2KbsM4ys",
                    "--audio-file",
                    "unused.m4a",
                    "--transcript-json",
                    str(transcript_path),
                    "--peaks-json",
                    str(peaks_path),
                    "--theme",
                    "lucu bagus",
                    "--formats",
                    "top_n",
                    "--languages",
                    "id,en",
                    "--top-n",
                    "1",
                    "--output-dir",
                    str(root / "packs"),
                ],
                cwd=Path.cwd(),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["video_id"], "YFy2KbsM4ys")
            self.assertEqual(len(payload["clips"]), 1)
            self.assertTrue((root / "packs" / "YFy2KbsM4ys" / "content_pack.json").exists())


if __name__ == "__main__":
    unittest.main()
