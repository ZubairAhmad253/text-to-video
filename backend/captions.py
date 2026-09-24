"""Caption images drawn with Pillow."""
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]

# scale = font size as a fraction of the frame's shorter side
# y = vertical centre of the caption as a fraction of frame height
STYLES = {
    "bold": {"scale": 0.072, "y": 0.78, "outline": True, "box": False, "shadow": False},
    "box": {"scale": 0.058, "y": 0.80, "outline": False, "box": True, "shadow": False},
    "minimal": {"scale": 0.046, "y": 0.87, "outline": False, "box": False, "shadow": True},
}


def _load_font(px: int):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, px)
        except OSError:
            continue
    return ImageFont.load_default(size=px)


def _wrap(draw, text, font, max_width) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if not line or draw.textlength(candidate, font=font) <= max_width:
            line = candidate
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def make_caption(text: str, size: tuple[int, int], style_name: str) -> tuple[Image.Image, tuple[int, int]]:
    """Return (RGBA caption image, (x, y) position) — cropped to the caption so pasting it is fast."""
    width, height = size
    style = STYLES.get(style_name, STYLES["bold"])
    px = int(min(width, height) * style["scale"])
    font = _load_font(px)

    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    lines = _wrap(draw, text, font, width * 0.86)
    line_h = int(px * 1.25)
    block_h = line_h * len(lines)
    y = min(height * style["y"] - block_h / 2, height * 0.95 - block_h)

    if style["box"]:
        pad = px * 0.45
        box_w = max(draw.textlength(line, font=font) for line in lines)
        draw.rounded_rectangle(
            ((width - box_w) / 2 - pad, y - pad * 0.6, (width + box_w) / 2 + pad, y + block_h + pad * 0.4),
            radius=int(px * 0.35),
            fill=(0, 0, 0, 160),
        )

    for line in lines:
        x = (width - draw.textlength(line, font=font)) / 2
        if style["shadow"]:
            offset = max(2, px // 18)
            draw.text((x + offset, y + offset), line, font=font, fill=(0, 0, 0, 170))
        draw.text(
            (x, y), line, font=font, fill="white",
            stroke_width=max(2, px // 12) if style["outline"] else 0, stroke_fill="black",
        )
        y += line_h

    bbox = overlay.getbbox() or (0, 0, 1, 1)
    return overlay.crop(bbox), (bbox[0], bbox[1])


def with_opacity(img: Image.Image, opacity: float) -> Image.Image:
    r, g, b, a = img.split()
    return Image.merge("RGBA", (r, g, b, a.point(lambda v: int(v * opacity))))
