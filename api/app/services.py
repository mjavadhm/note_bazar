from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import LedgerEntry, Note, Review


def wallet_balance(db: Session, user_id: int) -> int:
    total = (
        db.query(func.coalesce(func.sum(LedgerEntry.amount_toman), 0))
        .filter(LedgerEntry.user_id == user_id)
        .scalar()
    )
    return int(total or 0)


def note_card(db: Session, note: Note) -> dict:
    avg, cnt = (
        db.query(func.avg(Review.rating), func.count(Review.id))
        .filter(Review.note_id == note.id)
        .first()
    )
    return {
        "id": note.id,
        "title": note.title,
        "description": note.description,
        "price_toman": note.price_toman,
        "term": note.term,
        "tags": note.tags or [],
        "page_count": note.page_count,
        "file_name": note.file_name,
        "file_size": note.file_size,
        "status": note.status.value,
        "has_preview": bool(note.preview_keys),
        "rating_avg": round(float(avg), 1) if avg else None,
        "rating_count": int(cnt or 0),
        "university": note.course.faculty.university.name,
        "faculty": note.course.faculty.name,
        "course": note.course.name,
        "professor": note.professor.name,
        "seller_name": note.seller.first_name or note.seller.username or "ناشناس",
        "created_at": note.created_at.isoformat() if note.created_at else None,
    }
