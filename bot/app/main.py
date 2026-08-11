import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from .api import api
from .config import settings
from .handlers import admin, browse, buy, search, sell, start, wallet


async def main() -> None:
    # صبر تا API بالا بیاد
    for _ in range(30):
        if await api.healthz():
            break
        await asyncio.sleep(2)

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=RedisStorage.from_url(settings.redis_url))
    dp.include_routers(
        start.router,
        browse.router,
        search.router,
        buy.router,
        sell.router,
        wallet.router,
        admin.router,
    )
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
