"""Endpoints for tenant management.

This router provides APIs to manage tenants in a multi‑tenant deployment. Only
administrators are allowed to create and view tenants.  Regular users can
retrieve their own tenant's details.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_session
from ..models import Tenant, User, RoleEnum
from ..schemas import TenantCreate, TenantRead, TenantUpdate
from ..auth import get_current_active_user, require_role


router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("/", response_model=List[TenantRead])
async def list_tenants(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(RoleEnum.admin)),
):
    """List all tenants.  Admin only."""
    result = await session.execute(select(Tenant))
    tenants = result.scalars().all()
    return [TenantRead.model_validate(t) for t in tenants]


@router.post("/", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_in: TenantCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(RoleEnum.admin)),
):
    """Create a new tenant.  Admin only."""
    tenant = Tenant(**tenant_in.model_dump(exclude_unset=True))
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return TenantRead.model_validate(tenant)


@router.get("/me", response_model=TenantRead)
async def get_my_tenant(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Return the tenant associated with the current user."""
    tenant = await session.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return TenantRead.model_validate(tenant)


# Public endpoint to retrieve a tenant without authentication.
@router.get("/public", response_model=TenantRead)
async def get_public_tenant(
    session: AsyncSession = Depends(get_session),
):
    """Return the first available tenant for unauthenticated users.

    This endpoint allows pages like the login or landing page to display
    tenant branding without requiring authentication.  When multiple tenants
    exist, the first one is returned.  In a production environment this
    could be extended to accept a domain parameter and look up the tenant by
    its custom domain.
    """
    result = await session.execute(select(Tenant).limit(1))
    tenant = result.scalars().first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No tenants configured")
    return TenantRead.model_validate(tenant)


@router.put("/{tenant_id}", response_model=TenantRead)
async def update_tenant(
    tenant_id: str,
    tenant_in: TenantUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(RoleEnum.admin)),
):
    """Update a tenant's details.  Admin only."""
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    for attr, value in tenant_in.model_dump(exclude_unset=True).items():
        setattr(tenant, attr, value)
    await session.commit()
    await session.refresh(tenant)
    return TenantRead.model_validate(tenant)