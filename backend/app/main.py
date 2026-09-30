from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app import jev
from app.categories import CATEGORIES
from app.config import settings
from app.db import get_db
from app.models import Item
from app.schemas import ItemCreate, ItemRead

app = FastAPI(title="Starter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


def apply_category(item: Item) -> None:
    result = jev.categorize(item.name)
    if result:
        item.category, item.category_confidence = result


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "jev": bool(settings.openrouter_api_key)}


@app.get("/categories")
def list_categories():
    return CATEGORIES


@app.get("/items", response_model=list[ItemRead])
def list_items(category: str | None = None, db: Session = Depends(get_db)):
    query = select(Item).order_by(Item.id.desc())
    if category:
        query = query.where(Item.category == category)
    return db.scalars(query).all()


@app.post("/items", response_model=ItemRead, status_code=201)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)):
    item = Item(name=payload.name)
    apply_category(item)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.post("/items/{item_id}/categorize", response_model=ItemRead)
def categorize_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    apply_category(item)
    db.commit()
    db.refresh(item)
    return item
