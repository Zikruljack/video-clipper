from __future__ import annotations

import argparse
import json
import logging
import math
import random
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from shutil import which
from typing import Any, Iterable
from urllib.parse import urlparse

try:
    import yt_dlp
    from yt_dlp.utils import download_range_func
except ModuleNotFoundError:  # Allows unit tests that do not hit the network/downloader.
    yt_dlp = None  # type: ignore[assignment]
    download_range_func = None  # type: ignore[assignment]

LOGGER = logging.getLogger(__name__)
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}


@dataclass(frozen=True)
class PipelineConfig:
    peak_k: float = 1.5
    pre_margin_seconds: float = 10.0
    post_margin_seconds: float = 15.0
    base_delay_seconds: float = 3.0
    jitter_seconds: float = 4.0
    max_retries: int = 3
    output_dir: Path = Path("clips")
    output_template: str = "%(id)s_%(title).80s.%(ext)s"
    format_selector: str = "bestvideo[vcodec^=avc1][ext=mp4]+bestaudio[acodec^=mp4a][ext=m4a]/best[vcodec^=avc1][acodec^=mp4a][ext=mp4]"
    socket_timeout_seconds: float = 30.0
    js_runtime: str = "node"
    js_runtime_path: str | None = which("node")


@dataclass(frozen=True)
class HeatmapPoint:
    start_time: float
    end_time: float | None
    value: float


@dataclass(frozen=True)
class PeakResult:
    url: str
    video_id: str | None
    title: str | None
    timestamp: float
    value: float
    mean: float
    stddev: float
    threshold: float
    duration: float | None


@dataclass(frozen=True)
class ClipJobResult:
    url: str
    ok: bool
    status: str
    peak: PeakResult | None = None
    section: str | None = None
    error: str | None = None


def require_yt_dlp() -> Any:
    if yt_dlp is None:
        raise RuntimeError("yt-dlp belum terpasang. Jalankan: python3 -m pip install -U yt-dlp")
    return yt_dlp


def is_youtube_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":", 1)[0]
    return parsed.scheme in {"http", "https"} and host in YOUTUBE_HOSTS


def first_non_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


class HeatmapExtractor:
    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()

    def extract_metadata(self, url: str) -> dict[str, Any]:
        if not is_youtube_url(url):
            raise ValueError(f"URL bukan YouTube: {url}")

        ytdlp = require_yt_dlp()
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": False,
            "socket_timeout": self.config.socket_timeout_seconds,
            "js_runtimes": self.build_js_runtimes(),
        }
        with ytdlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    def find_peak(self, url: str) -> PeakResult | None:
        peaks = self.find_peaks(url)
        return peaks[0] if peaks else None

    def find_peaks(self, url: str) -> list[PeakResult]:
        try:
            info = self.extract_metadata(url)
            points = self.extract_heatmap_points(info)
        except Exception as exc:
            LOGGER.warning("metadata_or_heatmap_failed url=%s error=%s", url, exc)
            return []

        if not points:
            LOGGER.info("NO_HEATMAP_DATA url=%s video_id=%s", url, info.get("id"))
            return []

        values = [point.value for point in points]
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        stddev = math.sqrt(variance)
        threshold = mean + (self.config.peak_k * stddev)
        candidates = [point for point in points if point.value >= threshold]

        if not candidates:
            LOGGER.info("NO_HEATMAP_PEAK url=%s video_id=%s", url, info.get("id"))
            return []

        duration = self.safe_float(info.get("duration"))
        return [
            PeakResult(
                url=url,
                video_id=info.get("id"),
                title=info.get("title"),
                timestamp=self.resolve_point_timestamp(point),
                value=point.value,
                mean=mean,
                stddev=stddev,
                threshold=threshold,
                duration=duration,
            )
            for point in sorted(candidates, key=lambda candidate: candidate.value, reverse=True)
        ]

    def extract_heatmap_points(self, info: dict[str, Any]) -> list[HeatmapPoint]:
        heatmap = self.find_heatmap_object(info)
        if not heatmap:
            return []

        points: list[HeatmapPoint] = []
        for raw_point in heatmap:
            point = self.parse_heatmap_point(raw_point)
            if point is not None:
                points.append(point)
        return points

    def find_heatmap_object(self, info: dict[str, Any]) -> Iterable[dict[str, Any]] | None:
        heatmap = info.get("heatmap")
        if heatmap:
            return heatmap

        chapters = info.get("chapters") or []
        for chapter in chapters:
            heatmap = chapter.get("heatmap") if isinstance(chapter, dict) else None
            if heatmap:
                return heatmap
        return None

    def parse_heatmap_point(self, raw_point: dict[str, Any]) -> HeatmapPoint | None:
        try:
            start_time = self.safe_float(
                first_non_none(
                    raw_point.get("start_time"),
                    raw_point.get("startTime"),
                    raw_point.get("time"),
                    raw_point.get("t"),
                )
            )
            end_time = self.safe_float(first_non_none(raw_point.get("end_time"), raw_point.get("endTime")))
            value = self.safe_float(
                first_non_none(
                    raw_point.get("value"),
                    raw_point.get("heatMarkerIntensityScoreNormalized"),
                    raw_point.get("intensity"),
                    raw_point.get("v"),
                )
            )
            if start_time is None or value is None:
                return None
            return HeatmapPoint(start_time=start_time, end_time=end_time, value=value)
        except (TypeError, ValueError):
            return None

    def resolve_point_timestamp(self, point: HeatmapPoint) -> float:
        if point.end_time is None:
            return point.start_time
        return point.start_time + ((point.end_time - point.start_time) / 2)

    def safe_float(self, value: Any) -> float | None:
        if value is None:
            return None
        return float(value)

    def build_js_runtimes(self) -> dict[str, dict[str, str] | dict[str, None]]:
        if not self.config.js_runtime:
            return {}
        runtime_config: dict[str, str] | dict[str, None]
        runtime_config = {"path": self.config.js_runtime_path} if self.config.js_runtime_path else {}
        return {self.config.js_runtime: runtime_config}


