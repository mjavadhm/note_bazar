from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, is_admin
from ..models import Course, Faculty, Professor, Status, University, User
from ..schemas import CourseIn, FacultyIn, NameIn, ProfessorIn

router = APIRouter(prefix="/taxonomy", tags=["taxonomy"])


def _visible(model, query, user: User, include_own_pending: bool):
    """موارد تأییدشده + (اختیاری) پیشنهادهای در انتظارِ خود کاربر."""
    if include_own_pending:
        query = query.filter(
            or_(
                model.status == Status.approved,
                and_(model.status == Status.pending, model.created_by_id == user.id),
            )
        )
    else:
        query = query.filter(model.status == Status.approved)
    return query.order_by(model.name).all()


def _out(item) -> dict:
    return {"id": item.id, "name": item.name, "status": item.status.value}


@router.get("/universities")
def list_universities(
    include_own_pending: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    items = _visible(University, db.query(University), user, include_own_pending)
    return [_out(i) for i in items]


@router.get("/faculties")
def list_faculties(
    university_id: int,
    include_own_pending: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    q = db.query(Faculty).filter(Faculty.university_id == university_id)
    return [{**_out(i), "university_id": i.university_id} for i in _visible(Faculty, q, user, include_own_pending)]


@router.get("/courses")
def list_courses(
    faculty_id: int,
    include_own_pending: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    q = db.query(Course).filter(Course.faculty_id == faculty_id)
    return [
        {**_out(i), "faculty_id": i.faculty_id, "university_id": i.faculty.university_id}
        for i in _visible(Course, q, user, include_own_pending)
    ]


@router.get("/professors")
def list_professors(
    university_id: int,
    include_own_pending: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    q = db.query(Professor).filter(Professor.university_id == university_id)
    return [{**_out(i), "university_id": i.university_id} for i in _visible(Professor, q, user, include_own_pending)]


def _create(model, name: str, extra: dict, db: Session, user: User) -> dict:
    existing = db.query(model).filter(model.name == name, *[
        getattr(model, k) == v for k, v in extra.items()
    ]).first()
    if existing:
        return _out(existing)
    status = Status.approved if is_admin(user) else Status.pending
    obj = model(name=name, status=status, created_by_id=user.id, **extra)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _out(obj)


@router.post("/universities", status_code=201)
def create_university(body: NameIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return _create(University, body.name.strip(), {}, db, user)


@router.post("/faculties", status_code=201)
def create_faculty(body: FacultyIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not db.get(University, body.university_id):
        raise HTTPException(404, "دانشگاه پیدا نشد")
    return _create(Faculty, body.name.strip(), {"university_id": body.university_id}, db, user)


@router.post("/courses", status_code=201)
def create_course(body: CourseIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not db.get(Faculty, body.faculty_id):
        raise HTTPException(404, "دانشکده پیدا نشد")
    return _create(Course, body.name.strip(), {"faculty_id": body.faculty_id}, db, user)


@router.post("/professors", status_code=201)
def create_professor(body: ProfessorIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not db.get(University, body.university_id):
        raise HTTPException(404, "دانشگاه پیدا نشد")
    return _create(Professor, body.name.strip(), {"university_id": body.university_id}, db, user)
