"""ایمپورت جزوه از کانال‌های کراول‌شده — فقط ادمین.

فایل یا مستقیم آپلود می‌شه (multipart) یا با telegram_file_id از تلگرام دانلود می‌شه.
درخت دانشگاه ← دانشکده ← درس ← استاد خودکار find-or-create و تأییدشده ساخته می‌شه
(دانشکده چون توی داده کراول نیست، پیش‌فرض «سایر» ساخته می‌شه).

مثال:
  curl -X POST http://localhost:8000/import/notes \
    -H "X-Bot-Secret: $API_SECRET" -H "X-Telegram-Id: $ADMIN_TG_ID" \
    -F "university=دانشگاه صنعتی شریف" -F "course=ریاضی ۱" -F "professor=دکتر احمدی" \
    -F "title=ریاضی ۱ — نمونه سوال" -F "term=بهار ۱۴۰۴" \
    -F "tags=نمونه سوال, جمع‌بندی" -F "price_toman=30000" -F "file=@notes.pdf"
"""

import mimetypes
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_admin
from ..jobs import enqueue_preview
from ..models import Course, Faculty, Note, Professor, Status, University, User
from ..storage import put_bytes
from ..telegram_files import download_telegram_file
from .notes import MAX_FILE_SIZE

router = APIRouter(prefix="/import", tags=["import"])

DEFAULT_FACULTY = "سایر"


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


@router.post("/notes", status_code=201)
def import_note(
    university: str = Form(...),
    course: str = Form(...),
    professor: str = Form(...),
    title: str = Form(...),
    term: str = Form(""),
    tags: str = Form(""),  # با کاما (یا «،») جدا کن
    description: str = Form(""),
    price_toman: int = Form(0),
    telegram_file_id: str = Form(""),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    # درخت دسته‌بندی
    uni = _find_or_create(db, University, university.strip(), {})
    fac = _find_or_create(db, Faculty, DEFAULT_FACULTY, {"university_id": uni.id})
    crs = _find_or_create(db, Course, course.strip(), {"faculty_id": fac.id})
    prof = _find_or_create(db, Professor, professor.strip(), {"university_id": uni.id})

    # فایل: آپلود مستقیم یا دانلود از تلگرام
    file_name = "file"
    if file is not None and file.filename:
        data = file.file.read()
        file_name = file.filename
    elif telegram_file_id:
        try:
            data, path = download_telegram_file(telegram_file_id)
            file_name = path.rsplit("/", 1)[-1] or file_name
        except Exception:
            raise HTTPException(502, "دانلود فایل از تلگرام ناموفق بود")
    else:
        raise HTTPException(400, "یا فایل رو آپلود کن یا telegram_file_id بده")
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(400, "حجم فایل بیش از ۵۰ مگابایت است")

    content_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    key = f"notes/{uuid4().hex}/{file_name}"
    put_bytes(key, data, content_type)

    tag_list = [t.strip() for t in tags.replace("،", ",").split(",") if t.strip()][:10]
    note = Note(
        seller_id=admin.id,
        course_id=crs.id,
        professor_id=prof.id,
        title=title.strip(),
        description=description.strip(),
        price_toman=price_toman,
        term=term.strip() or None,
        tags=tag_list,
        file_key=key,
        file_name=file_name,
        file_size=len(data),
        content_type=content_type,
        status=Status.approved,  # ایمپورت ادمین مستقیم منتشر می‌شه
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    enqueue_preview(note.id)
    return {
        "id": note.id,
        "status": note.status.value,
        "university_id": uni.id,
        "course_id": crs.id,
        "professor_id": prof.id,
    }
