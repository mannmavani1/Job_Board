from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.dependencies.auth import get_current_user

from app.database.session import get_session
from app.models.user import User
from app.schemas.auth import (
    UserRegisterRequest,
    UserRegisterResponse,
    UserLoginRequest,
    TokenResponse
)
from app.core.security import (
    get_password_hash as hash_password,
    verify_password,
    create_access_token
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)




@router.post(
    "/register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED
)
def register_user(
    data: UserRegisterRequest,
    session: Session = Depends(get_session)
):
   
    existing_user = session.exec(
        select(User).where(User.email == data.email)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        role=data.role
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return user




@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK
)
def login_user(
    data: UserLoginRequest,
    session: Session = Depends(get_session)
):
    user = session.exec(
        select(User).where(User.email == data.email)
    ).first()

    if not user or not verify_password(
        data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    access_token = create_access_token(
        data={"sub": str(user.id)}
    )

    return TokenResponse(access_token=access_token)

@router.get("/me", status_code=status.HTTP_200_OK)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user