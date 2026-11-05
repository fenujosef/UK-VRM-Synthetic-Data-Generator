from __future__ import annotations

import argparse
import csv
import random
import string
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


WIDTH, HEIGHT = 1040, 222
ALLOWED_AREA = "ABCDEFGHJKLMNPRSTUVWXY"
ALLOWED_SUFFIX = "ABCDEFGHJKLMNPRSTUVWY"
AGE_CODES = [f"{n:02d}" for n in range(1, 100)]
PLATE_COLORS = {"white": (245, 245, 239), "yellow": (250, 207, 20)}
INK = (12, 14, 16)


def make_vrm(rng: random.Random) -> str:
    """UK style VRM string: 2 letters, age code, 3 letters."""
    prefix = "".join(rng.choice(ALLOWED_AREA) for _ in range(2))
    age = rng.choice(AGE_CODES)
    suffix = "".join(rng.choice(ALLOWED_SUFFIX) for _ in range(3))
    return f"{prefix}{age} {suffix}"



def load_font(font_path: str | None, size: int):

    candidates = []

    if font_path:
        candidates.append(font_path)

    candidates.extend([
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\Arial.ttf",
        r"C:\Windows\Fonts\calibrib.ttf",
        r"C:\Windows\Fonts\verdana.ttf",
    ])

    candidates.extend([
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ])

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            try:
                return ImageFont.truetype(
                    candidate,
                    size=size
                )
            except OSError:
                continue

    raise FileNotFoundError(
        "No usable TTF font found. "
    )


def draw_tracked_text(draw: ImageDraw.ImageDraw, text: str, font, y: int,
                      char_width: int, gap: int, group_gap: int) -> None:
    chars = text.replace(" ", "")
    total = 7 * char_width + 5 * gap + group_gap
    x = (WIDTH - total) // 2
    for idx, ch in enumerate(chars):
        bbox = font.getbbox(ch)
        glyph = Image.new("RGBA", (max(1, bbox[2]-bbox[0]), max(1, bbox[3]-bbox[1])), (0,0,0,0))
        gd = ImageDraw.Draw(glyph)
        gd.text((-bbox[0], -bbox[1]), ch, font=font, fill=INK+(255,))
        # Fitting glyph into a consistent character cell while preserving aspect ratio.
        target_h = 150
        max_w = 86
        scale = min(target_h / glyph.height, max_w / glyph.width)
        new_w = max(1, int(glyph.width * scale))
        new_h = max(1, int(glyph.height * scale))
        glyph = glyph.resize((new_w, new_h), Image.Resampling.LANCZOS)
        gx = x + (char_width-new_w)//2
        gy = y + (target_h-new_h)//2
        draw._image.alpha_composite(glyph, (gx, gy))
        x += char_width
        if idx == 3:
            x += group_gap
        elif idx < 6:
            x += gap


def render_plate(vrm: str, color_name: str, font_path: str | None,
                 rng: random.Random, spacing_scale: float = 1.0) -> Image.Image:
    bg = PLATE_COLORS[color_name]

    # Slightly varied reflective base.
    base = Image.new("RGB", (WIDTH, HEIGHT), bg)
    arr = np.asarray(base).astype(np.int16)
    vertical = np.linspace(2, -2, HEIGHT, dtype=np.int16)[:, None, None]
    arr = np.clip(arr + vertical, 0, 255).astype(np.uint8)
    plate = Image.fromarray(arr).convert("RGBA")
    draw = ImageDraw.Draw(plate)
    
    draw.rounded_rectangle((2, 2, WIDTH-3, HEIGHT-3), radius=5, outline=(35,35,35,210), width=3)
    draw.rounded_rectangle((7, 7, WIDTH-8, HEIGHT-8), radius=3, outline=(255,255,255,100), width=2)

    font_size = 160
    font = load_font(font_path, font_size)
    char_width = int(100 * spacing_scale)
    gap = int(22 * spacing_scale)
    group_gap = int(66 * spacing_scale)

    draw_tracked_text(ImageDraw.Draw(plate), vrm, font, 34, char_width, gap, group_gap)

    for sx in (24, WIDTH-24):
        draw.ellipse((sx-4, HEIGHT//2-4, sx+4, HEIGHT//2+4),
                     fill=(100,100,100,100), outline=(70,70,70,120))
    return plate.convert("RGB")



def motion_blur(image: Image.Image, rng: random.Random) -> Image.Image:
    arr = np.asarray(image)
    k = rng.choice([3, 5, 7, 9, 11])
    kernel = np.zeros((k, k), dtype=np.float32)
    if rng.random() < 0.5:
        kernel[k//2, :] = 1.0 / k
    else:
        np.fill_diagonal(kernel, 1.0 / k)
    return Image.fromarray(cv2.filter2D(arr, -1, kernel))


def defocus_blur(image: Image.Image, rng: random.Random) -> Image.Image:
    return image.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0.7, 2.3)))


