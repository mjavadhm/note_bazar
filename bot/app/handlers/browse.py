from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from ..api import ApiError, api
from ..helpers import card_text
from ..keyboards import items_kb, note_card_kb

router = Router()


@router.message(F.text == "🏛️ مرور دانشگاه‌ها")
async def browse_universities(message: Message):
    items = await api.get("/taxonomy/universities", message.from_user.id)
    if not items:
        await message.answer("هنوز دانشگاهی ثبت نشده 😕 اولین نفر باش و از فلوی فروش جزوه پیشنهادش بده!")
        return
    await message.answer("🏛️ دانشگاه رو انتخاب کن:", reply_markup=items_kb(items, "u"))


@router.callback_query(F.data.startswith("u:"))
async def browse_faculties(cb: CallbackQuery):
    university_id = int(cb.data.split(":")[1])
    items = await api.get("/taxonomy/faculties", cb.from_user.id, params={"university_id": university_id})
    if not items:
        await cb.answer("برای این دانشگاه دانشکده‌ای ثبت نشده", show_alert=True)
        return
    await cb.message.edit_text("🏢 دانشکده رو انتخاب کن:", reply_markup=items_kb(items, "f"))
    await cb.answer()


@router.callback_query(F.data.startswith("f:"))
async def browse_courses(cb: CallbackQuery):
    faculty_id = int(cb.data.split(":")[1])
    items = await api.get("/taxonomy/courses", cb.from_user.id, params={"faculty_id": faculty_id})
    if not items:
        await cb.answer("برای این دانشکده درسی ثبت نشده", show_alert=True)
        return
    rows = [
        [{"text": it["name"], "callback_data": f"c:{it['id']}:{it['university_id']}"}]
        for it in items[:15]
    ]
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=r[0]["text"], callback_data=r[0]["callback_data"])] for r in rows
        ]
    )
    await cb.message.edit_text("📘 درس رو انتخاب کن:", reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("c:"))
async def browse_professors(cb: CallbackQuery):
    _, course_id, university_id = cb.data.split(":")
    items = await api.get("/taxonomy/professors", cb.from_user.id, params={"university_id": int(university_id)})
    if not items:
        await cb.answer("استادی ثبت نشده — موقع فروش جزوه می‌تونی پیشنهادش بدی", show_alert=True)
        return
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=it["name"], callback_data=f"w:{course_id}:{it['id']}")]
            for it in items[:15]
        ]
    )
    await cb.message.edit_text("👨‍🏫 استاد رو انتخاب کن:", reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("w:"))
async def browse_notes(cb: CallbackQuery):
    _, course_id, professor_id = cb.data.split(":")
    try:
        data = await api.get(
            "/notes",
            cb.from_user.id,
            params={"course_id": int(course_id), "professor_id": int(professor_id)},
        )
    except ApiError:
        await cb.answer("خطایی پیش اومد، دوباره تلاش کن", show_alert=True)
        return
    items = data["items"]
    await cb.answer()
    if not items:
        await cb.message.answer("برای این درس/استاد هنوز جزوه‌ای نیست 😕")
        return
    await cb.message.answer(f"📚 {len(items)} جزوه پیدا شد:")
    for card in items:
        await cb.message.answer(card_text(card), reply_markup=note_card_kb(card["id"], card["has_preview"]))
