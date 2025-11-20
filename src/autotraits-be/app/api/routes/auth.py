from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models import Breeder, User
from app.dependencies import get_db
from app.schemas import UserCreate, UserInDB

router = APIRouter()

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 7  # 7 days


# ======= AUTH API =======
@router.post("/signup", response_model=UserInDB)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    breeder = None
    if user.breeder_name:
        breeder = db.query(Breeder).filter(Breeder.name == user.breeder_name).first()
        if not breeder:
            breeder = Breeder(name=user.breeder_name)
            db.add(breeder)
            db.commit()
            db.refresh(breeder)
    elif user.role != "admin":
        # breeder required for normal users
        raise HTTPException(
            status_code=400, detail="Breeder name required for non-admins"
        )

    db_user = User(
        email=user.email,
        hashed_password=hash_password(user.password),
        full_name=user.full_name,
        role=user.role or "user",
        breeder_id=breeder.id if breeder else None,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/login")
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        {"user_id": user.id, "breeder_id": user.breeder_id, "role": user.role},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(
        {"user_id": user.id},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )

    # Set HttpOnly cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="none",  # required for frontend on different origin
        secure=True,  # set True if using HTTPS
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        samesite="none",  # required for frontend on different origin
        secure=True,
    )

    return {"message": "Login successful"}


@router.post("/refresh")
def refresh_token_endpoint(
    response: Response, request: Request, db: Session = Depends(get_db)
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    payload = decode_token(refresh_token)
    if not payload or payload.type != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_access_token = create_access_token(
        {"user_id": user.id, "breeder_id": user.breeder_id, "role": user.role},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="none",  # required for frontend on different origin
        secure=True,
    )

    return {"message": "Access token refreshed"}


@router.post("/logout")
def logout(response: Response):
    # Clear the access token cookie
    response.delete_cookie(
        key="access_token",
        samesite="none",  # required for frontend on different origin
        secure=True,
    )
    # Clear the refresh token cookie
    response.delete_cookie(
        key="refresh_token",
        samesite="none",  # required for frontend on different origin
        secure=True,
    )

    return {"message": "Logout successful"}
