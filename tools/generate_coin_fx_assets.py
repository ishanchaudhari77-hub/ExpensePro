#!/usr/bin/env python3
"""
Generate lightweight coin FX assets for the Rupy mascot widget.

Outputs:
  - static/mascot/rupy/fx/rupee-coin.png
  - static/mascot/rupy/fx/rupee-coin-glow.png
  - static/mascot/rupy/fx/rupee-particle.png
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


OUT_DIR = Path("static/mascot/rupy/fx")


def draw_coin() -> Image.Image:
    image = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")

    draw.ellipse((12, 12, 148, 148), fill=(179, 112, 16, 255))
    draw.ellipse((18, 18, 142, 142), fill=(246, 201, 62, 255))
    draw.ellipse((28, 28, 132, 132), fill=(255, 223, 97, 255))
    draw.ellipse((42, 42, 118, 118), fill=(240, 183, 40, 255))

    draw.ellipse((38, 30, 88, 72), fill=(255, 245, 170, 170))
    draw.ellipse((30, 86, 66, 116), fill=(255, 240, 150, 100))

    draw.line((78, 52, 78, 106), fill=(132, 78, 8, 255), width=6)
    draw.arc((60, 54, 104, 84), start=200, end=360, fill=(132, 78, 8, 255), width=6)
    draw.arc((60, 76, 104, 106), start=0, end=160, fill=(132, 78, 8, 255), width=6)

    return image


def draw_coin_glow(coin: Image.Image) -> Image.Image:
    glow = Image.new("RGBA", (220, 220), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow, "RGBA")
    draw.ellipse((18, 18, 202, 202), fill=(251, 191, 36, 90))
    draw.ellipse((36, 36, 184, 184), fill=(250, 204, 21, 95))
    draw.ellipse((64, 64, 156, 156), fill=(255, 255, 255, 88))
    glow = glow.filter(ImageFilter.GaussianBlur(4))

    coin_layer = coin.resize((146, 146), Image.Resampling.LANCZOS)
    glow.alpha_composite(coin_layer, dest=(37, 37))
    return glow


def draw_particle() -> Image.Image:
    image = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.ellipse((8, 8, 52, 52), fill=(252, 211, 77, 235))
    draw.ellipse((20, 20, 40, 40), fill=(255, 243, 186, 220))
    draw.polygon([(30, 2), (35, 25), (58, 30), (35, 35), (30, 58), (25, 35), (2, 30), (25, 25)], fill=(255, 255, 255, 90))
    return image


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    coin = draw_coin()
    coin_glow = draw_coin_glow(coin)
    particle = draw_particle()

    coin.save(OUT_DIR / "rupee-coin.png", format="PNG", optimize=True)
    coin_glow.save(OUT_DIR / "rupee-coin-glow.png", format="PNG", optimize=True)
    particle.save(OUT_DIR / "rupee-particle.png", format="PNG", optimize=True)

    print("Generated FX assets in static/mascot/rupy/fx")


if __name__ == "__main__":
    main()
