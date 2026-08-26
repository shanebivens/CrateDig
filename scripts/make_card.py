#!/usr/bin/env python3
"""Draw the share card and touch icon in the site's own materials.

Run by hand when the identity changes; the PNGs are committed, so nothing in CI
depends on this. Fonts come in via --anton and --courier (TTF paths).
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent

PAPER = "#e4e1d8"
CARD = "#f1efe9"
INK = "#15150f"
FAINT = "#8a877c"
ORANGE = "#ff4e00"


def sticker(text, font, pad_x=26, pad_y=14, angle=-2.0, bg=ORANGE, fg=INK):
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    x0, y0, x1, y1 = probe.textbbox((0, 0), text, font=font)
    w, h = x1 - x0 + pad_x * 2, y1 - y0 + pad_y * 2
    tile = Image.new("RGBA", (w, h), bg)
    ImageDraw.Draw(tile).text((pad_x - x0, pad_y - y0), text, font=font, fill=fg)
    return tile.rotate(angle, expand=True, resample=Image.BICUBIC)


def card(anton, courier):
    img = Image.new("RGB", (1200, 630), PAPER)
    draw = ImageDraw.Draw(img)

    # the bin divider
    draw.rectangle((36, 36, 1163, 593), outline=INK, width=6)
    draw.rectangle((36, 36, 1163, 593), outline=None)
    inner = Image.new("RGB", (1116, 546), CARD)
    img.paste(inner, (42, 42))
    draw.rectangle((36, 36, 1163, 593), outline=INK, width=6)

    wordmark = ImageFont.truetype(anton, 190)
    tag = ImageFont.truetype(courier, 34)
    small = ImageFont.truetype(courier, 24)

    draw.text((92, 130), "CRATEDIG", font=wordmark, fill=INK)
    draw.text((98, 378), "One song in, an afternoon out", font=tag, fill=INK)
    draw.text((1016, 76), "CD-001", font=small, fill=FAINT)

    tile = sticker("DIG · FALL IN · BRING ONE BACK", ImageFont.truetype(courier, 30))
    img.paste(tile, (92, 464), tile)

    out = ROOT / "assets" / "card.png"
    img.save(out, optimize=True)
    print(f"wrote {out.relative_to(ROOT)}  {img.size}")


def touch_icon(anton):
    img = Image.new("RGB", (180, 180), PAPER)
    tile = sticker("CD", ImageFont.truetype(anton, 92), pad_x=26, pad_y=10, angle=-5)
    img.paste(tile, ((180 - tile.width) // 2, (180 - tile.height) // 2), tile)
    out = ROOT / "assets" / "icon-180.png"
    img.save(out, optimize=True)
    print(f"wrote {out.relative_to(ROOT)}  {img.size}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--anton", required=True)
    parser.add_argument("--courier", required=True)
    args = parser.parse_args()
    card(args.anton, args.courier)
    touch_icon(args.anton)
