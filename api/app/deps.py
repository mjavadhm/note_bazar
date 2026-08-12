from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User
from .tokens import verify_user_token


def is_admin(user: User) -> bool:
    return user.is_admin or (user.telegram_id is not None and user.telegram_id in settings.admin_ids)


def current_user(
    authorization: str | None = Header(None),
    x_bot_secret: str | None = Header(None),
    x_telegram_id: int | None = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """احراز دومسیره:

    ۱) Bearer token — اکانت مستقل (ایمیلی) از سایت
    ۲) X-Bot-Secret + X-Telegram-Id — بات تلگرام به نیابت از کاربر
    """
    if authorization and authorization.lower().startswith("bearer "):
        user_id = verify_user_token(authorization[7:].strip())
        user = db.get(User, user_id)
        if user:
            return user
        raise HTTPException(401, "invalid token user")

    if x_bot_secret and x_telegram_id is not None:
        if x_bot_secret != settings.api_secret:
            raise HTTPException(401, "invalid bot secret")
        user = db.query(User).filter(User.telegram_id == x_telegram_id).first()
        if user:
            return user
        raise HTTPException(401, "user not registered")

    raise HTTPException(401, "authentication required")


def require_admin(user: User = Depends(current_user)) -> User:
    if not is_admin(user):
        raise HTTPException(403, "admin only")
    return user
