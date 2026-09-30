"""Password hashing, signed session cookies, login rate limiting and role dependencies."""

import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Customer, User

COOKIE_NAME = "session"
ALGORITHM = "HS256"
SCRYPT = dict(n=2**14, r=8, p=1, dklen=32)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **SCRYPT)
    return hmac.compare_digest(digest.hex(), digest_hex)


# Used to spend the same time on unknown usernames as on wrong passwords.
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def create_session(user: User) -> str:
    now = datetime.now(timezone.utc)
    claims = {"sub": str(user.id), "role": user.role, "iat": now, "exp": now + timedelta(hours=settings.session_hours)}
    return jwt.encode(claims, settings.session_secret, algorithm=ALGORITHM)


def set_session_cookie(response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME, token, max_age=settings.session_hours * 3600, httponly=True,
        samesite="lax", secure=settings.cookie_secure, path="/",
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="lax", secure=settings.cookie_secure)


class LoginRateLimiter:
    """In-memory sliding window of failed logins per (username, client IP). Single-process only."""

    def __init__(self, max_failures: int = 5, window_seconds: int = 300):
        self.max_failures = max_failures
        self.window = window_seconds
        self._failures: dict[tuple[str, str], deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key, now) -> deque | None:
        q = self._failures.get(key)
        if q is None:
            return None
        while q and now - q[0] > self.window:
            q.popleft()
        if not q:
            del self._failures[key]
            return None
        return q

    def blocked(self, username: str, ip: str) -> bool:
        with self._lock:
            q = self._prune((username.lower(), ip), time.monotonic())
            return q is not None and len(q) >= self.max_failures

    def record_failure(self, username: str, ip: str) -> None:
        with self._lock:
            now = time.monotonic()
            key = (username.lower(), ip)
            self._prune(key, now)
            self._failures[key].append(now)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


login_limiter = LoginRateLimiter()

UNAUTHORIZED = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise UNAUTHORIZED
    try:
        claims = jwt.decode(token, settings.session_secret, algorithms=[ALGORITHM], options={"require": ["exp", "sub"]})
    except jwt.PyJWTError:
        raise UNAUTHORIZED
    user = db.get(User, int(claims["sub"]))
    if user is None or user.role != claims.get("role"):
        raise UNAUTHORIZED
    return user


def require_advisor(user: User = Depends(current_user)) -> User:
    if user.role != "advisor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Advisors only")
    return user


def require_customer(user: User = Depends(current_user), db: Session = Depends(get_db)) -> Customer:
    """The customer comes from the session only, never from a request parameter."""
    if user.role != "customer" or user.customer_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customers only")
    customer = db.get(Customer, user.customer_id)
    if customer is None:
        raise UNAUTHORIZED
    return customer
