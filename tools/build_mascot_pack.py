#!/usr/bin/env python3
"""
Build a web-friendly Rupy mascot pack from a single 2x2 expression sheet.

Default source is the collage already present in the project References folder.
Output is written to static/mascot/rupy as optimized WebP images and a manifest.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Tuple

from PIL import Image


DEFAULT_SOURCE = (
    "References/"
    "different-expressions_ndGWLgHWQr-_fiBEhd5ITw_J-XBt_lJRGi9DelUqe4epw_cover.jpeg"
)
DEFAULT_OUTPUT = "static/mascot/rupy"


# The source sheet is arranged as:
# top-left: surprised, top-right: sad, bottom-left: warning, bottom-right: happy.
EMOTION_MAP: Dict[str, Tuple[int, int]] = {
    "thinking": (0, 0),
    "error": (1, 0),
    "warning": (0, 1),
    "celebrate": (1, 1),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Rupy mascot web assets.")
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help="Path to source 2x2 expression image.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="Output directory for generated assets.",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=640,
        help="Primary output size in pixels (square).",
    )
    parser.add_argument(
        "--thumb-size",
        type=int,
        default=320,
        help="Thumbnail size in pixels (square).",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=88,
        help="WebP quality (0-100).",
    )
    return parser.parse_args()


def save_webp(image: Image.Image, path: Path, quality: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="WEBP", quality=quality, method=6)


def main() -> None:
    args = parse_args()
    source_path = Path(args.source)
    output_dir = Path(args.output)

    if not source_path.exists():
        raise SystemExit(f"Source file not found: {source_path}")

    quality = max(10, min(100, int(args.quality)))
    target_size = max(128, int(args.size))
    thumb_size = max(96, int(args.thumb_size))

    with Image.open(source_path) as src_img:
        source = src_img.convert("RGB")

    width, height = source.size
    half_w = width // 2
    half_h = height // 2
    if half_w <= 0 or half_h <= 0:
        raise SystemExit(f"Invalid source image dimensions: {source.size}")

    assets: Dict[str, str] = {}

    for emotion, (grid_x, grid_y) in EMOTION_MAP.items():
        left = grid_x * half_w
        top = grid_y * half_h
        right = left + half_w
        bottom = top + half_h

        tile = source.crop((left, top, right, bottom))
        tile_main = tile.resize((target_size, target_size), Image.Resampling.LANCZOS)
        tile_thumb = tile.resize((thumb_size, thumb_size), Image.Resampling.LANCZOS)

        main_name = f"rupy_{emotion}.webp"
        thumb_name = f"rupy_{emotion}_{thumb_size}.webp"
        save_webp(tile_main, output_dir / main_name, quality)
        save_webp(tile_thumb, output_dir / thumb_name, quality)

        assets[emotion] = main_name
        assets[f"{emotion}_thumb"] = thumb_name

    # Reuse the happy face as idle so UI always has a neutral default.
    idle_source = output_dir / assets["celebrate"]
    idle_target = output_dir / "rupy_idle.webp"
    idle_target.write_bytes(idle_source.read_bytes())
    assets["idle"] = idle_target.name

    manifest = {
        "source": str(source_path).replace("\\", "/"),
        "output_dir": str(output_dir).replace("\\", "/"),
        "size": target_size,
        "thumb_size": thumb_size,
        "quality": quality,
        "assets": assets,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Generated mascot pack in: {output_dir}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
