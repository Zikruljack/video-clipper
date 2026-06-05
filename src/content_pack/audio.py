from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yt_dlp
except ModuleNotFoundError:
    yt_dlp = None  # type: ignore[assignment]


@dataclass(frozen=True)
class AudioDownloadResult:
    video_id: str
    title: str | None
    audio_path: Path


def default_audio_path(output_root: Path, video_id: str) -> Path:
    return output_root / video_id / "audio" / "source.m4a"


class YtDlpAudioDownloader:
    def __init__(self, ytdlp_module: Any | None = None) -> None:
        self.ytdlp_module = ytdlp_module or yt_dlp

    def download(self, url: str, output_root: Path) -> AudioDownloadResult:
        if self.ytdlp_module is None:
            raise RuntimeError("yt-dlp belum terpasang. Jalankan: python3 -m pip install -U yt-dlp")

        with self.ytdlp_module.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(url, download=False)

        video_id = str(info.get("id") or "unknown_video")
        audio_path = default_audio_path(output_root, video_id)
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        output_template = str(audio_path.with_suffix(".%(ext)s"))
        opts = {
            "format": "bestaudio[ext=m4a]/bestaudio",
            "outtmpl": output_template,
            "quiet": False,
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}],
        }
        with self.ytdlp_module.YoutubeDL(opts) as ydl:
            ydl.download([url])
        return AudioDownloadResult(video_id=video_id, title=info.get("title"), audio_path=audio_path)
