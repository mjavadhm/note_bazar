"""احراز مستقل از تلگرام — ایمیل/رمز + توکن Bearer.

بات تلگرام همچنان با مسیر /auth/telegram/register و هدرهای خودش کار می‌کنه؛
این راوتر برای اکانت‌های مستقل سایته (و آینده: موبایل/گوگل...).
"""

import hashlib
import re
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import User
from ..services import wallet_balance
from ..tokens import make_user_token

router = APIRouter(prefix="/auth", tags=["auth"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PBKDF2_ROUNDS = 120_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ROUNDS)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ROUNDS)
        return secrets.compare_digest(calc.hex(), digest)
    except Exception:
        return False


class RegisterEmailIn(BaseModel):
    email: str
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=2, max_length=128)


class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/register", status_code=201)
def register_email(body: RegisterEmailIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "ایمیل نامعتبره")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, "این ایمیل قبلاً ثبت شده — وارد شو")
    user = User(
        email=email,
        password_hash=hash_password(body.password),
        first_name=body.name.strip(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"token": make_user_token(user.id), "name": user.first_name}


@router.post("/login")
def login_email(body: LoginIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "ایمیل یا رمز اشتباهه")
    return {"token": make_user_token(user.id), "name": user.first_name}


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {
        "id": user.id,
        "name": user.first_name,
        "email": user.email,
        "telegram_linked": user.telegram_id is not None,
        "is_admin": user.is_admin,
        "balance": wallet_balance(db, user.id),
    }
