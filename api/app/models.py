from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (BigInteger, Boolean, DateTime, ForeignKey, Integer,
                        String, Text, UniqueConstraint, func)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Status(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class PurchaseStatus(str, enum.Enum):
    held = "held"
    released = "released"
    refunded = "refunded"


class LedgerKind(str, enum.Enum):
    charge = "charge"          # شارژ کیف پول
    purchase = "purchase"      # کسر از خریدار
    earning = "earning"        # درآمد فروشنده
    commission = "commission"  # کمیسیون پلتفرم
    refund = "refund"          # برگشت وجه
    payout = "payout"          # تسویه با فروشنده
    adjustment = "adjustment"  # اصلاحیه ادمین


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TaxonomyMixin:
    """ستون‌های مشترک درخت دانشگاه ← دانشکده ← درس ← استاد."""

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[Status] = mapped_column(default=Status.pending, index=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class University(TaxonomyMixin, Base):
    __tablename__ = "universities"
    __table_args__ = (UniqueConstraint("name"),)


class Faculty(TaxonomyMixin, Base):
    __tablename__ = "faculties"
    __table_args__ = (UniqueConstraint("university_id", "name"),)

    university_id: Mapped[int] = mapped_column(ForeignKey("universities.id"), index=True)
    university: Mapped[University] = relationship()


class Course(TaxonomyMixin, Base):
    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("faculty_id", "name"),)

    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculties.id"), index=True)
    faculty: Mapped[Faculty] = relationship()


class Professor(TaxonomyMixin, Base):
    __tablename__ = "professors"
    __table_args__ = (UniqueConstraint("university_id", "name"),)

    university_id: Mapped[int] = mapped_column(ForeignKey("universities.id"), index=True)
    university: Mapped[University] = relationship()


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    professor_id: Mapped[int] = mapped_column(ForeignKey("professors.id"))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    price_toman: Mapped[int] = mapped_column(Integer)
    term: Mapped[str | None] = mapped_column(String(32))  # سال/ترم — مثل «بهار ۱۴۰۴»
    tags: Mapped[list] = mapped_column(JSONB, default=list)  # ["جمع‌بندی", "نمونه سوال"]
    file_key: Mapped[str] = mapped_column(String(500))
    file_name: Mapped[str] = mapped_column(String(300))
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    content_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    preview_keys: Mapped[list] = mapped_column(JSONB, default=list)
    page_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[Status] = mapped_column(default=Status.pending, index=True)
    reject_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    seller: Mapped[User] = relationship()
    course: Mapped[Course] = relationship()
    professor: Mapped[Professor] = relationship()


class Purchase(Base):
    __tablename__ = "purchases"
    __table_args__ = (UniqueConstraint("buyer_id", "note_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    note_id: Mapped[int] = mapped_column(ForeignKey("notes.id"), index=True)
    price_toman: Mapped[int] = mapped_column(Integer)
    commission_toman: Mapped[int] = mapped_column(Integer)
    # فعلاً آزادسازی فوری (released). قلاب escrow برای آینده: held + تایمر آزادسازی
    status: Mapped[PurchaseStatus] = mapped_column(default=PurchaseStatus.released)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    buyer: Mapped[User] = relationship()
    note: Mapped[Note] = relationship()


class LedgerEntry(Base):
    """دفتر کل غیرقابل‌تغییر — موجودی همیشه از روی این جدول محاسبه می‌شه."""

    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)  # None = پلتفرم
    amount_toman: Mapped[int] = mapped_column(BigInteger)  # علامت‌دار
    kind: Mapped[LedgerKind] = mapped_column(index=True)
    purchase_id: Mapped[int | None] = mapped_column(ForeignKey("purchases.id"))
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(ForeignKey("notes.id"), index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"), unique=True)
    rating: Mapped[int] = mapped_column(Integer)  # 1..5
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
