import json
import tempfile
import unittest
from pathlib import Path

from src.content_pack.heatmap import JsonPeakLoader


class ContentPackHeatmapTests(unittest.TestCase):
    def test_json_peak_loader_reads_peak_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "peaks.json"
            path.write_text(json.dumps([{"video_id": "abc123", "title": "Demo", "timestamp": 10, "value": 0.8, "duration": 100}]), encoding="utf-8")
            peaks = JsonPeakLoader(path).find_peaks("https://www.youtube.com/watch?v=abc123")
        self.assertEqual(peaks[0].video_id, "abc123")
        self.assertEqual(peaks[0].timestamp, 10.0)


if __name__ == "__main__":
    unittest.main()
