from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from src.content_pack.models import TranscriptSegment


class Transcriber(Protocol):
    def transcribe(self, audio_path: Path) -> list[TranscriptSegment]:
        ...


class JsonTranscriptLoader:
    def __init__(self, transcript_path: Path) -> None:
        self.transcript_path = transcript_path

    def transcribe(self, audio_path: Path) -> list[TranscriptSegment]:
        payload = json.loads(self.transcript_path.read_text(encoding="utf-8"))
        return [
            TranscriptSegment(
                start=float(item["start"]),
                end=float(item["end"]),
                text=str(item["text"]),
                language=str(item.get("language", "mixed")),
            )
            for item in payload
        ]


class FasterWhisperTranscriber:
    def __init__(self, model_size: str = "medium", device: str = "auto", compute_type: str = "default") -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

    def transcribe(self, audio_path: Path) -> list[TranscriptSegment]:
        try:
            from faster_whisper import WhisperModel
        except ModuleNotFoundError as exc:
            raise RuntimeError("faster-whisper belum terpasang. Jalankan: python3 -m pip install faster-whisper") from exc

        model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        raw_segments, _info = model.transcribe(str(audio_path), vad_filter=True)
        return [
            TranscriptSegment(
                start=float(segment.start),
                end=float(segment.end),
                text=segment.text.strip(),
                language="mixed",
            )
            for segment in raw_segments
            if segment.text.strip()
        ]
