from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Base, engine, get_db
from app.models import Item
from app.schemas import ItemCreate, ItemRead


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Starter convenience: create tables on boot. Swap for Alembic migrations when the schema grows.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Starter API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/items", response_model=list[ItemRead])
def list_items(db: Session = Depends(get_db)):
    return db.scalars(select(Item).order_by(Item.id.desc())).all()


@app.post("/items", response_model=ItemRead, status_code=201)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)):
    item = Item(name=payload.name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
