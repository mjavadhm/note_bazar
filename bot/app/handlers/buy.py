from aiogram import F, Router
from aiogram.types import (BufferedInputFile, CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, InputMediaPhoto, Message, WebAppInfo)

from ..api import ApiError, api
from ..config import settings
from ..helpers import fa_money
from ..keyboards import purchase_kb

router = Router()


def viewer_url(note_id: int) -> str:
    return f"{settings.miniapp_url.rstrip('/')}/viewer.html?note={note_id}"


@router.callback_query(F.data.startswith("pv:"))
async def preview(cb: CallbackQuery):
    note_id = int(cb.data.split(":")[1])
    try:
        data = await api.get(f"/notes/{note_id}/preview", cb.from_user.id)
    except ApiError:
        await cb.answer("خطا در دریافت پیش‌نمایش", show_alert=True)
        return
    urls = data["urls"]
    if not urls:
        await cb.answer("این جزوه پیش‌نمایش نداره", show_alert=True)
        return
    await cb.answer()
    media = []
    for i, url in enumerate(urls[:5]):
        raw = await api.fetch_bytes(url)
        media.append(InputMediaPhoto(media=BufferedInputFile(raw, filename=f"page-{i + 1}.jpg")))
    await cb.message.answer_media_group(media)
    await cb.message.answer("👆 پیش‌نمایش واترمارک‌دار — فایل کامل بعد از خرید ارسال می‌شه.")


@router.callback_query(F.data.startswith("buy:"))
async def buy(cb: CallbackQuery):
    note_id = int(cb.data.split(":")[1])
    try:
        await api.post("/purchases", cb.from_user.id, json={"note_id": note_id})
    except ApiError as e:
        if e.status_code == 402 and isinstance(e.detail, dict):
            text = (
                "موجودی کیف پولت کافی نیست 😕\n"
                f"💰 قیمت: {e.detail['price']:,} تومان\n"
                f"👛 موجودی: {e.detail['balance']:,} تومان\n\n"
                "از منوی «💰 کیف پول» شارژش کن."
            )
        else:
            text = e.detail if isinstance(e.detail, str) else "خطایی پیش اومد"
        await cb.answer()
        await cb.message.answer(text)
        return
    await cb.answer("خرید موفق ✅")
    dl = await api.get(f"/notes/{note_id}/download", cb.from_user.id)
    raw = await api.fetch_bytes(dl["url"])
    await cb.message.answer_document(
        BufferedInputFile(raw, filename=dl["file_name"]),
        caption="📚 فایل کامل جزوه — نوش جونت!",
    )

    # ردیف ستاره‌ها + در صورت تنظیم MINIAPP_URL دکمه مطالعه آنلاین
    rows = []
    if settings.miniapp_url:
        rows.append([
            InlineKeyboardButton(text="📖 مطالعه آنلاین", web_app=WebAppInfo(url=viewer_url(note_id)))
        ])
    rows.append([InlineKeyboardButton(text="⭐" * i, callback_data=f"r:{note_id}:{i}") for i in range(1, 6)])
    await cb.message.answer(
        "به این جزوه چه امتیازی می‌دی؟",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("r:"))
async def rate(cb: CallbackQuery):
    _, note_id, stars = cb.data.split(":")
    try:
        await api.post(f"/notes/{note_id}/reviews", cb.from_user.id, json={"rating": int(stars)})
    except ApiError as e:
        msg = "قبلاً امتیازت رو ثبت کردی" if e.status_code == 400 else "ثبت امتیاز ممکن نشد"
        await cb.answer(msg, show_alert=True)
        return
    await cb.answer("مرسی از امتیازت 🙏")
    await cb.message.edit_reply_markup(reply_markup=None)


@router.message(F.text == "📚 خریدهای من")
async def my_purchases(message: Message):
    try:
        data = await api.get("/purchases/mine", message.from_user.id)
    except ApiError:
        await message.answer("خطایی پیش اومد، دوباره تلاش کن.")
        return
    if not data["items"]:
        await message.answer("هنوز چیزی نخریدی — از «🔍 جستجو» شروع کن!")
        return
    await message.answer("📚 خریدهای تو:")
    for p in data["items"]:
        await message.answer(
            f"📄 {p['title']}\n💰 {fa_money(p['price_toman'])}",
            reply_markup=purchase_kb(p["note_id"]),
        )


@router.callback_query(F.data.startswith("dl:"))
async def download(cb: CallbackQuery):
    note_id = int(cb.data.split(":")[1])
    try:
        dl = await api.get(f"/notes/{note_id}/download", cb.from_user.id)
    except ApiError as e:
        await cb.answer(e.detail if isinstance(e.detail, str) else "خطا", show_alert=True)
        return
    raw = await api.fetch_bytes(dl["url"])
    await cb.message.answer_document(BufferedInputFile(raw, filename=dl["file_name"]))
    await cb.answer()
