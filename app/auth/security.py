"""Argon2 password hashes and short-lived signed access tokens."""
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.config import get_jwt_secret
from app.core.db import get_db
from app.core.models import User

hasher = PasswordHasher()
bearer = HTTPBearer(auto_error=False)


def jwt_secret() -> str:
    return get_jwt_secret()


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        return hasher.verify(stored_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def issue_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": user_id, "iss": "fitai", "aud": "fitai-api", "iat": now, "exp": now + timedelta(minutes=30)},
        jwt_secret(), algorithm="HS256"
    )


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(status_code=401, detail="Invalid or missing bearer token", headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(credentials.credentials, jwt_secret(), algorithms=["HS256"], audience="fitai-api", issuer="fitai", options={"require": ["sub", "iat", "exp"]})
        subject = payload["sub"]
        if not isinstance(subject, str):
            raise unauthorized
    except InvalidTokenError as exc:
        raise unauthorized from exc
    user = db.get(User, subject)
    if user is None:
        raise unauthorized
    return user
