"""Routes for campaign management."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_session
from ..models import Campaign, Brand, User, RoleEnum, CampaignStatus
from ..schemas import CampaignCreate, CampaignRead, CampaignUpdate
from ..auth import get_current_active_user, require_role
from ..services.ai import analyse_brief


router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("/", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_in: CampaignCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new campaign under a brand.

    Only admins and brand owners can create campaigns for a given brand.  The
    request may optionally trigger AI analysis of the brief (not implemented
    here).  The analysis field remains null until triggered via a separate
    endpoint.
    """
    brand = await session.get(Brand, campaign_in.brand_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    if current_user.role != RoleEnum.admin and brand.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised to create campaigns for this brand")
    # ensure brand belongs to current tenant
    if brand.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised to create campaigns for this tenant")
    campaign = Campaign(
        brand_id=campaign_in.brand_id,
        title=campaign_in.title,
        brief=campaign_in.brief,
        status=campaign_in.status,
        start_date=campaign_in.start_date,
        end_date=campaign_in.end_date,
        budget=campaign_in.budget,
        tenant_id=current_user.tenant_id,
    )
    session.add(campaign)
    await session.commit()
    await session.refresh(campaign)
    return CampaignRead.model_validate(campaign)


@router.get("/", response_model=List[CampaignRead])
async def list_campaigns(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
    brand_id: str | None = None,
):
    """List campaigns visible to the current user.

    Admins see all campaigns; clients see campaigns belonging to their brands.
    """
    # Always restrict to current tenant
    query = select(Campaign).where(Campaign.tenant_id == current_user.tenant_id)
    if brand_id:
        query = query.where(Campaign.brand_id == brand_id)
    if current_user.role != RoleEnum.admin:
        # restrict to campaigns belonging to the user's brands
        query = query.join(Brand).where(Brand.owner_id == current_user.id)
    result = await session.execute(query)
    campaigns = result.scalars().all()
    return [CampaignRead.model_validate(c) for c in campaigns]


@router.get("/{campaign_id}", response_model=CampaignRead)
async def get_campaign(
    campaign_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Return a campaign by ID, if authorised."""
    campaign = await session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    # verify tenant
    if campaign.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised to view this campaign")
    if current_user.role != RoleEnum.admin:
        brand = await session.get(Brand, campaign.brand_id)
        if not brand or brand.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised to view this campaign")
    return CampaignRead.model_validate(campaign)


@router.put("/{campaign_id}", response_model=CampaignRead)
async def update_campaign(
    campaign_id: str,
    campaign_in: CampaignUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Update a campaign.  Only authorised users may modify campaigns."""
    campaign = await session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if campaign.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised to modify this campaign")
    if current_user.role != RoleEnum.admin:
        brand = await session.get(Brand, campaign.brand_id)
        if not brand or brand.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised to modify this campaign")
    # apply updates
    for attr, value in campaign_in.model_dump(exclude_unset=True).items():
        setattr(campaign, attr, value)
    await session.commit()
    await session.refresh(campaign)
    return CampaignRead.model_validate(campaign)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a campaign."""
    campaign = await session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if campaign.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised to delete this campaign")
    if current_user.role != RoleEnum.admin:
        brand = await session.get(Brand, campaign.brand_id)
        if not brand or brand.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised to delete this campaign")
    await session.delete(campaign)
    await session.commit()
    return


@router.post("/{campaign_id}/analyse", response_model=CampaignRead)
async def analyse_campaign_brief(
    campaign_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(RoleEnum.admin, RoleEnum.client)),
):
    """Analyse a campaign's brief using the AI engine and update the analysis field.

    This endpoint triggers the AI analysis of the campaign brief by calling the
    `analyse_brief` service.  The result is stored in the `analysis` column of
    the campaign.  Only admins and brand owners can trigger analysis.
    """
    campaign = await session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    brand = await session.get(Brand, campaign.brand_id)
    if campaign.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised to analyse this campaign")
    if not brand or (current_user.role != RoleEnum.admin and brand.owner_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised to analyse this campaign")
    # call AI service (may be asynchronous) to process the brief
    analysis = await analyse_brief(campaign.brief)
    campaign.analysis = analysis
    await session.commit()
    await session.refresh(campaign)
    return CampaignRead.model_validate(campaign)