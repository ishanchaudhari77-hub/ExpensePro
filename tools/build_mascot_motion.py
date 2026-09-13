#!/usr/bin/env python3
"""
Build a lightweight mascot motion loop and poster image for auth pages.

Requires FFmpeg (ffmpeg and ffprobe available in PATH).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


DEFAULT_SOURCE = "References/20260306_2337_New Video_simple_compose_01kk259h7cfv9t4z8gsnarra6y.mp4"
DEFAULT_OUTPUT_VIDEO = "static/mascot/rupy/rupy_idle_loop.mp4"
DEFAULT_OUTPUT_POSTER = "static/mascot/rupy/rupy_idle_loop_poster.webp"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Rupy motion assets.")
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="Input video file path.")
    parser.add_argument("--video", default=DEFAULT_OUTPUT_VIDEO, help="Output MP4 path.")
    parser.add_argument("--poster", default=DEFAULT_OUTPUT_POSTER, help="Output poster WebP path.")
    parser.add_argument("--size", type=int, default=320, help="Square output size in pixels.")
    parser.add_argument("--fps", type=int, default=24, help="Target FPS for output loop.")
    parser.add_argument("--crf", type=int, default=28, help="H264 quality CRF (lower = better quality).")
    parser.add_argument(
        "--poster-second",
        type=float,
        default=3.7,
        help="Timestamp (seconds) used to capture poster frame.",
    )
    return parser.parse_args()


def require_binary(name: str) -> None:
    if shutil.which(name):
        return
    raise SystemExit(f"Missing dependency: {name} is not available in PATH.")


def run(cmd: list[str]) -> None:
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if completed.returncode == 0:
        return
    raise SystemExit(
        f"Command failed ({completed.returncode}): {' '.join(cmd)}\n"
        f"{completed.stderr.strip()}"
    )


def main() -> None:
    args = parse_args()
    require_binary("ffmpeg")

    source = Path(args.source)
    out_video = Path(args.video)
    out_poster = Path(args.poster)

    if not source.exists():
        raise SystemExit(f"Source video not found: {source}")

    size = max(128, int(args.size))
    fps = max(12, int(args.fps))
    crf = max(16, min(40, int(args.crf)))
    poster_second = max(0.0, float(args.poster_second))

    out_video.parent.mkdir(parents=True, exist_ok=True)
    out_poster.parent.mkdir(parents=True, exist_ok=True)

    # Encode a startup-friendly H264 loop (faststart + no audio).
    run([
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-an",
        "-vf",
        f"scale={size}:{size}:flags=lanczos,fps={fps}",
        "-c:v",
        "libx264",
        "-profile:v",
        "baseline",
        "-level",
        "3.0",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-crf",
        str(crf),
        str(out_video),
    ])

    # Capture a single poster frame for fallback / reduced motion users.
    run([
        "ffmpeg",
        "-y",
        "-ss",
        f"{poster_second}",
        "-i",
        str(source),
        "-frames:v",
        "1",
        "-vf",
        f"scale={size}:{size}:flags=lanczos",
        "-c:v",
        "libwebp",
        "-lossless",
        "0",
        "-q:v",
        "75",
        "-compression_level",
        "6",
        str(out_poster),
    ])

    print(f"Motion video: {out_video}")
    print(f"Poster image: {out_poster}")


if __name__ == "__main__":
    main()