class VideoClipper:
    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

    def build_section(self, peak: PeakResult) -> str:
        start = max(0.0, peak.timestamp - self.config.pre_margin_seconds)
        end = peak.timestamp + self.config.post_margin_seconds
        if peak.duration is not None:
            end = min(peak.duration, end)
        return f"*{start:.3f}-{end:.3f}"

    def build_range(self, peak: PeakResult) -> tuple[float, float]:
        start = max(0.0, peak.timestamp - self.config.pre_margin_seconds)
        end = peak.timestamp + self.config.post_margin_seconds
        if peak.duration is not None:
            end = min(peak.duration, end)
        return start, end

    def build_ydl_opts(self, time_range: tuple[float, float], peak_index: int = 1) -> dict[str, Any]:
        if download_range_func is None:
            require_yt_dlp()
            raise RuntimeError("yt-dlp download_range_func tidak tersedia pada versi ini")

        output_path = self.config.output_dir / self.output_template_for_peak(peak_index)
        return {
            "format": self.config.format_selector,
            "merge_output_format": "mp4",
            "outtmpl": str(output_path),
            "download_ranges": download_range_func([], [list(time_range)]),
            "force_keyframes_at_cuts": False,
            "socket_timeout": self.config.socket_timeout_seconds,
            "js_runtimes": {self.config.js_runtime: {"path": self.config.js_runtime_path}} if self.config.js_runtime_path else {self.config.js_runtime: {}},
            "postprocessor_args": {
                "ffmpeg": ["-c", "copy"],
            },
        }

    def output_template_for_peak(self, peak_index: int) -> str:
        stem, dot, extension = self.config.output_template.rpartition(".")
        if not dot:
            return f"{self.config.output_template}_peak{peak_index:02d}"
        return f"{stem}_peak{peak_index:02d}.{extension}"

    def download_peak_clip(self, url: str, peak: PeakResult, peak_index: int = 1) -> str:
        if not is_youtube_url(url):
            raise ValueError(f"URL bukan YouTube: {url}")

        ytdlp = require_yt_dlp()
        section = self.build_section(peak)
        time_range = self.build_range(peak)
        with ytdlp.YoutubeDL(self.build_ydl_opts(time_range, peak_index=peak_index)) as ydl:
            ydl.download([url])
        return section

    def download_with_retries(self, url: str, peak: PeakResult, peak_index: int = 1) -> ClipJobResult:
        for attempt in range(1, self.config.max_retries + 1):
            try:
                self.sleep_with_jitter()
                section = self.download_peak_clip(url=url, peak=peak, peak_index=peak_index)
                return ClipJobResult(url=url, ok=True, status="DONE", peak=peak, section=section)
            except Exception as exc:
                message = str(exc)
                if "429" in message or "Too Many Requests" in message:
                    backoff = self.backoff_seconds(attempt)
                    LOGGER.warning("HTTP_429_BACKOFF url=%s attempt=%s sleep=%s", url, attempt, backoff)
                    time.sleep(backoff)
                    continue
                LOGGER.warning("CLIP_FAILED url=%s error=%s", url, exc)
                return ClipJobResult(url=url, ok=False, status="CLIP_FAILED", peak=peak, error=message)
        return ClipJobResult(url=url, ok=False, status="HTTP_429_MAX_RETRIES", peak=peak)

    def sleep_with_jitter(self) -> None:
        delay = self.config.base_delay_seconds + random.uniform(0, self.config.jitter_seconds)
        time.sleep(delay)

    def backoff_seconds(self, attempt: int) -> float:
        return min(120.0, (2**attempt) + random.uniform(0, self.config.jitter_seconds))


