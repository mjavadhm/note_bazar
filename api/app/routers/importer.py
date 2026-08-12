"""ایمپورت جزوه از کانال‌های کراول‌شده — فقط ادمین.

دو مسیر:
  POST /import/notes  — تک‌فایل multipart (آپلود مستقیم یا telegram_file_id)
  POST /import/crawl  — دسته‌ای JSON دقیقاً با خروجی کراولر tgarchive:
                        course_name, professor, term («4041»), university,
                        doc_type, tags, media_type, body (پست متنی ← فایل txt)
درخت دانشگاه ← دانشکده ← درس ← استاد خودکار find-or-create و تأییدشده ساخته می‌شه.

نکته مهم: telegram_file_id باید متعلق به همین بات (نوت‌بازار) باشه —
file_id بات‌های دیگه (مثل بات کراولر) برای دانلود معتبر نیست.
"""

import mimetypes
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_admin
from ..jobs import enqueue_preview
from ..models import Course, Faculty, Note, Professor, Status, University, User
from ..normalize import doc_type, term_display
from ..storage import put_bytes
from ..telegram_files import download_telegram_file
from .notes import MAX_FILE_SIZE

router = APIRouter(prefix="/import", tags=["import"])

DEFAULT_FACULTY = "سایر"
UNKNOWN_PROFESSOR = "نامشخص"


def _find_or_create(db: Session, model, name: str, extra: dict):
    obj = (
        db.query(model)
        .filter(model.name == name, *[getattr(model, k) == v for k, v in extra.items()])
        .first()
    )
    if obj:
        return obj
    obj = model(name=name, status=Status.approved, **extra)
    db.add(obj)
    db.flush()
    return obj


def _store_file(data: bytes, file_name: str) -> tuple[str, str]:
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(400, "حجم فایل بیش از ۵۰ مگابایت است")
    content_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    key = f"notes/{uuid4().hex}/{file_name}"
    put_bytes(key, data, content_type)
    return key, content_type


def _create_note(db, seller: User, *, university, course_name, professor_name,
                 title, description, price_toman, kind, term, tags,
                 file_key, file_name, file_size, content_type) -> Note:
    uni = _find_or_create(db, University, university.strip(), {})
    fac = _find_or_create(db, Faculty, DEFAULT_FACULTY, {"university_id": uni.id})
    crs = _find_or_create(db, Course, course_name.strip(), {"faculty_id": fac.id})
    prof = _find_or_create(db, Professor, professor_name.strip(), {"university_id": uni.id})
    note = Note(
        seller_id=seller.id,
        course_id=crs.id,
        professor_id=prof.id,
        title=title.strip(),
        description=description.strip(),
        price_toman=price_toman,
        kind=kind,
        term=term,
        tags=tags,
        file_key=file_key,
        file_name=file_name,
        file_size=file_size,
        content_type=content_type,
        status=Status.approved,  # ایمپورت ادمین مستقیم منتشر می‌شه
    )
    db.add(note)
    db.flush()
    enqueue_preview(note.id)
    return note


@router.post("/notes", status_code=201)
def import_note(
    university: str = Form(...),
    course: str = Form(...),
    professor: str = Form(...),
    title: str = Form(...),
    term: str = Form(""),
    kind: str = Form(""),
    tags: str = Form(""),  # با کاما (یا «،») جدا کن
    description: str = Form(""),
    price_toman: int = Form(0),
    telegram_file_id: str = Form(""),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if file is not None and file.filename:
        data = file.file.read()
        file_name = file.filename
    elif telegram_file_id:
        try:
            data, path = download_telegram_file(telegram_file_id)
            file_name = path.rsplit("/", 1)[-1] or "file"
        except Exception:
            raise HTTPException(502, "دانلود فایل از تلگرام ناموفق بود")
    else:
        raise HTTPException(400, "یا فایل رو آپلود کن یا telegram_file_id بده")

    key, content_type = _store_file(data, file_name)
    tag_list = [t.strip() for t in tags.replace("،", ",").split(",") if t.strip()][:10]
    note = _create_note(
        db, admin,
        university=university, course_name=course, professor_name=professor,
        title=title, description=description, price_toman=price_toman,
        kind=doc_type(kind), term=term.strip() or None, tags=tag_list,
        file_key=key, file_name=file_name, file_size=len(data), content_type=content_type,
    )
    db.commit()
    return {"id": note.id, "status": note.status.value}


# ── ایمپورت دسته‌ای با خروجی کراولر ─────────────────────────────


class CrawlItem(BaseModel):
    university: str
    course_name: str
    professor: str | None = None
    term: str | None = None            # «4041» یا «1403»
    doc_type: str | None = None        # «جزوه»، «نمونه سوال پایانترم»، ...
    tags: list[str] = Field(default_factory=list, max_length=10)
    title: str | None = None           # اگه نباشه خودکار ساخته می‌شه
    description: str = ""
    price_toman: int = 0
    media_type: str = "pdf"            # pdf | photo | document | text
    telegram_file_id: str | None = None
    file_name: str = "file"
    body: str | None = None            # پست متنی — به فایل txt تبدیل می‌شه
    confidence: float | None = None


class CrawlBatch(BaseModel):
    items: list[CrawlItem] = Field(max_length=100)


def _import_crawl_item(db: Session, admin: User, item: CrawlItem) -> int:
    kind = doc_type(item.doc_type)
    title = item.title or " ".join(
        part for part in [
            kind or "جزوه",
            item.course_name,
            f"— {item.professor}" if item.professor else None,
            f"({term_display(item.term)})" if term_display(item.term) else None,
        ] if part
    )

    # فایل: دانلود از تلگرام، یا ساخت txt از پست متنی
    if item.telegram_file_id:
        try:
            data, path = download_telegram_file(item.telegram_file_id)
            file_name = path.rsplit("/", 1)[-1] or item.file_name
        except Exception:
            raise HTTPException(502, "دانلود فایل ناموفق — file_id باید متعلق به بات نوت‌بازار باشه")
    elif item.media_type == "text" and item.body:
        data = item.body.encode("utf-8")
        file_name = f"{title[:60]}.txt"
    else:
        raise HTTPException(400, "نه file_id هست نه body — چیزی برای ذخیره نیست")

    key, content_type = _store_file(data, file_name)
    note = _create_note(
        db, admin,
        university=item.university,
        course_name=item.course_name,
        professor_name=item.professor or UNKNOWN_PROFESSOR,
        title=title[:300],
        description=item.description,
        price_toman=item.price_toman,
        kind=kind,
        term=item.term,
        tags=[t.strip() for t in item.tags if t.strip()][:10],
        file_key=key,
        file_name=file_name,
        file_size=len(data),
        content_type=content_type,
    )
    return note.id


@router.post("/crawl", status_code=201)
def import_crawl(
    batch: CrawlBatch,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    results = []
    imported = 0
    for i, item in enumerate(batch.items):
        try:
            note_id = _import_crawl_item(db, admin, item)
            db.commit()
            results.append({"index": i, "ok": True, "note_id": note_id})
            imported += 1
        except HTTPException as e:
            db.rollback()
            results.append({"index": i, "ok": False, "error": str(e.detail)})
        except Exception:
            db.rollback()
            results.append({"index": i, "ok": False, "error": "internal error"})
    return {"imported": imported, "failed": len(batch.items) - imported, "results": results}
