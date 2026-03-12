from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_refresh_token, create_access_token, create_refresh_token
from app.schemas.user import UserCreate, UserOut, Token, TokenRefresh
from app.services.auth_service import (
    get_user_by_email,
    create_user,
    authenticate_user,
    issue_tokens,
)

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing = get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    return create_user(db, user_data)


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return issue_tokens(user)


@router.post("/refresh", response_model=Token)
def refresh_tokens(body: TokenRefresh, db: Session = Depends(get_db)):
    payload = decode_refresh_token(body.refresh_token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user = get_user_by_email(db, payload.get("email", ""))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return issue_tokens(user)
