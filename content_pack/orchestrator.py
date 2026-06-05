from __future__ import annotations

from pathlib import Path

from content_pack.audio import YtDlpAudioDownloader
from content_pack.candidates import CandidateBuilder
from content_pack.clips import ClipAssetExporter
from content_pack.exporter import ContentPackExporter
from content_pack.llm import ContentPlanner, OfflineContentPlanner
from content_pack.models import ContentPack
from content_pack.scoring import HybridScorer
from content_pack.transcriber import Transcriber
from heatmap_pipeline import HeatmapExtractor, PipelineConfig, VideoClipper


class ContentPackOrchestrator:
    def __init__(
        self,
        transcriber: Transcriber,
        heatmap_extractor: object | None = None,
        planner: ContentPlanner | None = None,
        output_root: Path = Path("content_packs"),
        exporter: ContentPackExporter | None = None,
        audio_downloader: YtDlpAudioDownloader | None = None,
        clip_exporter: ClipAssetExporter | None = None,
    ) -> None:
        self.transcriber = transcriber
        self.heatmap_extractor = heatmap_extractor or HeatmapExtractor(PipelineConfig())
        self.planner = planner or OfflineContentPlanner()
        self.output_root = output_root
        self.exporter = exporter or ContentPackExporter()
        self.audio_downloader = audio_downloader or YtDlpAudioDownloader()
        self.clip_exporter = clip_exporter or ClipAssetExporter(VideoClipper(PipelineConfig(output_dir=output_root)))

    def generate(
        self,
        url: str,
        audio_path: Path | None,
        theme: str | None,
        formats: list[str],
        languages: list[str],
        top_n: int,
        export_clips: bool = False,
    ) -> ContentPack:
        audio_result = None
        if audio_path is None:
            audio_result = self.audio_downloader.download(url, self.output_root)
            audio_path = audio_result.audio_path

        transcript = self.transcriber.transcribe(audio_path)
        peaks = self.heatmap_extractor.find_peaks(url)
        candidates = CandidateBuilder().from_peaks(peaks, transcript)
        selected_candidates = HybridScorer(theme=theme).select_top(candidates, top_n=top_n)

        clips = []
        for format_name in formats:
            clips.extend(self.planner.plan_clips(selected_candidates, format_name=format_name, languages=languages))

        video_id = peaks[0].video_id if peaks and peaks[0].video_id else "unknown_video"
        if audio_result is not None:
            video_id = audio_result.video_id
        title = peaks[0].title if peaks else (audio_result.title if audio_result else None)
        output_dir = self.output_root / video_id
        if export_clips:
            clips = self.clip_exporter.export(url, clips, output_dir)
        pack = ContentPack(
            video_id=video_id,
            source_url=url,
            title=title,
            theme=theme,
            formats=formats,
            languages=languages,
            clips=clips,
            candidates=candidates,
            output_dir=output_dir,
        )
        self.exporter.export(pack, transcript)
        return pack
