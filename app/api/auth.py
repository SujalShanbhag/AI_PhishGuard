from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.database_models import User
from app.models.schemas import UserRegister, UserLogin, UserResponse, TokenResponse, RetentionUpdate
from app.security.authentication import (
    hash_password, verify_password, create_access_token, get_current_user, enforce_rate_limit
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse)
def register_user(req: Request, response: Response, user_in: UserRegister, db: Session = Depends(get_db)):
    enforce_rate_limit(req, max_requests=10, window_seconds=60)
    
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address is already registered."
        )

    user = User(
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        full_name=user_in.full_name or user_in.email.split("@")[0].capitalize(),
        role=user_in.role or "analyst"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.post("/login", response_model=TokenResponse)
def login_user(req: Request, response: Response, login_in: UserLogin, db: Session = Depends(get_db)):
    enforce_rate_limit(req, max_requests=settings.LOGIN_RATE_LIMIT, window_seconds=settings.LOGIN_RATE_LIMIT_WINDOW)
    
    user = db.query(User).filter(User.email == login_in.email).first()
    if not user or not verify_password(login_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password credentials."
        )

    token = create_access_token({"sub": user.id})
    # Set cookie for seamless web UI session
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.post("/logout")
def logout_user(response: Response, current_user: User = Depends(get_current_user)):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully."}

@router.get("/me", response_model=UserResponse)
def get_user_profile(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

@router.put("/retention")
def update_retention_policy(
    update_in: RetentionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_user.retention_days = update_in.retention_days
    db.commit()
    return {"message": f"Data retention policy updated to {update_in.retention_days} days."}

@router.delete("/me")
def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes user account and cascades deletion of analyses, identity, and reports."""
    db.delete(current_user)
    db.commit()
    return {"message": "Account and all associated private forensic data wiped successfully."}
