import unittest
from pathlib import Path
from content_pack.audio import default_audio_path

class ContentPackAudioTests(unittest.TestCase):
    def test_default_audio_path_uses_video_id(self):
        self.assertEqual(default_audio_path(Path("content_packs"), "abc123"), Path("content_packs") / "abc123" / "audio" / "source.m4a")

if __name__ == "__main__":
    unittest.main()
