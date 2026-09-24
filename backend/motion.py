"""Camera movement over a still photo (the "Ken Burns" effect)."""
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ZOOM = 1.15  # how much the camera zooms/pans within one scene
MOVES = ["zoom_in", "pan_right", "zoom_out", "pan_left"]  # cycled scene by scene


def prepare_base(image_path, size: tuple[int, int]) -> Image.Image:
    """Return the photo fitted to the video's shape, slightly larger than the frame to leave room for motion."""
    width, height = size
    base_size = (int(width * ZOOM), int(height * ZOOM))

    img = ImageOps.exif_transpose(Image.open(image_path)).convert("RGB")
    src_ratio = img.width / img.height
    dst_ratio = width / height

    # Similar shape: crop to fill the frame.
    if max(src_ratio / dst_ratio, dst_ratio / src_ratio) < 1.5:
        return ImageOps.fit(img, base_size, Image.LANCZOS)

    # Very different shape (e.g. portrait photo in a 16:9 video): show the whole
    # photo on top of a blurred, darkened copy of itself instead of cropping most of it away.
    small = ImageOps.fit(img, (base_size[0] // 4, base_size[1] // 4))
    background = small.filter(ImageFilter.GaussianBlur(8)).resize(base_size, Image.BILINEAR)
    background = ImageEnhance.Brightness(background).enhance(0.6)
    foreground = ImageOps.contain(img, (int(base_size[0] * 0.92), int(base_size[1] * 0.92)), Image.LANCZOS)
    background.paste(foreground, ((base_size[0] - foreground.width) // 2, (base_size[1] - foreground.height) // 2))
    return background


def _ease(p: float) -> float:
    return p * p * (3 - 2 * p)  # smoothstep: slow start and end


def render_frame(base: Image.Image, size: tuple[int, int], move: str, progress: float) -> Image.Image:
    """Crop a moving window out of `base` for a point `progress` (0..1) through the scene."""
    p = _ease(max(0.0, min(1.0, progress)))
    tight = 1 / ZOOM  # window size (fraction of base) when fully zoomed in
    cx = cy = 0.5     # window position within the free space (0 = left/top, 1 = right/bottom)

    if move == "zoom_in":
        scale = 1 - (1 - tight) * p
    elif move == "zoom_out":
        scale = tight + (1 - tight) * p
    elif move == "pan_right":
        scale, cx = 0.9, p
    else:  # pan_left
        scale, cx = 0.9, 1 - p

    window_w, window_h = base.width * scale, base.height * scale
    x0 = (base.width - window_w) * cx
    y0 = (base.height - window_h) * cy
    return base.resize(size, Image.BILINEAR, box=(x0, y0, x0 + window_w, y0 + window_h))
