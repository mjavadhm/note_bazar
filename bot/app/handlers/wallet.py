from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ..api import ApiError, api
from ..config import settings
from ..keyboards import WALLET_ADMIN_KB
from ..states import CreditSG
from .sell import parse_amount

router = Router()

KIND_FA = {
    "charge": "شارژ",
    "purchase": "خرید",
    "earning": "فروش",
    "commission": "کمیسیون",
    "refund": "برگشت وجه",
    "payout": "تسویه",
    "adjustment": "اصلاحیه",
}


@router.message(F.text == "💰 کیف پول")
async def wallet(message: Message):
    try:
        data = await api.get("/wallet", message.from_user.id)
    except ApiError:
        await message.answer("خطایی پیش اومد، دوباره تلاش کن.")
        return
    lines = [f"💰 موجودی: <b>{data['balance']:,} تومان</b>"]
    if data["entries"]:
        lines.append("\nآخرین تراکنش‌ها:")
        for e in data["entries"]:
            sign = "➕" if e["amount"] >= 0 else "➖"
            label = KIND_FA.get(e["kind"], e["kind"])
            note = f" ({e['note']})" if e.get("note") else ""
            lines.append(f"{sign} {abs(e['amount']):,} — {label}{note}")
    kb = WALLET_ADMIN_KB if message.from_user.id in settings.admin_ids else None
    await message.answer("\n".join(lines), reply_markup=kb)


@router.callback_query(F.data == "dc")
async def dev_credit_start(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in settings.admin_ids:
        await cb.answer("فقط ادمین", show_alert=True)
        return
    await state.set_state(CreditSG.amount)
    await cb.answer()
    await cb.message.answer("💳 مبلغ شارژ تستی به تومان؟")


@router.message(CreditSG.amount)
async def dev_credit_do(message: Message, state: FSMContext):
    amount = parse_amount(message.text)
    if amount is None or amount <= 0:
        await message.answer("فقط عدد مثبت — دوباره بفرست:")
        return
    await state.clear()
    try:
        result = await api.post("/wallet/dev-credit", message.from_user.id, json={"amount": amount})
    except ApiError:
        await message.answer("شارژ نشد 😕")
        return
    await message.answer(f"✅ شارژ شد. موجودی جدید: {result['balance']:,} تومان")
