from __future__ import annotations

from pathlib import Path

from content_pack.candidates import CandidateBuilder
from content_pack.exporter import ContentPackExporter
from content_pack.llm import ContentPlanner, OfflineContentPlanner
from content_pack.models import ContentPack
from content_pack.scoring import HybridScorer
from content_pack.transcriber import Transcriber
from heatmap_pipeline import HeatmapExtractor, PipelineConfig


class ContentPackOrchestrator:
    def __init__(self, transcriber: Transcriber, heatmap_extractor: object | None = None, planner: ContentPlanner | None = None, output_root: Path = Path("content_packs"), exporter: ContentPackExporter | None = None) -> None:
        self.transcriber = transcriber
        self.heatmap_extractor = heatmap_extractor or HeatmapExtractor(PipelineConfig())
        self.planner = planner or OfflineContentPlanner()
        self.output_root = output_root
        self.exporter = exporter or ContentPackExporter()

    def generate(self, url: str, audio_path: Path, theme: str | None, formats: list[str], languages: list[str], top_n: int) -> ContentPack:
        transcript = self.transcriber.transcribe(audio_path)
        peaks = self.heatmap_extractor.find_peaks(url)
        candidates = CandidateBuilder().from_peaks(peaks, transcript)
        selected_candidates = HybridScorer(theme=theme).select_top(candidates, top_n=top_n)

        clips = []
        for format_name in formats:
            clips.extend(self.planner.plan_clips(selected_candidates, format_name=format_name, languages=languages))

        video_id = peaks[0].video_id if peaks and peaks[0].video_id else "unknown_video"
        title = peaks[0].title if peaks else None
        output_dir = self.output_root / video_id
        pack = ContentPack(video_id=video_id, source_url=url, title=title, theme=theme, formats=formats, languages=languages, clips=clips, candidates=candidates, output_dir=output_dir)
        self.exporter.export(pack, transcript)
        return pack
