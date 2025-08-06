"""Authentication endpoints.

Provides routes for user registration, login and retrieving the current user.
"""

from __future__ import annotations

from datetime import timedelta
import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from .. import schemas
from ..auth import (
    create_access_token,
    authenticate_user,
    get_current_active_user,
    get_password_hash,
    get_user_by_email,
)
from ..database import get_session
from ..models import User, RoleEnum


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: schemas.UserCreate, session: AsyncSession = Depends(get_session)):
    """Create a new user account.

    The user is created with the role specified in the request.  Duplicate
    email addresses are not allowed.  Passwords are hashed before storage.
    """
    # Check if email already exists
    existing = await get_user_by_email(session, user_in.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    hashed_password = get_password_hash(user_in.password)
    # Determine tenant for the new user.  If specified in the request use that,
    # otherwise fall back to DEFAULT_TENANT_ID environment variable.  If no default
    # tenant exists in the database, raise an error.
    tenant_id = user_in.tenant_id
    if not tenant_id:
        tenant_id = os.getenv("DEFAULT_TENANT_ID")
    if not tenant_id:
        # fetch first tenant as fallback
        from ..models import Tenant
        result = await session.execute(select(Tenant))
        tenant = result.scalars().first()
        if tenant:
            tenant_id = tenant.id
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No tenant configured for user registration")
    user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name,
        role=user_in.role,
        tenant_id=tenant_id,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return schemas.UserRead.model_validate(user)


@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
):
    """Authenticate a user and return a JWT token."""
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")))
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return schemas.Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=schemas.UserRead)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Return the currently authenticated user."""
    return schemas.UserRead.model_validate(current_user)