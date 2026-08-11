from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ..api import ApiError, api
from ..helpers import card_text
from ..keyboards import MAIN_KB, note_card_kb

router = Router()

WELCOME = (
    "سلام {name}! 👋 به «جزوه‌بازار» خوش اومدی 🎓\n\n"
    "اینجا می‌تونی جزوه‌های دانشگاهت رو پیدا کنی و بخری، "
    "یا جزوه‌هات رو بذاری و از فروششون درآمد داشته باشی.\n\n"
    "🔍 <b>جستجو:</b> بر اساس عنوان درس یا اسم استاد\n"
    "🏛️ <b>مرور:</b> دانشگاه ← دانشکده ← درس ← استاد\n"
    "➕ <b>فروش جزوه:</b> فایل بفرست، قیمت بذار، بعد از تأیید ادمین منتشر می‌شه"
)


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, command: CommandObject):
    await state.clear()
    try:
        await api.register(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
        )
    except ApiError:
        await message.answer("خطایی رخ داد 😕 چند ثانیه دیگه دوباره /start بزن.")
        return

    # دیپ‌لینک از سایت: t.me/bot?start=note_5
    if command.args and command.args.startswith("note_"):
        try:
            note_id = int(command.args.split("_", 1)[1])
            card = await api.get(f"/notes/{note_id}", message.from_user.id)
        except (ValueError, ApiError):
            await message.answer("جزوه پیدا نشد یا هنوز منتشر نشده 😕", reply_markup=MAIN_KB)
            return
        await message.answer(
            card_text(card),
            reply_markup=note_card_kb(card["id"], card["has_preview"]),
        )
        return

    name = message.from_user.first_name or "رفیق"
    await message.answer(WELCOME.format(name=name), reply_markup=MAIN_KB)


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("لغو شد ✅", reply_markup=MAIN_KB)
