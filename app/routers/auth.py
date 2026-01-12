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
    """
    Register a new user in the system.

    **Business Logic:**
    - Checks if the email is already registered to prevent duplicates.
    - Hashes the password before storing it in the database for security.
    - Assigns the specified role (Recruiter or Job Seeker).

    **Args:**
    - data (UserRegisterRequest): The registration details (email, password, role).

    **Returns:**
    - UserRegisterResponse: The created user object (excluding the password).

    **Raises:**
    - 400 Bad Request: If the email is already in use.
    """
    
    # Validation: Check if a user with this email already exists
    existing_user = session.exec(
        select(User).where(User.email == data.email)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # Creation: Hash the password and create the User instance
    # NEVER store plain-text passwords
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
    """
    Authenticate a user and issue a JWT access token.

    **Business Logic:**
    - Verifies that the email exists in the database.
    - Verifies that the provided password matches the stored hash.
    - Generates a JSON Web Token (JWT) that can be used for subsequent authenticated requests.

    **Args:**
    - data (UserLoginRequest): The login credentials (email and password).

    **Returns:**
    - TokenResponse: The JWT access token and token type.

    **Raises:**
    - 401 Unauthorized: If the email is not found or the password is incorrect.
    """
    
    # 1. Retrieve the user by email
    user = session.exec(
        select(User).where(User.email == data.email)
    ).first()

    # 2. Authenticate: Check if user exists AND if password matches hash
    if not user or not verify_password(
        data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # 3. Generate Token: Create a JWT with the user's ID as the subject ('sub')
    access_token = create_access_token(
        data={"sub": str(user.id)}
    )

    return TokenResponse(access_token=access_token)


@router.get("/me", status_code=status.HTTP_200_OK)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Retrieve the profile information of the currently authenticated user.

    **Mechanism:**
    - Uses the `get_current_user` dependency to validate the Bearer Token from the request header.
    - If the token is valid, the corresponding user object is returned.

    **Returns:**
    - User: The full user object of the logged-in user.
    """
    return current_user