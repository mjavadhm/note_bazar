"""امنیت مینی‌اپ: اعتبارسنجی initData تلگرام + توکن کوتاه‌مدت داخلی.

جریان: کلاینت initData امضاشده توسط تلگرام رو می‌فرسته → ما با HMAC بر اساس
توکن بات اعتبارسنجی می‌کنیم → یه توکن داخلی (امضاشده با API_SECRET) صادر می‌شه
که بقیه درخواست‌ها (مثل گرفتن صفحه‌های واترمارک‌دار) باهاش انجام می‌شن.
"""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import HTTPException

from .config import settings

TOKEN_TTL = 7 * 24 * 3600  # یک هفته


def validate_init_data(init_data: str, max_age: int = 86400) -> dict:
    """اعتبارسنجی امضای initData طبق مستندات تلگرام. خروجی: dict کاربر."""
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise HTTPException(401, "missing hash")

    data_check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        raise HTTPException(401, "invalid init data")

    auth_date = int(pairs.get("auth_date", "0") or 0)
    if time.time() - auth_date > max_age:
        raise HTTPException(401, "init data expired")

    try:
        user = json.loads(pairs.get("user", "{}"))
    except json.JSONDecodeError:
        raise HTTPException(401, "bad user payload")
    if "id" not in user:
        raise HTTPException(401, "no user id")
    return user


def make_token(tg_id: int) -> str:
    payload = f"{tg_id}:{int(time.time()) + TOKEN_TTL}"
    sig = hmac.new(settings.api_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{payload}:{sig}"


def verify_token(token: str) -> int:
    try:
        tg_id, exp, sig = token.split(":")
    except ValueError:
        raise HTTPException(401, "bad token")
    payload = f"{tg_id}:{exp}"
    expected = hmac.new(settings.api_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(expected, sig) or int(exp) < time.time():
        raise HTTPException(401, "invalid token")
    return int(tg_id)
