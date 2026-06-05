from __future__ import annotations

import json
from pathlib import Path

from content_pack.models import ContentPack, TranscriptSegment
from content_pack.srt import segments_to_srt


class ContentPackExporter:
    def export(self, pack: ContentPack, transcript: list[TranscriptSegment]) -> None:
        pack.output_dir.mkdir(parents=True, exist_ok=True)
        (pack.output_dir / "clips").mkdir(exist_ok=True)
        transcripts_dir = pack.output_dir / "transcripts"
        transcripts_dir.mkdir(exist_ok=True)
        metadata_dir = pack.output_dir / "metadata"
        metadata_dir.mkdir(exist_ok=True)

        self.write_json(pack.output_dir / "content_pack.json", pack.to_dict())
        self.write_json(pack.output_dir / "timeline.json", self.timeline_payload(pack))
        self.write_json(metadata_dir / "candidates.json", [candidate.to_dict() for candidate in pack.candidates])
        self.write_json(transcripts_dir / "full.json", [segment.to_dict() for segment in transcript])
        (transcripts_dir / "full.srt").write_text(segments_to_srt(transcript), encoding="utf-8")
        (pack.output_dir / "script_id.md").write_text(self.script_markdown(pack, "id"), encoding="utf-8")
        (pack.output_dir / "script_en.md").write_text(self.script_markdown(pack, "en"), encoding="utf-8")
        (pack.output_dir / "editor_notes.md").write_text(self.editor_notes(pack), encoding="utf-8")

    def write_json(self, path: Path, payload: object) -> None:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def timeline_payload(self, pack: ContentPack) -> dict[str, object]:
        return {"video_id": pack.video_id, "theme": pack.theme, "clips": [{"clip_id": clip.clip_id, "rank": clip.rank, "source_start": clip.source_start, "source_end": clip.source_end, "local_path": str(clip.local_path) if clip.local_path else None, "narration_id": clip.narration_id, "narration_en": clip.narration_en} for clip in pack.clips]}

    def script_markdown(self, pack: ContentPack, language: str) -> str:
        lines = [f"# {pack.title or pack.video_id}", "", f"Theme: {pack.theme or 'auto'}", ""]
        for clip in pack.clips:
            title = clip.title_id if language == "id" else clip.title_en
            narration = clip.narration_id if language == "id" else clip.narration_en
            lines.extend([f"## {clip.clip_id}: {title}", "", narration, ""])
        return "\n".join(lines)

    def editor_notes(self, pack: ContentPack) -> str:
        lines = [f"# Editor Notes: {pack.title or pack.video_id}", ""]
        for clip in pack.clips:
            lines.append(f"- {clip.clip_id}: {clip.source_start:.3f}-{clip.source_end:.3f}, score={clip.scores.get('final_score', 0):.3f}")
        return "\n".join(lines) + "\n"
