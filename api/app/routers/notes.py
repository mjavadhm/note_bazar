import mimetypes
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Text, cast, or_
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, is_admin
from ..jobs import enqueue_preview
from ..models import Course, Faculty, Note, Professor, Purchase, Review, Status, User
from ..normalize import doc_type
from ..schemas import NoteCreateIn, ReviewIn
from ..services import note_card
from ..storage import presigned_get, put_bytes
from ..telegram_files import download_telegram_file

MAX_FILE_SIZE = 50 * 1024 * 1024  # محدودیت دانلود Bot API تلگرام

router = APIRouter(prefix="/notes", tags=["notes"])


def clean_tags(tags: list[str]) -> list[str]:
    return [t.strip() for t in tags if t and t.strip()][:10]


@router.post("", status_code=201)
def create_note(
    body: NoteCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if not db.get(Course, body.course_id):
        raise HTTPException(404, "درس پیدا نشد")
    if not db.get(Professor, body.professor_id):
        raise HTTPException(404, "استاد پیدا نشد")
    try:
        data, _ = download_telegram_file(body.telegram_file_id)
    except Exception:
        raise HTTPException(502, "دانلود فایل از تلگرام ناموفق بود")
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(400, "حجم فایل بیش از ۵۰ مگابایت است")
    content_type = mimetypes.guess_type(body.file_name)[0] or "application/octet-stream"
    key = f"notes/{uuid4().hex}/{body.file_name}"
    put_bytes(key, data, content_type)
    note = Note(
        seller_id=user.id,
        course_id=body.course_id,
        professor_id=body.professor_id,
        title=body.title.strip(),
        description=body.description.strip(),
        price_toman=body.price_toman,
        kind=doc_type(body.kind),
        term=(body.term or "").strip() or None,
        tags=clean_tags(body.tags),
        file_key=key,
        file_name=body.file_name,
        file_size=len(data),
        content_type=content_type,
        status=Status.pending,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    enqueue_preview(note.id)
    return {"id": note.id, "status": note.status.value}


@router.get("/mine")
def my_notes(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = (
        db.query(Note)
        .filter(Note.seller_id == user.id)
        .order_by(Note.created_at.desc())
        .limit(50)
        .all()
    )
    return {
        "items": [
            {
                "id": n.id,
                "title": n.title,
                "status": n.status.value,
                "price_toman": n.price_toman,
                "reject_reason": n.reject_reason,
            }
            for n in rows
        ]
    }


@router.get("")
def list_notes(
    q: str | None = None,
    university_id: int | None = None,
    faculty_id: int | None = None,
    course_id: int | None = None,
    professor_id: int | None = None,
    tag: str | None = None,
    term: str | None = None,
    kind: str | None = None,
    limit: int = Query(5, le=20),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    query = (
        db.query(Note)
        .join(Course, Note.course_id == Course.id)
        .join(Faculty, Course.faculty_id == Faculty.id)
        .filter(Note.status == Status.approved)
    )
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Note.title.ilike(like),
                Note.description.ilike(like),
                Note.kind.ilike(like),
                cast(Note.tags, Text).ilike(like),
            )
        )
    if university_id:
        query = query.filter(Faculty.university_id == university_id)
    if faculty_id:
        query = query.filter(Course.faculty_id == faculty_id)
    if course_id:
        query = query.filter(Note.course_id == course_id)
    if professor_id:
        query = query.filter(Note.professor_id == professor_id)
    if tag:
        query = query.filter(Note.tags.contains([tag]))
    if term:
        query = query.filter(Note.term == term)
    if kind:
        query = query.filter(Note.kind == kind)
    items = query.order_by(Note.created_at.desc()).limit(limit).all()
    return {"items": [note_card(db, n) for n in items]}


def _get_visible_note(note_id: int, db: Session, user: User) -> Note:
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(404, "جزوه پیدا نشد")
    if note.status != Status.approved and note.seller_id != user.id and not is_admin(user):
        raise HTTPException(404, "جزوه پیدا نشد")
    return note


@router.get("/{note_id}")
def get_note(note_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return note_card(db, _get_visible_note(note_id, db, user))


@router.get("/{note_id}/preview")
def note_preview(note_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    note = _get_visible_note(note_id, db, user)
    return {"urls": [presigned_get(k) for k in (note.preview_keys or [])]}


@router.get("/{note_id}/download")
def note_download(note_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(404, "جزوه پیدا نشد")
    purchased = (
        db.query(Purchase)
        .filter(Purchase.buyer_id == user.id, Purchase.note_id == note.id)
        .first()
    )
    if not (purchased or note.seller_id == user.id or is_admin(user)):
        raise HTTPException(403, "برای دانلود باید جزوه رو خریده باشی")
    return {"url": presigned_get(note.file_key, expires=600), "file_name": note.file_name}


@router.post("/{note_id}/reviews", status_code=201)
def add_review(
    note_id: int,
    body: ReviewIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if not db.get(Note, note_id):
        raise HTTPException(404, "جزوه پیدا نشد")
    purchase = (
        db.query(Purchase)
        .filter(Purchase.buyer_id == user.id, Purchase.note_id == note_id)
        .first()
    )
    if not purchase:
        raise HTTPException(403, "فقط بعد از خرید می‌تونی امتیاز بدی")
    if db.query(Review).filter(Review.purchase_id == purchase.id).first():
        raise HTTPException(400, "برای این خرید قبلاً امتیاز ثبت کردی")
    db.add(
        Review(
            note_id=note_id,
            buyer_id=user.id,
            purchase_id=purchase.id,
            rating=body.rating,
            comment=body.comment.strip(),
        )
    )
    db.commit()
    return {"ok": True}


@router.get("/{note_id}/reviews")
def list_reviews(note_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = (
        db.query(Review)
        .filter(Review.note_id == note_id)
        .order_by(Review.created_at.desc())
        .limit(10)
        .all()
    )
    return {
        "items": [
            {
                "rating": r.rating,
                "comment": r.comment,
                "buyer": r.buyer.first_name or "کاربر",
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }
