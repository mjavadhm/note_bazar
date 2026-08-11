from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_admin
from ..models import (Course, Faculty, LedgerEntry, Note, Professor, Purchase,
                      Status, University, User)
from ..schemas import RejectIn
from ..services import note_card
from ..telegram_files import send_telegram_message

router = APIRouter(prefix="/admin", tags=["admin"])

TAXONOMY_MODELS = {
    "university": University,
    "faculty": Faculty,
    "course": Course,
    "professor": Professor,
}


def _creator_name(db: Session, obj) -> str | None:
    if not obj.created_by_id:
        return None
    creator = db.get(User, obj.created_by_id)
    if not creator:
        return None
    return creator.first_name or creator.username


def _notify_creator(db: Session, obj, text: str) -> None:
    if obj.created_by_id:
        creator = db.get(User, obj.created_by_id)
        if creator:
            send_telegram_message(creator.telegram_id, text)


@router.get("/pending-notes")
def pending_notes(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    rows = (
        db.query(Note)
        .filter(Note.status == Status.pending)
        .order_by(Note.created_at)
        .limit(10)
        .all()
    )
    return {"items": [note_card(db, n) for n in rows]}


@router.post("/notes/{note_id}/approve")
def approve_note(note_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(404, "جزوه پیدا نشد")
    note.status = Status.approved
    db.commit()
    send_telegram_message(note.seller.telegram_id, f"✅ جزوه «{note.title}» تأیید شد و منتشر شد!")
    return {"ok": True}


@router.post("/notes/{note_id}/reject")
def reject_note(
    note_id: int,
    body: RejectIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(404, "جزوه پیدا نشد")
    note.status = Status.rejected
    note.reject_reason = body.reason
    db.commit()
    reason = f"\nدلیل: {body.reason}" if body.reason else ""
    send_telegram_message(note.seller.telegram_id, f"❌ جزوه «{note.title}» رد شد.{reason}")
    return {"ok": True}


@router.get("/pending-taxonomy")
def pending_taxonomy(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    unis = db.query(University).filter(University.status == Status.pending).limit(20).all()
    facs = db.query(Faculty).filter(Faculty.status == Status.pending).limit(20).all()
    courses = db.query(Course).filter(Course.status == Status.pending).limit(20).all()
    profs = db.query(Professor).filter(Professor.status == Status.pending).limit(20).all()
    return {
        "universities": [
            {"id": u.id, "name": u.name, "context": "", "creator": _creator_name(db, u)}
            for u in unis
        ],
        "faculties": [
            {"id": f.id, "name": f.name, "context": f.university.name, "creator": _creator_name(db, f)}
            for f in facs
        ],
        "courses": [
            {
                "id": c.id,
                "name": c.name,
                "context": f"{c.faculty.university.name} ← {c.faculty.name}",
                "creator": _creator_name(db, c),
            }
            for c in courses
        ],
        "professors": [
            {"id": p.id, "name": p.name, "context": p.university.name, "creator": _creator_name(db, p)}
            for p in profs
        ],
    }


@router.post("/taxonomy/{kind}/{item_id}/{action}")
def moderate_taxonomy(
    kind: str,
    item_id: int,
    action: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    model = TAXONOMY_MODELS.get(kind)
    if model is None:
        raise HTTPException(404, "نوع نامعتبر")
    if action not in ("approve", "reject"):
        raise HTTPException(400, "عمل نامعتبر")
    obj = db.get(model, item_id)
    if obj is None:
        raise HTTPException(404, "مورد پیدا نشد")
    obj.status = Status.approved if action == "approve" else Status.rejected
    db.commit()
    label = "تأیید" if action == "approve" else "رد"
    _notify_creator(db, obj, f"{label} شد: «{obj.name}»")
    return {"ok": True}


@router.get("/stats")
def stats(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return {
        "users": db.query(func.count(User.id)).scalar() or 0,
        "notes_pending": db.query(func.count(Note.id)).filter(Note.status == Status.pending).scalar() or 0,
        "notes_approved": db.query(func.count(Note.id)).filter(Note.status == Status.approved).scalar() or 0,
        "purchases": db.query(func.count(Purchase.id)).scalar() or 0,
        "gmv_toman": int(db.query(func.coalesce(func.sum(Purchase.price_toman), 0)).scalar() or 0),
        "commission_toman": int(db.query(func.coalesce(func.sum(Purchase.commission_toman), 0)).scalar() or 0),
    }
