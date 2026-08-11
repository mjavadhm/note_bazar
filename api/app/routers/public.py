"""اندپوینت‌های عمومی سایت — بدون احراز، فقط محتوای تأییدشده."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Text, cast, func, or_
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (Course, Faculty, Note, Professor, Purchase, Review,
                      Status, University)
from ..services import note_card
from ..storage import presigned_get

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/notes")
def public_notes(
    q: str | None = None,
    university_id: int | None = None,
    faculty_id: int | None = None,
    course_id: int | None = None,
    professor_id: int | None = None,
    tag: str | None = None,
    term: str | None = None,
    limit: int = Query(12, le=48),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = (
        db.query(Note)
        .join(Course, Note.course_id == Course.id)
        .join(Faculty, Course.faculty_id == Faculty.id)
        .outerjoin(Professor, Note.professor_id == Professor.id)
        .filter(Note.status == Status.approved)
    )
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Note.title.ilike(like),
                Note.description.ilike(like),
                Course.name.ilike(like),
                Professor.name.ilike(like),
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

    total = query.count()
    items = query.order_by(Note.created_at.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": [note_card(db, n) for n in items]}


@router.get("/notes/{note_id}")
def public_note(note_id: int, db: Session = Depends(get_db)):
    note = db.get(Note, note_id)
    if note is None or note.status != Status.approved:
        raise HTTPException(404, "not found")
    return note_card(db, note)


@router.get("/notes/{note_id}/preview")
def public_preview(note_id: int, db: Session = Depends(get_db)):
    note = db.get(Note, note_id)
    if note is None or note.status != Status.approved:
        raise HTTPException(404, "not found")
    return {"urls": [presigned_get(k) for k in (note.preview_keys or [])]}


@router.get("/notes/{note_id}/reviews")
def public_reviews(note_id: int, db: Session = Depends(get_db)):
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


@router.get("/taxonomy/universities")
def public_universities(db: Session = Depends(get_db)):
    items = (
        db.query(University)
        .filter(University.status == Status.approved)
        .order_by(University.name)
        .all()
    )
    return [{"id": u.id, "name": u.name} for u in items]


@router.get("/taxonomy/faculties")
def public_faculties(university_id: int, db: Session = Depends(get_db)):
    items = (
        db.query(Faculty)
        .filter(Faculty.university_id == university_id, Faculty.status == Status.approved)
        .order_by(Faculty.name)
        .all()
    )
    return [{"id": f.id, "name": f.name, "university_id": f.university_id} for f in items]


@router.get("/taxonomy/courses")
def public_courses(faculty_id: int, db: Session = Depends(get_db)):
    items = (
        db.query(Course)
        .filter(Course.faculty_id == faculty_id, Course.status == Status.approved)
        .order_by(Course.name)
        .all()
    )
    return [
        {"id": c.id, "name": c.name, "faculty_id": c.faculty_id, "university_id": c.faculty.university_id}
        for c in items
    ]


@router.get("/taxonomy/professors")
def public_professors(university_id: int, db: Session = Depends(get_db)):
    items = (
        db.query(Professor)
        .filter(Professor.university_id == university_id, Professor.status == Status.approved)
        .order_by(Professor.name)
        .all()
    )
    return [{"id": p.id, "name": p.name, "university_id": p.university_id} for p in items]


@router.get("/stats")
def public_stats(db: Session = Depends(get_db)):
    return {
        "notes": db.query(func.count(Note.id)).filter(Note.status == Status.approved).scalar() or 0,
        "universities": db.query(func.count(University.id)).filter(University.status == Status.approved).scalar() or 0,
        "purchases": db.query(func.count(Purchase.id)).scalar() or 0,
    }
