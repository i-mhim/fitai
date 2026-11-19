"""Minimal email/password authentication for the development backend."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.auth.schemas import Credentials, MeResponse, TokenResponse
from app.auth.security import get_current_user, hash_password, issue_access_token, verify_password
from app.core.db import get_db
from app.core.models import User

router = APIRouter(prefix="/v1/auth", tags=["authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(credentials: Credentials, db: Session = Depends(get_db)) -> TokenResponse:
    email = str(credentials.email).strip().lower()
    user = User(email=email, password_hash=hash_password(credentials.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, detail="Email is already registered") from exc
    return TokenResponse(access_token=issue_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
def login(credentials: Credentials, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == str(credentials.email).strip().lower()))
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(401, detail="Invalid email or password")
    return TokenResponse(access_token=issue_access_token(user.id))


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(id=user.id, email=user.email)
