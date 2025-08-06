"""Endpoints for managing influencers."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy import or_, and_, asc, desc

from ..database import get_session
from ..models import Influencer, User, RoleEnum
from ..schemas import InfluencerCreate, InfluencerRead, InfluencerUpdate
from ..auth import get_current_active_user, require_role


router = APIRouter(prefix="/influencers", tags=["influencers"])


@router.post("/", response_model=InfluencerRead, status_code=status.HTTP_201_CREATED)
async def create_influencer(
    influencer_in: InfluencerCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(RoleEnum.admin)),
):
    """Create a new influencer profile.

    Only admins can create influencers in this simplified model.  In a full
    implementation this endpoint could support bulk import and integration with
    social media APIs.
    """
    influencer = Influencer(**influencer_in.model_dump(), tenant_id=current_user.tenant_id)
    session.add(influencer)
    await session.commit()
    await session.refresh(influencer)
    return InfluencerRead.model_validate(influencer)


@router.get("/", response_model=List[InfluencerRead])
async def list_influencers(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Return all influencer profiles.

    Any authenticated user can view the influencer directory.  Search and
    filtering are not implemented in this skeleton.
    """
    result = await session.execute(
        select(Influencer).where(Influencer.tenant_id == current_user.tenant_id)
    )
    influencers = result.scalars().all()
    return [InfluencerRead.model_validate(i) for i in influencers]


@router.get("/{influencer_id}", response_model=InfluencerRead)
async def get_influencer(
    influencer_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Return a single influencer profile."""
    influencer = await session.get(Influencer, influencer_id)
    if not influencer or influencer.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Influencer not found")
    return InfluencerRead.model_validate(influencer)


@router.put("/{influencer_id}", response_model=InfluencerRead)
async def update_influencer(
    influencer_id: str,
    influencer_in: InfluencerUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(RoleEnum.admin)),
):
    """Update an influencer profile."""
    influencer = await session.get(Influencer, influencer_id)
    if not influencer or influencer.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Influencer not found")
    for attr, value in influencer_in.model_dump(exclude_unset=True).items():
        setattr(influencer, attr, value)
    await session.commit()
    await session.refresh(influencer)
    return InfluencerRead.model_validate(influencer)


@router.delete("/{influencer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_influencer(
    influencer_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(RoleEnum.admin)),
):
    """Delete an influencer."""
    influencer = await session.get(Influencer, influencer_id)
    if not influencer or influencer.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Influencer not found")
    await session.delete(influencer)
    await session.commit()
    return


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_influencers(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(RoleEnum.admin)),
):
    """Refresh influencer metrics.

    This endpoint simulates data enrichment by updating follower counts,
    engagement metrics and other fields for all influencers in the current
    tenant.  In a full implementation this would call external APIs or
    scraping routines to fetch real data.  Only admins can trigger a
    refresh.
    """
    import random
    from datetime import datetime
    result = await session.execute(
        select(Influencer).where(Influencer.tenant_id == current_user.tenant_id)
    )
    influencers = result.scalars().all()
    for inf in influencers:
        # Generate random follower growth and engagement metrics
        current_followers = inf.followers or random.randint(1000, 10000)
        delta = random.randint(-100, 500)
        inf.followers = max(0, current_followers + delta)
        # Random engagement rate between 0.5% and 10%
        inf.engagement_rate = round(random.uniform(0.5, 10.0), 2)
        # Random likes and comments for demonstration
        inf.avg_likes = random.randint(50, 1000)
        inf.avg_comments = random.randint(1, 100)
        # Update last_updated timestamp
        inf.last_updated = datetime.utcnow()
    await session.commit()
    return {"detail": f"Refreshed {len(influencers)} influencers"}


@router.get("/search", response_model=List[InfluencerRead])
async def search_influencers(
    q: str | None = None,
    platform: str | None = None,
    min_followers: int | None = None,
    max_followers: int | None = None,
    min_engagement_rate: float | None = None,
    max_engagement_rate: float | None = None,
    country: str | None = None,
    topic: str | None = None,
    sort_by: str | None = None,
    order: str = "desc",
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
) -> List[InfluencerRead]:
    """Search and filter influencers.

    Supports full‑text search across name, handle, topics and bio as well as
    filtering by platform, follower counts, engagement rates, country and
    topics.  Results can be sorted by followers or engagement_rate.
    """
    # Base query limited to current tenant
    stmt = select(Influencer).where(Influencer.tenant_id == current_user.tenant_id)
    # Full text search (case‑insensitive) across selected fields
    if q:
        pattern = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                Influencer.name.ilike(pattern),
                Influencer.handle.ilike(pattern),
                Influencer.topics.ilike(pattern),
                Influencer.bio.ilike(pattern),
            )
        )
    # Platform filter (case‑insensitive)
    if platform:
        stmt = stmt.where(Influencer.platform.ilike(platform))
    # Country filter
    if country:
        stmt = stmt.where(Influencer.country.ilike(country))
    # Topic filter: topics stored as comma‑separated string
    if topic:
        pattern = f"%{topic.lower()}%"
        stmt = stmt.where(Influencer.topics.ilike(pattern))
    # Follower and engagement filters
    if min_followers is not None:
        stmt = stmt.where((Influencer.followers >= min_followers) | (Influencer.followers == None))
    if max_followers is not None:
        stmt = stmt.where((Influencer.followers <= max_followers) | (Influencer.followers == None))
    if min_engagement_rate is not None:
        stmt = stmt.where((Influencer.engagement_rate >= min_engagement_rate) | (Influencer.engagement_rate == None))
    if max_engagement_rate is not None:
        stmt = stmt.where((Influencer.engagement_rate <= max_engagement_rate) | (Influencer.engagement_rate == None))
    # Sorting
    if sort_by in {"followers", "engagement_rate"}:
        column = getattr(Influencer, sort_by)
        stmt = stmt.order_by(desc(column) if order.lower() == "desc" else asc(column))
    # Execute query
    result = await session.execute(stmt)
    influencers = result.scalars().all()
    return [InfluencerRead.model_validate(i) for i in influencers]