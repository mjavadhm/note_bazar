from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ..api import ApiError, api
from ..keyboards import MAIN_KB, items_kb, kind_kb
from ..states import SellSG

router = Router()

# مراحل درخت: (پارامتر والد، پیشوند کالبک، کالبک «پیشنهاد جدید»، عنوان مرحله)
LEVELS = {
    "university": (None, "su", "snew:university", "🏛️ دانشگاه:"),
    "faculty": ("university_id", "sf", "snew:faculty", "🏢 دانشکده:"),
    "course": ("faculty_id", "sc", "snew:course", "📘 درس:"),
    "professor": ("university_id", "sp", "snew:professor", "👨‍🏫 استاد:"),
}

LIST_PATHS = {
    "university": "/taxonomy/universities",
    "faculty": "/taxonomy/faculties",
    "course": "/taxonomy/courses",
    "professor": "/taxonomy/professors",
}

POST_PATHS = LIST_PATHS

KIND_FA = {"university": "دانشگاه", "faculty": "دانشکده", "course": "درس", "professor": "استاد"}

FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def parse_amount(text: str) -> int | None:
    cleaned = text.strip().translate(FA_DIGITS).replace(",", "").replace("٬", "")
    return int(cleaned) if cleaned.isdigit() else None


def parse_tags(text: str) -> list[str]:
    return [t.strip() for t in text.replace("،", ",").split(",") if t.strip()][:10]


async def show_level(message: Message, state: FSMContext, kind: str):
    parent_param, prefix, add_new, title = LEVELS[kind]
    data = await state.get_data()
    params = {"include_own_pending": "true"}
    if parent_param:
        params[parent_param] = data[parent_param]
    items = await api.get(LIST_PATHS[kind], message.from_user.id, params=params)
    await message.answer(title, reply_markup=items_kb(items, prefix, add_new=add_new))


@router.message(F.text == "➕ فروش جزوه")
async def sell_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(SellSG.file)
    await message.answer(
        "📎 فایل جزوه رو بفرست — هر فرمتی قبوله (PDF، عکس، Word، زیپ...).\n"
        "برای لغو /cancel بزن."
    )


@router.message(SellSG.file, F.document)
async def sell_file(message: Message, state: FSMContext):
    await state.update_data(
        file_id=message.document.file_id,
        file_name=message.document.file_name or "file",
    )
    await state.set_state(SellSG.title)
    await message.answer("📝 عنوان جزوه چی باشه؟\nمثلاً: «ریاضی ۱ — فصل ۱ تا ۴»")


@router.message(SellSG.file)
async def sell_file_wrong(message: Message):
    await message.answer("لطفاً فایل رو به‌صورت Document بفرست 📎")


@router.message(SellSG.title)
async def sell_title(message: Message, state: FSMContext):
    if len(message.text.strip()) < 2:
        await message.answer("عنوان خیلی کوتاهه — دوباره بفرست:")
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(SellSG.description)
    await message.answer("🗒️ یه توضیح کوتاه بنویس (مثلاً چی توشه و مال کدوم ترمه).\nبرای رد کردن «-» بفرست.")


