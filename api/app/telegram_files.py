"""ارتباط با Bot API تلگرام: دانلود فایل و ارسال نوتیفیکیشن."""

import httpx

from .config import settings


def download_telegram_file(file_id: str) -> tuple[bytes, str]:
    base = settings.telegram_file_api
    with httpx.Client(timeout=120) as client:
        r = client.get(f"{base}/bot{settings.bot_token}/getFile", params={"file_id": file_id})
        r.raise_for_status()
        file_path = r.json()["result"]["file_path"]
        r2 = client.get(f"{base}/file/bot{settings.bot_token}/{file_path}")
        r2.raise_for_status()
        return r2.content, file_path


def send_telegram_message(chat_id: int, text: str) -> None:
    if not settings.bot_token:
        return
    try:
        with httpx.Client(timeout=15) as client:
            client.post(
                f"{settings.telegram_file_api}/bot{settings.bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
            )
    except Exception:
        pass  # نوتیف بهترین‌تلاشه؛ خرابی‌ش نباید فلو رو بشکنه
