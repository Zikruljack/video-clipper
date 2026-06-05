import unittest
from pathlib import Path

from content_pack.clips import ClipAssetExporter
from content_pack.models import SelectedClip


class FakeClipper:
    def __init__(self):
        self.calls = []

    def download_range_clip(self, url, start, end, output_path):
        self.calls.append((url, start, end, output_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("fake", encoding="utf-8")


class ContentPackClipsTests(unittest.TestCase):
    def test_exporter_downloads_each_selected_clip_and_sets_local_path(self):
        clip = SelectedClip("clip01", "top_n", 1, 10, 40, "cand001", "ID", "EN", "narasi", "narration", {"final_score": 1})
        fake = FakeClipper()

        updated = ClipAssetExporter(fake).export("https://www.youtube.com/watch?v=abc123", [clip], Path("/tmp/content_pack_clip_test"))

        self.assertEqual(updated[0].local_path, Path("/tmp/content_pack_clip_test") / "clips" / "clip01.mp4")
        self.assertEqual(fake.calls[0][1:3], (10, 40))


if __name__ == "__main__":
    unittest.main()
