import unittest

from content_pack.models import TranscriptSegment
from content_pack.srt import format_srt_timestamp, segments_to_srt


class ContentPackSrtTests(unittest.TestCase):
    def test_format_srt_timestamp_uses_hours_minutes_seconds_millis(self):
        self.assertEqual(format_srt_timestamp(3661.234), "01:01:01,234")

    def test_segments_to_srt_exports_numbered_blocks(self):
        srt = segments_to_srt([
            TranscriptSegment(start=0.0, end=1.5, text="Halo", language="id"),
            TranscriptSegment(start=2.0, end=3.25, text="World", language="en"),
        ])

        self.assertEqual(
            srt,
            "1\n00:00:00,000 --> 00:00:01,500\nHalo\n\n2\n00:00:02,000 --> 00:00:03,250\nWorld\n",
        )


if __name__ == "__main__":
    unittest.main()
