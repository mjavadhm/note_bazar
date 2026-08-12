"""نرمال‌سازی متادیتای جزوه — واژگان کنترل‌شده نوع مدرک + پارس ترم تحصیلی.

هم‌راستا با خروجی کراولر tgarchive:
  doc_type ∈ DOC_TYPES ، term مثل «4041» (سال+نیمسال) یا «1403» (فقط سال)
"""

import re
import unicodedata

# ---- واژگان کنترل‌شده نوع محتوا (بدون نیم‌فاصله) ----------------
DOC_TYPES: tuple[str, ...] = (
    "جزوه",
    "اسلاید",
    "خلاصه",
    "نمونه سوال میانترم",
    "نمونه سوال پایانترم",
    "نمونه سوال",
    "حل تمرین",
    "تمرین",
    "پروژه",
    "کتاب",
    "برنامه امتحانی",
    "اطلاعیه",
    "سایر",
)

_DOC_ALIASES: dict[str, str] = {
    "نمونه سوال میان ترم": "نمونه سوال میانترم",
    "سوالات میان ترم": "نمونه سوال میانترم",
    "امتحان میان ترم": "نمونه سوال میانترم",
    "میان ترم": "نمونه سوال میانترم",
    "میانترم": "نمونه سوال میانترم",
    "میدترم": "نمونه سوال میانترم",
    "نمونه سوال پایان ترم": "نمونه سوال پایانترم",
    "سوالات پایان ترم": "نمونه سوال پایانترم",
    "امتحان پایان ترم": "نمونه سوال پایانترم",
    "پایان ترم": "نمونه سوال پایانترم",
    "پایانترم": "نمونه سوال پایانترم",
    "فاینال": "نمونه سوال پایانترم",
    "نمونه سوالات": "نمونه سوال",
    "سوالات تشریحی": "نمونه سوال",
    "سوالات": "نمونه سوال",
    "سوال": "نمونه سوال",
    "آزمون": "نمونه سوال",
    "کوئیز": "نمونه سوال",
    "جزوه دست نویس": "جزوه",
    "دست نویس": "جزوه",
    "پاورپوینت": "اسلاید",
    "اسلایدها": "اسلاید",
    "جمع بندی": "خلاصه",
    "حل تمرینات": "حل تمرین",
    "پاسخ تمرین": "حل تمرین",
    "تمرینات": "تمرین",
    "تکلیف": "تمرین",
}

_MAP = str.maketrans(
    {
        "\u064a": "\u06cc",  # ي → ی
        "\u0649": "\u06cc",  # ى → ی
        "\u0643": "\u06a9",  # ك → ک
        "\u0660": "0", "\u0661": "1", "\u0662": "2", "\u0663": "3", "\u0664": "4",
        "\u0665": "5", "\u0666": "6", "\u0667": "7", "\u0668": "8", "\u0669": "9",
        "\u06f0": "0", "\u06f1": "1", "\u06f2": "2", "\u06f3": "3", "\u06f4": "4",
        "\u06f5": "5", "\u06f6": "6", "\u06f7": "7", "\u06f8": "8", "\u06f9": "9",
    }
)

_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

SEMESTERS = {"1": "بهار", "2": "پاییز", "3": "تابستان"}


def fa(text: str | None) -> str:
    """نرمال‌سازی پایه: یکسان‌سازی حروف/اعداد و فاصله‌ها."""
    if not text:
        return ""
    t = unicodedata.normalize("NFC", str(text)).translate(_MAP)
    t = t.replace("\u200c", " ")
    return re.sub(r"\s+", " ", t).strip()


def doc_type(value: str | None) -> str | None:
    """ورودی آزاد → یکی از DOC_TYPES."""
    v = fa(value)
    if not v:
        return None
    if v in DOC_TYPES:
        return v
    if v in _DOC_ALIASES:
        return _DOC_ALIASES[v]
    for known in sorted(DOC_TYPES, key=len, reverse=True):
        if known in v:
            return known
    for key in sorted(_DOC_ALIASES, key=len, reverse=True):
        if key in v:
            return _DOC_ALIASES[key]
    return "سایر"


def parse_term(term: str | None) -> tuple[int | None, str | None]:
    """«4041» ← (1404، «بهار»)  |  «1403» ← (1403, None)"""
    t = re.sub(r"\D", "", fa(term))
    if len(t) == 4 and t.startswith("14"):  # 1403 → فقط سال
        return int(t), None
    if len(t) == 4:  # 4041 → سال ۱۴۰۴ نیمسال ۱
        return 1400 + int(t[:3]), SEMESTERS.get(t[3])
    if len(t) == 2:  # 03 → ۱۴۰۳
        return 1400 + int(t), None
    return None, None


def term_display(term: str | None) -> str | None:
    """ترم خام → متن نمایشی فارسی: «4041» → «بهار ۱۴۰۴»"""
    if not term:
        return None
    year, sem = parse_term(term)
    if not year:
        return fa(term) or None
    fa_year = str(year).translate(_FA_DIGITS)
    return f"{sem} {fa_year}" if sem else fa_year