def add_noise(image: Image.Image, rng: np.random.Generator) -> Image.Image:
    arr = np.asarray(image).astype(np.float32)
    sigma = float(rng.uniform(3, 15))
    noise = rng.normal(0, sigma, arr.shape)
    return Image.fromarray(np.clip(arr + noise, 0, 255).astype(np.uint8))


def add_dirt(image: Image.Image, rng: random.Random) -> Image.Image:
    base = image.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    w, h = base.size
    colors = [(75,65,48,55), (95,82,58,75), (45,43,38,45), (130,115,85,45)]

    for _ in range(rng.randint(12, 35)):
        side = rng.choice(["left", "right", "top", "bottom", "any"])
        if side == "left":
            x, y = rng.randint(0, w//5), rng.randint(0, h)
        elif side == "right":
            x, y = rng.randint(4*w//5, w-1), rng.randint(0, h)
        elif side == "top":
            x, y = rng.randint(0, w), rng.randint(0, h//4)
        elif side == "bottom":
            x, y = rng.randint(0, w), rng.randint(3*h//4, h-1)
        else:
            x, y = rng.randint(0, w), rng.randint(0, h)

        rx, ry = rng.randint(5, 45), rng.randint(3, 16)
        points = [(x+rng.randint(-rx,rx), y+rng.randint(-ry,ry)) for _ in range(7)]
        d.polygon(points, fill=rng.choice(colors))
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=2))
    return Image.alpha_composite(base, overlay).convert("RGB")


def add_wear(image: Image.Image, rng: random.Random) -> Image.Image:
    """Add sparse scratches, faded patches and tiny chips without hiding all text."""
    base = image.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    w, h = base.size
    for _ in range(rng.randint(8, 24)):
        x1, y1 = rng.randint(0,w-1), rng.randint(0,h-1)
        x2 = max(0, min(w-1, x1+rng.randint(-55,55)))
        y2 = max(0, min(h-1, y1+rng.randint(-5,5)))
        d.line((x1,y1,x2,y2), fill=(45,42,35,rng.randint(20,75)), width=rng.randint(1,3))
    for _ in range(rng.randint(3, 9)):
        x, y = rng.randint(0,w-1), rng.randint(0,h-1)
        r = rng.randint(2,7)
        d.ellipse((x-r,y-r,x+r,y+r), fill=(80,70,55,rng.randint(25,65)))
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=0.5))
    return Image.alpha_composite(base, overlay).convert("RGB")


def degrade(image: Image.Image, rng: random.Random, np_rng: np.random.Generator) -> tuple[Image.Image, list[str]]:
    result = image.copy()
    applied = []
    # Apply all required categories, varying order and strength per sample.
    operations = [
        ("motion_blur", lambda im: motion_blur(im, rng)),
        ("defocus_blur", lambda im: defocus_blur(im, rng)),
        ("dirt_mud", lambda im: add_dirt(im, rng)),
        ("noise", lambda im: add_noise(im, np_rng)),
        ("wear_tear", lambda im: add_wear(im, rng)),
    ]
    rng.shuffle(operations)
    for name, operation in operations:
        result = operation(result)
        applied.append(name)
    if rng.random() < 0.45:
        result = ImageEnhance.Brightness(result).enhance(rng.uniform(0.65, 0.9))
        applied.append("low_light")
    return result, applied


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--output", type=Path, default=Path("dataset"))
    parser.add_argument("--font", type=str, default=None)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.count < 1:
        raise ValueError("--count must be at least 1")

    py_rng = random.Random(args.seed)
    np_rng = np.random.default_rng(args.seed)
    clean_dir = args.output / "clean"
    degraded_dir = args.output / "degraded"
    clean_dir.mkdir(parents=True, exist_ok=True)
    degraded_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output / "manifest.csv"

    seen = set()
    rows = []
    for i in range(args.count):
        vrm = make_vrm(py_rng)
        while vrm in seen:
            vrm = make_vrm(py_rng)
        seen.add(vrm)
        color = "white" if i % 2 == 0 else "yellow"
        spacing = py_rng.choice([0.94, 1.0, 1.06])
        clean = render_plate(vrm, color, args.font, py_rng, spacing)
        degraded, operations = degrade(clean, py_rng, np_rng)
        filename = f"plate_{i+1:05d}.png"
        clean.save(clean_dir / filename, quality=95)
        degraded.save(degraded_dir / filename, quality=95)

        rows.append({
            "image_id": f"plate_{i+1:05d}",
            "vrm": vrm,
            "background": color,
            "clean_path": f"clean/{filename}",
            "degraded_path": f"degraded/{filename}",
            "spacing_scale": spacing,
            "degradation_applied": "|".join(operations),
            "seed": args.seed,
        })
        

    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {args.count} clean + {args.count} degraded images.")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
