"""رندر صفحه‌های PDF با واترمارک شخصی خریدار — نسخه مخصوص هر نفر.

واترمارک ASCII نگه داشته می‌شه (آیدی تلگرام + یوزرنیم) تا بدون فونت فارسی
و شکل‌دهی RTL هم تمیز چاپ بشه.
"""

import io

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont

RENDER_DPI = 130
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _load_font(size: int):
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_page(file_bytes: bytes, file_name: str, page_index: int, watermark: str) -> bytes:
    if not file_name.lower().endswith(".pdf"):
        raise ValueError("only pdf files are supported for online viewing")
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        pix = doc[page_index].get_pixmap(dpi=RENDER_DPI)
    finally:
        doc.close()

    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

    # نوار سربرگ با مشخصات خریدار
    header_h = 44
    header = Image.new("RGB", (img.size[0], img.size[1] + header_h), "white")
    header.paste(img, (0, header_h))
    draw = ImageDraw.Draw(header)
    draw.rectangle([0, 0, img.size[0], header_h], fill=(249, 248, 247))
    draw.rectangle([0, header_h - 1, img.size[0], header_h], fill=(230, 229, 227))
    draw.text(
        (16, header_h // 2),
        f"Licensed to {watermark} — NoteBazar",
        font=_load_font(16),
        fill=(125, 122, 117),
        anchor="lm",
    )

    # واترمارک مورب تکرارشونده
    base = header.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    font = _load_font(max(26, base.size[0] // 22))
    step_x = max(240, base.size[0] // 2)
    step_y = max(180, base.size[1] // 5)
    for y in range(0, base.size[1], step_y):
        for x in range(0, base.size[0], step_x):
            od.text((x, y), watermark, font=font, fill=(220, 30, 30, 45))
    out = Image.alpha_composite(base, overlay).convert("RGB")

    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=82)
    return buf.getvalue()
