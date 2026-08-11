from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import current_user
from ..models import LedgerEntry, LedgerKind, Note, Purchase, PurchaseStatus, Status, User
from ..schemas import PurchaseIn
from ..services import wallet_balance
from ..telegram_files import send_telegram_message

router = APIRouter(prefix="/purchases", tags=["purchases"])


@router.post("", status_code=201)
def buy_note(
    body: PurchaseIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    note = db.get(Note, body.note_id)
    if note is None or note.status != Status.approved:
        raise HTTPException(404, "جزوه پیدا نشد")
    if note.seller_id == user.id:
        raise HTTPException(400, "نمی‌تونی جزوه خودت رو بخری 🙂")
    existing = (
        db.query(Purchase)
        .filter(Purchase.buyer_id == user.id, Purchase.note_id == note.id)
        .first()
    )
    if existing:
        raise HTTPException(400, "این جزوه رو قبلاً خریدی — از «خریدهای من» دانلودش کن")

    price = note.price_toman
    balance = wallet_balance(db, user.id)
    if balance < price:
        raise HTTPException(
            402,
            detail={"message": "موجودی کافی نیست", "balance": balance, "price": price},
        )

    commission = price * settings.commission_percent // 100
    # فعلاً آزادسازی فوری؛ برای escrow بعداً status=held + تایمر آزادسازی اضافه می‌شه
    purchase = Purchase(
        buyer_id=user.id,
        note_id=note.id,
        price_toman=price,
        commission_toman=commission,
        status=PurchaseStatus.released,
    )
    db.add(purchase)
    db.flush()
    db.add_all(
        [
            LedgerEntry(
                user_id=user.id,
                amount_toman=-price,
                kind=LedgerKind.purchase,
                purchase_id=purchase.id,
                note=f"خرید «{note.title}»",
            ),
            LedgerEntry(
                user_id=note.seller_id,
                amount_toman=price - commission,
                kind=LedgerKind.earning,
                purchase_id=purchase.id,
                note=f"فروش «{note.title}»",
            ),
            LedgerEntry(
                user_id=None,  # پلتفرم
                amount_toman=commission,
                kind=LedgerKind.commission,
                purchase_id=purchase.id,
                note=f"کمیسیون «{note.title}»",
            ),
        ]
    )
    db.commit()

    seller = note.seller
    send_telegram_message(
        seller.telegram_id,
        f"🎉 جزوه «{note.title}» فروخته شد!\nمبلغ {(price - commission):,} تومان به کیف پولت اضافه شد.",
    )
    return {"id": purchase.id, "status": purchase.status.value}


@router.get("/mine")
def my_purchases(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = (
        db.query(Purchase)
        .filter(Purchase.buyer_id == user.id)
        .order_by(Purchase.created_at.desc())
        .limit(50)
        .all()
    )
    return {
        "items": [
            {
                "id": p.id,
                "note_id": p.note_id,
                "title": p.note.title,
                "price_toman": p.price_toman,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in rows
        ]
    }
