from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None


class NameIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class FacultyIn(NameIn):
    university_id: int


class CourseIn(NameIn):
    faculty_id: int


class ProfessorIn(NameIn):
    university_id: int


class NoteCreateIn(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    description: str = ""
    price_toman: int = Field(ge=0)
    course_id: int
    professor_id: int
    telegram_file_id: str
    file_name: str = "file"
    kind: str | None = Field(default=None, max_length=40)  # نوع مدرک
    term: str | None = Field(default=None, max_length=32)  # ترم خام — مثل «4041»
    tags: list[str] = Field(default_factory=list, max_length=10)


class PurchaseIn(BaseModel):
    note_id: int


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = ""


class CreditIn(BaseModel):
    amount: int = Field(gt=0)


class RejectIn(BaseModel):
    reason: str = ""
