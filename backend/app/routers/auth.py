from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.auth import (
    DUMMY_HASH, clear_session_cookie, create_session, current_user, login_limiter,
    set_session_cookie, verify_password,
)
from app.db import get_db
from app.models import Customer, User

router = APIRouter(prefix="/auth", tags=["auth"])


def me_view(db: Session, user: User) -> schemas.Me:
    if user.role == "customer" and user.customer_id:
        c = db.get(Customer, user.customer_id)
        return schemas.Me(role="customer", display_name=f"{c.first_name} {c.last_name}")
    return schemas.Me(role="advisor", display_name="KBC Advisor")


@router.post("/login", response_model=schemas.Me)
def login(body: schemas.LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    if login_limiter.blocked(body.username, ip):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many failed attempts, try again later")
    user = db.scalar(select(User).where(User.username == body.username.lower()))
    valid = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        login_limiter.record_failure(body.username, ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    set_session_cookie(response, create_session(user))
    return me_view(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    clear_session_cookie(response)


@router.get("/me", response_model=schemas.Me)
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return me_view(db, user)
