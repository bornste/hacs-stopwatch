"""Generate the brand images of Stopwatch Plus (icon and logo, light and dark).

Usage, from the repository root:

    pip install cairosvg pillow
    python docs/brand/generate.py path/to/ReadexPro-SemiBold.ttf

The icon SVGs in docs/brand are written as well; the PNG files go to
custom_components/stopwatch_plus/brand. Readex Pro (weight 600, SemiBold) is available
from Google Fonts.
"""

from __future__ import annotations

import io
from pathlib import Path
import sys

import cairosvg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
SVG_DIR = ROOT / "docs" / "brand"
PNG_DIR = ROOT / "custom_components" / "stopwatch_plus" / "brand"


def palette(dark: bool) -> dict[str, str]:
    """Return the colors for the light or the dark theme."""
    if dark:
        return {
            "body": "#818CF8",
            "accent": "#FBBF24",
            "face": "#1F2937",
            "text": "#F9FAFB",
        }
    return {
        "body": "#4F46E5",
        "accent": "#F59E0B",
        "face": "#FFFFFF",
        "text": "#111827",
    }


def icon_svg(colors: dict[str, str]) -> str:
    """Return the icon: a stopwatch with a plus on its face."""
    # The square viewBox is trimmed to the drawing, so there are no empty edges
    body, accent, face = colors["body"], colors["accent"], colors["face"]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="9 8 238 238" \
width="256" height="256">
  <rect x="114" y="22" width="28" height="30" rx="4" fill="{body}"/>
  <rect x="96" y="8" width="64" height="22" rx="11" fill="{body}"/>
  <rect x="190" y="52" width="22" height="34" rx="6" fill="{body}" \
transform="rotate(45 201 69)"/>
  <circle cx="128" cy="146" r="100" fill="{body}"/>
  <circle cx="128" cy="146" r="76" fill="{face}"/>
  <rect x="84" y="134" width="88" height="24" rx="12" fill="{accent}"/>
  <rect x="116" y="102" width="24" height="88" rx="12" fill="{accent}"/>
</svg>
"""


def render(svg: str, size: int) -> Image.Image:
    """Render an SVG to a square RGBA image."""
    png = cairosvg.svg2png(
        bytestring=svg.encode(), output_width=size, output_height=size
    )
    return Image.open(io.BytesIO(png)).convert("RGBA")


def logo(colors: dict[str, str], font_path: str, height: int) -> Image.Image:
    """Return the logo: icon on the left, wordmark "Stopwatch Plus" on the right."""
    scale = 4  # draw large, then scale down for smooth edges
    size = height * scale
    icon = render(icon_svg(colors), size)
    font = ImageFont.truetype(font_path, int(size * 0.50))
    words = [("Stopwatch", colors["text"]), (" Plus", colors["body"])]
    measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    widths = [measure.textlength(word, font=font) for word, _ in words]
    gap = int(size * 0.22)

    image = Image.new("RGBA", (size + gap + int(sum(widths)) + size, size))
    image.paste(icon, (0, 0), icon)
    draw = ImageDraw.Draw(image)
    x = size + gap
    for (word, color), width in zip(words, widths, strict=True):
        # Centred on the round body of the icon, slightly below the middle
        draw.text((x, size * 0.57), word, fill=color, font=font, anchor="lm")
        x += width

    image = image.crop((0, 0, image.getbbox()[2], size))
    return image.resize((round(image.width / scale), height), Image.LANCZOS)


def main(font_path: str) -> None:
    """Write all SVG and PNG files."""
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    for dark in (False, True):
        colors = palette(dark)
        prefix = "dark_" if dark else ""
        svg = icon_svg(colors)
        (SVG_DIR / f"{prefix}icon.svg").write_text(svg, encoding="utf-8")
        images = {
            f"{prefix}icon.png": render(svg, 256),
            f"{prefix}icon@2x.png": render(svg, 512),
            f"{prefix}logo.png": logo(colors, font_path, 128),
            f"{prefix}logo@2x.png": logo(colors, font_path, 256),
        }
        for name, image in images.items():
            image.save(PNG_DIR / name, optimize=True)
            print(name, image.size)


if __name__ == "__main__":
    main(sys.argv[1])
