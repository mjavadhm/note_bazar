from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User


def is_admin(user: User) -> bool:
    return user.is_admin or user.telegram_id in settings.admin_ids


def current_user(
    x_bot_secret: str = Header(),
    x_telegram_id: int = Header(),
    db: Session = Depends(get_db),
) -> User:
    """احراز: فقط بات (با سکرت مشترک) به API دسترسی داره و کاربر رو با هدر معرفی می‌کنه."""
    if x_bot_secret != settings.api_secret:
        raise HTTPException(401, "invalid bot secret")
    user = db.query(User).filter(User.telegram_id == x_telegram_id).first()
    if user is None:
        raise HTTPException(401, "user not registered")
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if not is_admin(user):
        raise HTTPException(403, "admin only")
    return user
