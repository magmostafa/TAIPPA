"""Endpoints for capturing marketing leads."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_session
from ..models import Lead, User, RoleEnum, Tenant
from ..schemas import LeadCreate, LeadRead, LeadUpdate
from ..auth import get_current_active_user, require_role
import os


router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("/", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
async def create_lead(
    lead_in: LeadCreate,
    session: AsyncSession = Depends(get_session),
):
    """Capture a new marketing lead.

    This endpoint is public and does not require authentication.  The lead is stored
    for later follow‑up by the sales team.
    """
    # Determine tenant for public lead.  Use DEFAULT_TENANT_ID environment variable
    tenant_id = os.getenv("DEFAULT_TENANT_ID")
    if not tenant_id:
        # if no default tenant configured, attempt to select the first tenant
        result = await session.execute(select(Tenant))
        tenant = result.scalars().first()
        if not tenant:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No tenant configured for lead capture")
        tenant_id = tenant.id
    lead = Lead(**lead_in.model_dump(), tenant_id=tenant_id)
    session.add(lead)
    await session.commit()
    await session.refresh(lead)
    return LeadRead.model_validate(lead)


@router.get("/", response_model=List[LeadRead])
async def list_leads(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(RoleEnum.admin, RoleEnum.team_member)),
):
    """List captured leads for the sales team.

    Only admin and team_member roles can view leads.
    """
    # restrict to leads in current user's tenant
    result = await session.execute(select(Lead).where(Lead.tenant_id == current_user.tenant_id))
    leads = result.scalars().all()
    return [LeadRead.model_validate(l) for l in leads]


@router.put("/{lead_id}", response_model=LeadRead)
async def update_lead(
    lead_id: str,
    lead_in: LeadUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(RoleEnum.admin, RoleEnum.team_member)),
):
    """Update a lead's status or notes."""
    lead = await session.get(Lead, lead_id)
    if not lead or lead.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    for attr, value in lead_in.model_dump(exclude_unset=True).items():
        setattr(lead, attr, value)
    await session.commit()
    await session.refresh(lead)
    return LeadRead.model_validate(lead)