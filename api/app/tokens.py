"""توکن نشست کاربر — مستقل از تلگرام (برای اکانت‌های ایمیلی و آینده: موبایل).

توکن‌ها امضاشده با API_SECRET و بدون ذخیره‌سازی سمت سرورن (stateless).
"""

import hashlib
import hmac
import time

from fastapi import HTTPException

from .config import settings

TOKEN_TTL = 30 * 24 * 3600  # یک ماه


def make_user_token(user_id: int) -> str:
    payload = f"u{user_id}:{int(time.time()) + TOKEN_TTL}"
    sig = hmac.new(settings.api_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:40]
    return f"{payload}:{sig}"


def verify_user_token(token: str) -> int:
    try:
        uid, exp, sig = token.split(":")
        assert uid.startswith("u") and uid[1:].isdigit()
    except (ValueError, AssertionError):
        raise HTTPException(401, "bad token")
    payload = f"{uid}:{exp}"
    expected = hmac.new(settings.api_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:40]
    if not hmac.compare_digest(expected, sig) or int(exp) < time.time():
        raise HTTPException(401, "invalid token")
    return int(uid[1:])
