import tempfile
import unittest
from pathlib import Path

from src.content_pack.audio import YtDlpAudioDownloader, default_audio_path


class FakeYtdlp:
    class YoutubeDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            FakeYtdlp.last_opts = self.opts
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, url, download=False):
            return {"id": "abc123", "title": "Demo"}

        def download(self, urls):
            FakeYtdlp.last_urls = urls


class ContentPackAudioTests(unittest.TestCase):
    def test_default_audio_path_uses_video_id(self):
        self.assertEqual(default_audio_path(Path("content_packs"), "abc123"), Path("content_packs") / "abc123" / "audio" / "source.m4a")

    def test_audio_downloader_builds_m4a_output_options(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = YtDlpAudioDownloader(ytdlp_module=FakeYtdlp).download(
                "https://www.youtube.com/watch?v=abc123",
                Path(tmpdir),
            )

        self.assertEqual(result.video_id, "abc123")
        self.assertEqual(result.audio_path, Path(tmpdir) / "abc123" / "audio" / "source.m4a")
        self.assertEqual(FakeYtdlp.last_opts["format"], "bestaudio[ext=m4a]/bestaudio")
        self.assertEqual(FakeYtdlp.last_urls, ["https://www.youtube.com/watch?v=abc123"])


if __name__ == "__main__":
    unittest.main()
