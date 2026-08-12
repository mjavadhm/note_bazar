"""کلاینت HTTP برای ارتباط با بک‌اند — بات هیچ منطق دیتابیسی نداره."""

import httpx

from .config import settings


class ApiError(Exception):
    def __init__(self, status_code: int, detail):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API {status_code}: {detail}")


class Api:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=settings.api_base_url, timeout=60)

    def _headers(self, tg_id: int) -> dict[str, str]:
        return {"X-Bot-Secret": settings.api_secret, "X-Telegram-Id": str(tg_id)}

    @staticmethod
    async def _check(resp: httpx.Response):
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise ApiError(resp.status_code, detail)
        return resp.json()

    async def get(self, path: str, tg_id: int, params: dict | None = None):
        resp = await self._client.get(path, headers=self._headers(tg_id), params=params)
        return await self._check(resp)

    async def post(self, path: str, tg_id: int, json: dict | None = None):
        resp = await self._client.post(path, headers=self._headers(tg_id), json=json)
        return await self._check(resp)

    async def register(self, tg_id: int, username: str | None, first_name: str | None):
        resp = await self._client.post(
            "/auth/telegram/register",
            json={"telegram_id": tg_id, "username": username, "first_name": first_name},
            headers={"X-Bot-Secret": settings.api_secret},
        )
        return await self._check(resp)

    async def healthz(self) -> bool:
        try:
            resp = await self._client.get("/healthz")
            return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    async def fetch_bytes(url: str) -> bytes:
        """دانلود فایل از MinIO — بات فایل رو relay می‌کنه چون URL داخلیه."""
        async with httpx.AsyncClient(timeout=180, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content


api = Api()
