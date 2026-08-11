from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, require_admin
from ..models import LedgerEntry, LedgerKind, User
from ..schemas import CreditIn
from ..services import wallet_balance

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("")
def get_wallet(db: Session = Depends(get_db), user: User = Depends(current_user)):
    entries = (
        db.query(LedgerEntry)
        .filter(LedgerEntry.user_id == user.id)
        .order_by(LedgerEntry.created_at.desc())
        .limit(10)
        .all()
    )
    return {
        "balance": wallet_balance(db, user.id),
        "entries": [
            {
                "amount": e.amount_toman,
                "kind": e.kind.value,
                "note": e.note,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ],
    }


@router.post("/dev-credit")
def dev_credit(
    body: CreditIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """شارژ تستی — فقط ادمین. تا وقتی درگاه پرداخت وصل بشه، از این برای تست استفاده کن."""
    db.add(
        LedgerEntry(
            user_id=admin.id,
            amount_toman=body.amount,
            kind=LedgerKind.charge,
            note="شارژ تستی",
        )
    )
    db.commit()
    return {"balance": wallet_balance(db, admin.id)}
