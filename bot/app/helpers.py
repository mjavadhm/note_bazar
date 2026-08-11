from html import escape


def fa_money(amount: int) -> str:
    return f"{amount:,} تومان"


def card_text(c: dict) -> str:
    stars = (
        f"⭐ {c['rating_avg']} ({c['rating_count']} نظر)"
        if c.get("rating_count")
        else "⭐ هنوز بدون امتیاز"
    )
    pages = f"{c['page_count']} صفحه" if c.get("page_count") else escape(c["file_name"])
    tags = " ".join(f"#{escape(str(t))}" for t in (c.get("tags") or []))

    lines = [
        f"📄 <b>{escape(c['title'])}</b>",
        f"🏛️ {escape(c['university'])} ← {escape(c['course'])}",
        f"👨‍🏫 {escape(c['professor'])}",
        f"📃 {pages} | {stars}",
    ]
    if c.get("term"):
        lines.append(f"📅 {escape(c['term'])}")
    if tags:
        lines.append(f"🏷️ {tags}")
    lines.append(f"💰 {fa_money(c['price_toman'])}")
    lines.append(f"👤 فروشنده: {escape(c['seller_name'])}")

    description = escape(c.get("description") or "")
    if description:
        lines += ["", description]
    return "\n".join(lines)