@router.message(SellSG.description)
async def sell_description(message: Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(description="" if text == "-" else text)
    await state.set_state(SellSG.price)
    await message.answer("💰 قیمت به تومان؟ (فقط عدد — مثلاً 30000)\nبرای رایگان گذاشتن 0 بفرست.")


@router.message(SellSG.price)
async def sell_price(message: Message, state: FSMContext):
    amount = parse_amount(message.text)
    if amount is None:
        await message.answer("فقط عدد قبوله — دوباره بفرست:")
        return
    await state.update_data(price_toman=amount)
    await state.set_state(SellSG.term)
    await message.answer("📅 سال یا ترم تحصیلی؟ مثلاً «4041» یا «بهار ۱۴۰۴»\nبرای رد کردن «-» بفرست.")


@router.message(SellSG.term)
async def sell_term(message: Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(term="" if text == "-" else text)
    await state.set_state(SellSG.tags)
    await message.answer(
        "🏷️ چند تگ بنویس و با کاما جدا کن — مثلاً:\n«جمع‌بندی، نمونه سوال، حل تمرین»\n"
        "برای رد کردن «-» بفرست."
    )


@router.message(SellSG.tags)
async def sell_tags(message: Message, state: FSMContext):
    text = message.text.strip()
    tags = [] if text == "-" else parse_tags(text)
    await state.update_data(tags=tags)
    await state.set_state(SellSG.kind)
    await message.answer("📚 نوع مدرک چیه؟", reply_markup=kind_kb())


@router.callback_query(SellSG.kind, F.data.startswith("sk:"))
async def sell_kind(cb: CallbackQuery, state: FSMContext):
    value = cb.data.split(":", 1)[1]
    await state.update_data(kind=None if value == "-" else value)
    await cb.answer()
    await state.set_state(SellSG.pick)
    await show_level(cb.message, state, "university")


@router.callback_query(SellSG.pick, F.data.startswith(("su:", "sf:", "sc:", "sp:")))
async def sell_pick(cb: CallbackQuery, state: FSMContext):
    prefix, item_id = cb.data.split(":")
    item_id = int(item_id)
    await cb.answer()
    if prefix == "su":
        await state.update_data(university_id=item_id)
        await show_level(cb.message, state, "faculty")
    elif prefix == "sf":
        await state.update_data(faculty_id=item_id)
        await show_level(cb.message, state, "course")
    elif prefix == "sc":
        await state.update_data(course_id=item_id)
        await show_level(cb.message, state, "professor")
    else:  # sp — آخرین مرحله: ثبت جزوه
        await state.update_data(professor_id=item_id)
        data = await state.get_data()
        payload = {
            "title": data["title"],
            "description": data.get("description", ""),
            "price_toman": data["price_toman"],
            "kind": data.get("kind"),
            "term": data.get("term") or None,
            "tags": data.get("tags") or [],
            "course_id": data["course_id"],
            "professor_id": data["professor_id"],
            "telegram_file_id": data["file_id"],
            "file_name": data["file_name"],
        }
        await cb.message.answer("⏳ در حال آپلود و ثبت جزوه...")
        try:
            await api.post("/notes", cb.from_user.id, json=payload)
        except ApiError as e:
            detail = e.detail if isinstance(e.detail, str) else "خطایی پیش اومد"
            await cb.message.answer(f"❌ ثبت نشد: {detail}")
            return
        await state.clear()
        await cb.message.answer(
            "✅ جزوه ثبت شد و توی صف بررسی ادمین قرار گرفت.\n"
            "بعد از تأیید، منتشر می‌شه و خبرت می‌کنم 🎉",
            reply_markup=MAIN_KB,
        )


@router.callback_query(SellSG.pick, F.data.startswith("snew:"))
async def sell_suggest_new(cb: CallbackQuery, state: FSMContext):
    kind = cb.data.split(":")[1]
    await state.update_data(pending_kind=kind)
    await state.set_state(SellSG.new_name)
    await cb.answer()
    await cb.message.answer(f"✏️ نام {KIND_FA[kind]} جدید رو بنویس (بعد از تأیید ادمین به لیست اضافه می‌شه):")


@router.message(SellSG.new_name)
async def sell_save_suggestion(message: Message, state: FSMContext):
    data = await state.get_data()
    kind = data["pending_kind"]
    payload = {"name": message.text.strip()}
    if kind == "faculty":
        payload["university_id"] = data["university_id"]
    elif kind == "course":
        payload["faculty_id"] = data["faculty_id"]
    elif kind == "professor":
        payload["university_id"] = data["university_id"]
    try:
        await api.post(POST_PATHS[kind], message.from_user.id, json=payload)
    except ApiError:
        await message.answer("ثبت پیشنهاد ممکن نشد 😕 دوباره تلاش کن.")
        return
    await message.answer(
        f"⏳ پیشنهادت («{payload['name']}») ثبت شد و منتظر تأیید ادمینه.\n"
        "فعلاً می‌تونی از موارد موجود انتخاب کنی:"
    )
    await state.set_state(SellSG.pick)
    await show_level(message, state, kind)


STATUS_FA = {
    "pending": "⏳ در انتظار تأیید",
    "approved": "✅ منتشر شده",
    "rejected": "❌ رد شده",
}


@router.message(F.text == "📂 جزوه‌های من")
async def my_notes(message: Message):
    try:
        data = await api.get("/notes/mine", message.from_user.id)
    except ApiError:
        await message.answer("خطایی پیش اومد، دوباره تلاش کن.")
        return
    items = data["items"]
    if not items:
        await message.answer("هنوز جزوه‌ای نذاشتی — از «➕ فروش جزوه» شروع کن!")
        return
    lines = ["📂 جزوه‌های تو:\n"]
    for n in items:
        line = f"• {n['title']} — {STATUS_FA.get(n['status'], n['status'])} — {n['price_toman']:,} تومان"
        if n["status"] == "rejected" and n.get("reject_reason"):
            line += f"\n  ↳ دلیل رد: {n['reject_reason']}"
        lines.append(line)
    await message.answer("\n".join(lines))
