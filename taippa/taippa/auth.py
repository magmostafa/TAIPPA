"""Authentication utilities for TAIPPA.

This module provides functions for hashing passwords, verifying credentials,
generating JSON Web Tokens and retrieving the current user from a request.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated, Optional

import os
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .models import User, RoleEnum
from .schemas import Token, TokenData
from .database import get_session

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for retrieving token from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if the provided password matches the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    """Return a User by email or None if not found."""
    result = await session.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def authenticate_user(session: AsyncSession, email: str, password: str) -> Optional[User]:
    """Verify a user's credentials and return the user if valid."""
    user = await get_user_by_email(session, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a JWT access token containing the provided data.

    The token payload includes an expiration claim (`exp`) calculated from
    `expires_delta`.  The token is signed using the secret key and algorithm
    configured via environment variables.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))))
    to_encode.update({"exp": expire})
    secret_key = os.getenv("JWT_SECRET_KEY", "changeme")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Extract the current user from the JWT token.

    Raises HTTP 401 if the token is invalid or the user cannot be found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    secret_key = os.getenv("JWT_SECRET_KEY", "changeme")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = await get_user_by_email(session, token_data.email)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure the current user is active.

    In this skeleton all users are considered active; if you add an `is_active`
    field to the User model then this function should check it.
    """
    return current_user


def require_role(*allowed_roles: RoleEnum):
    """Return a dependency that enforces one of the specified roles.

    Use this dependency in FastAPI path operations to restrict access based on
    the authenticated user's role.  For example:

        @router.get("/admin")
        async def read_admin_data(current_user: User = Depends(require_role(RoleEnum.admin))):
            ...
    """
    async def role_dependency(current_user: Annotated[User, Depends(get_current_active_user)]) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return role_dependency