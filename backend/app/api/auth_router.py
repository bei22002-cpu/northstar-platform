from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse, RefreshRequest
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    user = auth_service.register_user(db, user_data)
    return user


@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = auth_service.authenticate_user(db, credentials.email, credentials.password)
    return auth_service.generate_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    return auth_service.refresh_access_token(db, body.refresh_token)
