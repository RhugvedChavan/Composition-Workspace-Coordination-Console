"""User management endpoints."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.crud import get_user_or_404
from app.database import get_session
from app.models import User
from app.schemas import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(name=payload.name, email=payload.email, role=payload.role)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.get("", response_model=List[UserRead])
def list_users(session: Session = Depends(get_session)):
    return session.exec(select(User).order_by(User.id)).all()


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, session: Session = Depends(get_session)):
    return get_user_or_404(session, user_id)
