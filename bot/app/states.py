from aiogram.fsm.state import State, StatesGroup


class SearchSG(StatesGroup):
    query = State()


class SellSG(StatesGroup):
    file = State()
    title = State()
    description = State()
    price = State()
    term = State()       # سال/ترم تحصیلی (اختیاری)
    tags = State()       # تگ‌ها با کاما (اختیاری)
    kind = State()       # نوع مدرک — انتخاب با دکمه (اختیاری)
    pick = State()       # انتخاب درخت با دکمه‌های اینلاین
    new_name = State()   # نام مورد جدیدی که کاربر پیشنهاد میده


class CreditSG(StatesGroup):
    amount = State()
