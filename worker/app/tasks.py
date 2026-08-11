"""تسک‌های پس‌زمینه: ساخت پیش‌نمایش واترمارک‌دار از جزوه‌ها.

واترمارک عمداً انگلیسیه تا بدون دردسر فونت فارسی و شکل‌دهی RTL کار کنه.
"""

import io

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont

from app.db import SessionLocal
from app.models import Note
from app.storage import get_bytes, put_bytes

from .celery_app import celery

PREVIEW_PAGES = 3
WATERMARK_TEXT = "NOTEBAZAR PREVIEW"
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


def _watermark(img: Image.Image) -> Image.Image:
    base = img.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = _load_font(max(28, base.size[0] // 18))
    step_x = max(260, base.size[0] // 2)
    step_y = max(200, base.size[1] // 4)
    for y in range(0, base.size[1], step_y):
        for x in range(0, base.size[0], step_x):
            draw.text((x, y), WATERMARK_TEXT, font=font, fill=(220, 30, 30, 70))
    return Image.alpha_composite(base, overlay).convert("RGB")


@celery.task(name="notebazar.generate_preview", bind=True, max_retries=3)
def generate_preview(self, note_id: int) -> None:
    db = SessionLocal()
    try:
        note = db.get(Note, note_id)
        if note is None:
            return
        raw = get_bytes(note.file_key)
        keys: list[str] = []
        if note.file_name.lower().endswith(".pdf"):
            doc = fitz.open(stream=raw, filetype="pdf")
            note.page_count = doc.page_count
            for i in range(min(PREVIEW_PAGES, doc.page_count)):
                pix = doc[i].get_pixmap(dpi=110)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                img = _watermark(img)
                buf = io.BytesIO()
                img.save(buf, "JPEG", quality=80)
                key = f"previews/{note.id}/page-{i + 1}.jpg"
                put_bytes(key, buf.getvalue(), "image/jpeg")
                keys.append(key)
            doc.close()
        # فرمت‌های غیر PDF: فعلاً بدون پیش‌نمایش (دکمه پیش‌نمایش نشون داده نمی‌شه)
        note.preview_keys = keys
        db.commit()
    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc, countdown=15)
    finally:
        db.close()
