from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, ReplyKeyboardMarkup, WebAppInfo)

from .config import settings

MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 جستجو"), KeyboardButton(text="🏛️ مرور دانشگاه‌ها")],
        [KeyboardButton(text="📚 خریدهای من"), KeyboardButton(text="📂 جزوه‌های من")],
        [KeyboardButton(text="➕ فروش جزوه"), KeyboardButton(text="💰 کیف پول")],
    ],
    resize_keyboard=True,
)


def _viewer_url(note_id: int) -> str:
    return f"{settings.miniapp_url.rstrip('/')}/viewer.html?note={note_id}"


def items_kb(items: list[dict], prefix: str, add_new: str | None = None) -> InlineKeyboardMarkup:
    rows = []
    for it in items[:15]:
        label = it["name"] + (" ⏳" if it.get("status") == "pending" else "")
        rows.append([InlineKeyboardButton(text=label, callback_data=f"{prefix}:{it['id']}")])
    if add_new:
        rows.append([InlineKeyboardButton(text="➕ پیشنهاد مورد جدید", callback_data=add_new)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def note_card_kb(note_id: int, has_preview: bool) -> InlineKeyboardMarkup:
    rows = []
    if has_preview:
        rows.append([InlineKeyboardButton(text="👁 پیش‌نمایش", callback_data=f"pv:{note_id}")])
    rows.append([InlineKeyboardButton(text="🛒 خرید", callback_data=f"buy:{note_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def rate_kb(note_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐" * i, callback_data=f"r:{note_id}:{i}") for i in range(1, 6)]
        ]
    )


def purchase_kb(note_id: int) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="⬇️ دانلود", callback_data=f"dl:{note_id}")]]
    if settings.miniapp_url:
        rows.append([
            InlineKeyboardButton(text="📖 مطالعه آنلاین", web_app=WebAppInfo(url=_viewer_url(note_id)))
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_note_kb(note_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ تأیید", callback_data=f"an:{note_id}:ok"),
                InlineKeyboardButton(text="❌ رد", callback_data=f"an:{note_id}:no"),
            ]
        ]
    )


def admin_tax_kb(kind: str, item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ تأیید", callback_data=f"at:{kind}:{item_id}:ok"),
                InlineKeyboardButton(text="❌ رد", callback_data=f"at:{kind}:{item_id}:no"),
            ]
        ]
    )


ADMIN_PANEL_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📥 جزوه‌های در انتظار", callback_data="adm:notes")],
        [InlineKeyboardButton(text="🏛️ پیشنهادهای درخت", callback_data="adm:tax")],
        [InlineKeyboardButton(text="📊 آمار", callback_data="adm:stats")],
    ]
)

WALLET_ADMIN_KB = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="💳 شارژ تستی (ادمین)", callback_data="dc")]]
)
