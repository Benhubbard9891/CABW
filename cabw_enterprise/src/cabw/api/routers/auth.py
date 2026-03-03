"""Authentication router."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cabw.api.schemas import Token, TokenData, UserCreate, UserResponse
from cabw.config import settings
from cabw.db.base import db_manager
from cabw.db.models import User
from cabw.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.auth.access_token_expire_minutes
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.auth.secret_key,
        algorithm=settings.auth.algorithm
    )
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(db_manager.get_session)
) -> User:
    """Get current user from token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.auth.secret_key,
            algorithms=[settings.auth.algorithm]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError as err:
        raise credentials_exception from err

    result = await session.execute(
        select(User).where(User.id == token_data.user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(db_manager.get_session)
) -> User:
    """Register new user."""
    # Check if email exists
    result = await session.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if username exists
    result = await session.execute(
        select(User).where(User.username == user_data.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Create user
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    logger.info(f"User registered: {user.username}")
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(db_manager.get_session)
) -> dict:
    """Login user and return access token."""
    # Find user by email or username
    result = await session.execute(
        select(User).where(
            (User.email == form_data.username) | (User.username == form_data.username)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    await session.commit()

    # Create token
    access_token_expires = timedelta(minutes=settings.auth.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )

    logger.info(f"User logged in: {user.username}")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.auth.access_token_expire_minutes * 60
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)) -> User:
    """Get current user info."""
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """Refresh access token."""
    access_token_expires = timedelta(minutes=settings.auth.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(current_user.id)},
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.auth.access_token_expire_minutes * 60
    }