def serialize_result(result: ClipJobResult) -> dict[str, Any]:
    payload = asdict(result)
    if payload.get("peak"):
        payload["peak"] = asdict(result.peak) if result.peak else None
    return payload


def process_urls(urls: list[str], config: PipelineConfig) -> list[ClipJobResult]:
    extractor = HeatmapExtractor(config=config)
    clipper = VideoClipper(config=config)
    results: list[ClipJobResult] = []

    for url in urls:
        if not is_youtube_url(url):
            results.append(ClipJobResult(url=url, ok=False, status="INVALID_URL"))
            continue

        peaks = extractor.find_peaks(url)
        if not peaks:
            results.append(ClipJobResult(url=url, ok=False, status="NO_HEATMAP_PEAK"))
            continue

        for peak_index, peak in enumerate(peaks, start=1):
            results.append(clipper.download_with_retries(url=url, peak=peak, peak_index=peak_index))
    return results


def load_urls(args: argparse.Namespace) -> list[str]:
    urls = list(args.url or [])
    if args.input_file:
        urls.extend(
            line.strip()
            for line in Path(args.input_file).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        )
    return urls


def add_clip_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--url", action="append", help="YouTube URL. Bisa dipakai berulang.")
    parser.add_argument("--input-file", help="File teks berisi URL per baris.")
    parser.add_argument("--output-dir", default="clips")
    parser.add_argument("--k", type=float, default=1.5)
    parser.add_argument("--pre", type=float, default=10.0)
    parser.add_argument("--post", type=float, default=15.0)
    parser.add_argument("--base-delay", type=float, default=3.0)
    parser.add_argument("--jitter", type=float, default=4.0)
    parser.add_argument("--json", action="store_true", help="Cetak hasil JSON untuk dashboard/automation.")


def add_content_pack_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--url", required=True, help="YouTube URL sumber.")
    parser.add_argument("--audio-file", required=True, help="Path audio full video untuk transkripsi.")
    parser.add_argument("--theme", help="Tema konten. Jika kosong, mode discovery dapat ditambahkan nanti.")
    parser.add_argument("--formats", default="best_moments,shorts_pack")
    parser.add_argument("--languages", default="id,en")
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--output-dir", default="content_packs")
    parser.add_argument("--transcript-json", help="Fixture transcript JSON untuk dry run/test murah.")
    parser.add_argument("--peaks-json", help="Fixture heatmap peaks JSON untuk dry run/test murah.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="YouTube heatmap automated clipping CLI")
    subparsers = parser.add_subparsers(dest="command")

    clip_parser = subparsers.add_parser("clip", help="Download heatmap-based clips.")
    add_clip_arguments(clip_parser)

    content_pack_parser = subparsers.add_parser("content-pack", help="Generate editor-ready content pack.")
    add_content_pack_arguments(content_pack_parser)

    add_clip_arguments(parser)
    return parser


def comma_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def run_content_pack_command(args: argparse.Namespace) -> int:
    from content_pack.llm import OfflineContentPlanner
    from content_pack.orchestrator import ContentPackOrchestrator
    from content_pack.heatmap import JsonPeakLoader
    from content_pack.transcriber import FasterWhisperTranscriber, JsonTranscriptLoader

    transcriber = JsonTranscriptLoader(Path(args.transcript_json)) if args.transcript_json else FasterWhisperTranscriber()
    heatmap_extractor = JsonPeakLoader(Path(args.peaks_json)) if args.peaks_json else None
    orchestrator = ContentPackOrchestrator(
        transcriber=transcriber,
        heatmap_extractor=heatmap_extractor,
        output_root=Path(args.output_dir),
        planner=OfflineContentPlanner(),
    )
    pack = orchestrator.generate(
        url=args.url,
        audio_path=Path(args.audio_file),
        theme=args.theme,
        formats=comma_list(args.formats),
        languages=comma_list(args.languages),
        top_n=args.top_n,
    )
    print(json.dumps(pack.to_dict(), indent=2, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "command") or args.command is None:
        args.command = "clip"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.command == "content-pack":
        return run_content_pack_command(args)

    urls = load_urls(args)
    if not urls:
        parser.error("minimal satu --url atau --input-file wajib diisi")

    config = PipelineConfig(
        peak_k=args.k,
        pre_margin_seconds=args.pre,
        post_margin_seconds=args.post,
        base_delay_seconds=args.base_delay,
        jitter_seconds=args.jitter,
        output_dir=Path(args.output_dir),
    )
    results = process_urls(urls=urls, config=config)

    if args.json:
        print(json.dumps([serialize_result(result) for result in results], indent=2, ensure_ascii=False))
    else:
        for result in results:
            print(f"{result.status}\t{result.url}\t{result.section or ''}")

    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
