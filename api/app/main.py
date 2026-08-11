from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db, init_db
from .models import User
from .routers import admin, importer, miniapp, notes, public, purchases, taxonomy, wallet
from .schemas import RegisterIn
from .storage import ensure_bucket


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    ensure_bucket()
    yield


app = FastAPI(title="NoteBazar API", lifespan=lifespan)
app.include_router(taxonomy.router)
app.include_router(notes.router)
app.include_router(purchases.router)
app.include_router(wallet.router)
app.include_router(admin.router)
app.include_router(public.router)
app.include_router(miniapp.router)
app.include_router(importer.router)


@app.get("/")
def root():
    return {"name": "NoteBazar API", "docs": "/docs"}


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/auth/register")
def register(
    body: RegisterIn,
    x_bot_secret: str = Header(),
    db: Session = Depends(get_db),
):
    if x_bot_secret != settings.api_secret:
        raise HTTPException(401, "invalid bot secret")
    user = db.query(User).filter(User.telegram_id == body.telegram_id).first()
    if user is None:
        user = User(telegram_id=body.telegram_id)
        db.add(user)
    user.username = body.username
    user.first_name = body.first_name
    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "is_admin": user.is_admin or user.telegram_id in settings.admin_ids,
    }
