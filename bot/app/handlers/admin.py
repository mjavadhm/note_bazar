from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from ..api import ApiError, api
from ..config import settings
from ..helpers import card_text
from ..keyboards import ADMIN_PANEL_KB, admin_note_kb, admin_tax_kb

router = Router()

TAX_LABEL = {
    "universities": ("🏛️ دانشگاه", "university"),
    "faculties": ("🏢 دانشکده", "faculty"),
    "courses": ("📘 درس", "course"),
    "professors": ("👨‍🏫 استاد", "professor"),
}


def _is_admin(tg_id: int) -> bool:
    return tg_id in settings.admin_ids


@router.message(Command("panel"))
async def panel(message: Message):
    if not _is_admin(message.from_user.id):
        return
    await message.answer("👑 پنل مدیریت:", reply_markup=ADMIN_PANEL_KB)


@router.callback_query(F.data == "adm:notes")
async def pending_notes(cb: CallbackQuery):
    if not _is_admin(cb.from_user.id):
        await cb.answer("فقط ادمین", show_alert=True)
        return
    data = await api.get("/admin/pending-notes", cb.from_user.id)
    await cb.answer()
    if not data["items"]:
        await cb.message.answer("صف تأیید خالیه 🎉")
        return
    for card in data["items"]:
        await cb.message.answer(card_text(card), reply_markup=admin_note_kb(card["id"]))


@router.callback_query(F.data.startswith("an:"))
async def moderate_note(cb: CallbackQuery):
    if not _is_admin(cb.from_user.id):
        await cb.answer("فقط ادمین", show_alert=True)
        return
    _, note_id, action = cb.data.split(":")
    try:
        if action == "ok":
            await api.post(f"/admin/notes/{note_id}/approve", cb.from_user.id)
        else:
            await api.post(f"/admin/notes/{note_id}/reject", cb.from_user.id, json={"reason": ""})
    except ApiError:
        await cb.answer("عملیات ناموفق بود", show_alert=True)
        return
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.answer("تأیید شد ✅" if action == "ok" else "رد شد ❌")


@router.callback_query(F.data == "adm:tax")
async def pending_taxonomy(cb: CallbackQuery):
    if not _is_admin(cb.from_user.id):
        await cb.answer("فقط ادمین", show_alert=True)
        return
    data = await api.get("/admin/pending-taxonomy", cb.from_user.id)
    await cb.answer()
    shown = False
    for key, (label, kind) in TAX_LABEL.items():
        for item in data[key]:
            shown = True
            context = f" ← {item['context']}" if item.get("context") else ""
            creator = f"\n👤 پیشنهاددهنده: {item['creator']}" if item.get("creator") else ""
            await cb.message.answer(
                f"{label}: <b>{item['name']}</b>{context}{creator}",
                reply_markup=admin_tax_kb(kind, item["id"]),
            )
    if not shown:
        await cb.message.answer("پیشنهاد جدیدی نیست 🎉")


@router.callback_query(F.data.startswith("at:"))
async def moderate_taxonomy(cb: CallbackQuery):
    if not _is_admin(cb.from_user.id):
        await cb.answer("فقط ادمین", show_alert=True)
        return
    _, kind, item_id, action = cb.data.split(":")
    verb = "approve" if action == "ok" else "reject"
    try:
        await api.post(f"/admin/taxonomy/{kind}/{item_id}/{verb}", cb.from_user.id)
    except ApiError:
        await cb.answer("عملیات ناموفق بود", show_alert=True)
        return
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.answer("تأیید شد ✅" if action == "ok" else "رد شد ❌")


@router.callback_query(F.data == "adm:stats")
async def show_stats(cb: CallbackQuery):
    if not _is_admin(cb.from_user.id):
        await cb.answer("فقط ادمین", show_alert=True)
        return
    s = await api.get("/admin/stats", cb.from_user.id)
    await cb.answer()
    await cb.message.answer(
        "📊 آمار:\n"
        f"👥 کاربران: {s['users']}\n"
        f"📄 جزوه‌ها: {s['notes_approved']} منتشرشده / {s['notes_pending']} در انتظار\n"
        f"🛒 خریدها: {s['purchases']}\n"
        f"💰 گردش مالی: {s['gmv_toman']:,} تومان\n"
        f"🏦 کمیسیون: {s['commission_toman']:,} تومان"
    )
