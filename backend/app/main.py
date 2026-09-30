import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal, get_db
from app.detection import gemini
from app.limits import RequestLimitsMiddleware
from app.routers import advisor, auth, me
from app.seed import seed, story_customer_ids
from app.analysis import personalize_in_background

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    with SessionLocal() as db:
        seed(db)
    personalize_in_background(story_customer_ids())
    yield


app = FastAPI(title="KBC Foresight API", lifespan=lifespan)

app.add_middleware(RequestLimitsMiddleware, max_body_bytes=settings.max_body_bytes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type"],
)

MAX_VALIDATION_ERRORS = 5


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    # The contract promises {"detail": "<string>"} for every error, including 422.
    parts = []
    for err in exc.errors()[:MAX_VALIDATION_ERRORS]:  # bounded response, whatever the payload
        field = ".".join(str(p) for p in err.get("loc", []) if p not in ("body", "query", "path"))
        message = str(err.get("msg", "invalid value")).removeprefix("Value error, ")[:200]
        parts.append(f"{field}: {message}" if field else message)
    return JSONResponse(status_code=422, content={"detail": "; ".join(parts) or "Invalid request"})


app.include_router(auth.router)
app.include_router(me.router)
app.include_router(advisor.router)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "ai": gemini.is_configured()}
