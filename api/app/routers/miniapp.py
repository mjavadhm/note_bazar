"""اندپوینت‌های مینی‌اپ تلگرام — خواننده آنلاین با واترمارک شخصی.

فایل اصلی جزوه هیچ‌وقت به کلاینت داده نمی‌شه؛ فقط صفحه‌های رندرشده با
واترمارک مخصوص همون خریدار. خروجی رندرشده توی MinIO کش می‌شه.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..miniapp_security import make_token, validate_init_data, verify_token
from ..models import Note, Purchase, Status, User
from ..personal_render import render_page
from ..services import note_card
from ..storage import get_bytes, put_bytes

router = APIRouter(prefix="/miniapp", tags=["miniapp"])


class InitIn(BaseModel):
    init_data: str


@router.post("/auth")
def miniapp_auth(body: InitIn, db: Session = Depends(get_db)):
    tg_user = validate_init_data(body.init_data)
    tg_id = int(tg_user["id"])
    user = db.query(User).filter(User.telegram_id == tg_id).first()
    if user is None:
        raise HTTPException(403, "ابتدا داخل بات /start رو بزن")
    return {"token": make_token(tg_id), "name": user.first_name or user.username or ""}


def _current_user(token: str = Query(...), db: Session = Depends(get_db)) -> User:
    tg_id = verify_token(token)
    user = db.query(User).filter(User.telegram_id == tg_id).first()
    if user is None:
        raise HTTPException(401, "user not found")
    return user


@router.get("/purchases")
def miniapp_purchases(user: User = Depends(_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Purchase)
        .filter(Purchase.buyer_id == user.id)
        .order_by(Purchase.created_at.desc())
        .limit(100)
        .all()
    )
    return {"items": [note_card(db, p.note) for p in rows]}


def _check_access(note_id: int, user: User, db: Session) -> Note:
    note = db.get(Note, note_id)
    if note is None or note.status != Status.approved:
        raise HTTPException(404, "not found")
    if note.seller_id == user.id:
        return note
    purchased = (
        db.query(Purchase)
        .filter(Purchase.buyer_id == user.id, Purchase.note_id == note.id)
        .first()
    )
    if not purchased:
        raise HTTPException(403, "access denied")
    return note


def _page_count(note: Note, db: Session) -> int:
    if note.page_count:
        return note.page_count
    if not note.file_name.lower().endswith(".pdf"):
        raise HTTPException(415, "خواندن آنلاین فعلاً فقط برای PDF پشتیبانی می‌شه")
    import fitz

    raw = get_bytes(note.file_key)
    doc = fitz.open(stream=raw, filetype="pdf")
    count = doc.page_count
    doc.close()
    note.page_count = count
    db.commit()
    return count


@router.get("/notes/{note_id}/pages")
def miniapp_pages(note_id: int, user: User = Depends(_current_user), db: Session = Depends(get_db)):
    note = _check_access(note_id, user, db)
    return {"page_count": _page_count(note, db), "title": note.title}


@router.get("/notes/{note_id}/pages/{page}")
def miniapp_page_image(
    note_id: int,
    page: int,
    user: User = Depends(_current_user),
    db: Session = Depends(get_db),
):
    note = _check_access(note_id, user, db)
    total = _page_count(note, db)
    if not (1 <= page <= total):
        raise HTTPException(404, "page out of range")

    cache_key = f"personal/{note.id}/{user.telegram_id}/page-{page}.jpg"
    try:
        data = get_bytes(cache_key)
    except Exception:
        watermark = f"@{user.username}" if user.username else f"id:{user.telegram_id}"
        raw = get_bytes(note.file_key)
        try:
            data = render_page(raw, note.file_name, page - 1, watermark)
        except ValueError:
            raise HTTPException(415, "خواندن آنلاین فعلاً فقط برای PDF پشتیبانی می‌شه")
        put_bytes(cache_key, data, "image/jpeg")
    return Response(content=data, media_type="image/jpeg")
