from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ..api import ApiError, api
from ..helpers import card_text
from ..keyboards import note_card_kb
from ..states import SearchSG

router = Router()


@router.message(F.text == "🔍 جستجو")
async def search_start(message: Message, state: FSMContext):
    await state.set_state(SearchSG.query)
    await message.answer("🔍 کلیدواژه رو بفرست — مثلاً عنوان درس یا اسم استاد:")


@router.message(SearchSG.query)
async def search_do(message: Message, state: FSMContext):
    await state.clear()
    try:
        data = await api.get("/notes", message.from_user.id, params={"q": message.text.strip()})
    except ApiError:
        await message.answer("خطایی پیش اومد، دوباره تلاش کن.")
        return
    items = data["items"]
    if not items:
        await message.answer("چیزی پیدا نشد 😕 عنوان درس یا اسم استاد رو دقیق‌تر بزن.")
        return
    await message.answer(f"🔎 {len(items)} نتیجه:")
    for card in items:
        await message.answer(card_text(card), reply_markup=note_card_kb(card["id"], card["has_preview"]))
