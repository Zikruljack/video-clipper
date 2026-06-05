import unittest

from heatmap_pipeline import HeatmapExtractor, HeatmapPoint, PeakResult, PipelineConfig, VideoClipper, build_parser, is_youtube_url


class HeatmapPipelineTests(unittest.TestCase):
    def test_parse_heatmap_point_preserves_zero_values(self):
        extractor = HeatmapExtractor()

        point = extractor.parse_heatmap_point({"start_time": 0, "end_time": 10, "value": 0})

        self.assertEqual(point, HeatmapPoint(start_time=0.0, end_time=10.0, value=0.0))

    def test_build_section_applies_buffer_and_duration_cap(self):
        clipper = VideoClipper(PipelineConfig(pre_margin_seconds=10, post_margin_seconds=15))
        peak = PeakResult(
            url="https://www.youtube.com/watch?v=abc123",
            video_id="abc123",
            title="demo",
            timestamp=5,
            value=2,
            mean=1,
            stddev=0.5,
            threshold=1.75,
            duration=12,
        )

        self.assertEqual(clipper.build_section(peak), "*0.000-12.000")

    def test_youtube_url_validation_accepts_youtube_hosts_only(self):
        self.assertTrue(is_youtube_url("https://www.youtube.com/watch?v=abc123"))
        self.assertTrue(is_youtube_url("https://youtu.be/abc123"))
        self.assertFalse(is_youtube_url("https://example.com/watch?v=abc123"))

    def test_find_peaks_returns_all_threshold_peaks(self):
        extractor = HeatmapExtractor(PipelineConfig(peak_k=0.7))
        extractor.extract_metadata = lambda url: {
            "id": "abc123",
            "title": "demo",
            "duration": 100,
            "heatmap": [
                {"start_time": 0, "end_time": 10, "value": 1},
                {"start_time": 10, "end_time": 20, "value": 5},
                {"start_time": 20, "end_time": 30, "value": 1},
                {"start_time": 30, "end_time": 40, "value": 6},
            ],
        }

        peaks = extractor.find_peaks("https://www.youtube.com/watch?v=abc123")

        self.assertEqual([peak.timestamp for peak in peaks], [35.0, 15.0])

    def test_build_ydl_opts_adds_peak_index_to_output_template(self):
        clipper = VideoClipper(PipelineConfig(output_template="%(id)s_%(title).80s.%(ext)s"))

        opts = clipper.build_ydl_opts((1, 2), peak_index=3)

        self.assertEqual(opts["outtmpl"], "clips/%(id)s_%(title).80s_peak03.%(ext)s")

    def test_content_pack_subcommand_parses_arguments(self):
        parser = build_parser()

        args = parser.parse_args([
            "content-pack",
            "--url",
            "https://www.youtube.com/watch?v=abc123",
            "--audio-file",
            "audio.m4a",
            "--theme",
            "lucu",
            "--formats",
            "top_n,shorts_pack",
            "--languages",
            "id,en",
            "--top-n",
            "3",
            "--whisper-model",
            "small",
            "--whisper-device",
            "cpu",
            "--whisper-compute-type",
            "int8",
        ])

        self.assertEqual(args.command, "content-pack")
        self.assertEqual(args.audio_file, "audio.m4a")
        self.assertEqual(args.formats, "top_n,shorts_pack")
        self.assertEqual(args.languages, "id,en")
        self.assertEqual(args.top_n, 3)
        self.assertEqual(args.whisper_model, "small")
        self.assertEqual(args.whisper_device, "cpu")
        self.assertEqual(args.whisper_compute_type, "int8")


if __name__ == "__main__":
    unittest.main()
