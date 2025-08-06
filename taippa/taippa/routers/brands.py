"""Routes for managing brand profiles."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_session
from ..models import Brand, User, RoleEnum
from ..schemas import BrandCreate, BrandRead, BrandUpdate
from ..auth import get_current_active_user, require_role


router = APIRouter(prefix="/brands", tags=["brands"])


@router.post("/", response_model=BrandRead, status_code=status.HTTP_201_CREATED)
async def create_brand(
    brand_in: BrandCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(RoleEnum.admin, RoleEnum.client)),
):
    """Create a new brand owned by the current user."""
    brand = Brand(
        owner_id=current_user.id,
        name=brand_in.name,
        description=brand_in.description,
        industry=brand_in.industry,
        contact_email=brand_in.contact_email,
        target_audience=brand_in.target_audience,
        budget=brand_in.budget,
        tenant_id=current_user.tenant_id,
    )
    session.add(brand)
    await session.commit()
    await session.refresh(brand)
    return BrandRead.model_validate(brand)


@router.get("/", response_model=List[BrandRead])
async def list_brands(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Return brands visible to the current user.

    Admin users see all brands.  Clients see only their own brands.  Other
    roles currently return an empty list but could be extended to see assigned
    brands.
    """
    # Limit results to the current tenant
    query = select(Brand).where(Brand.tenant_id == current_user.tenant_id)
    # Non‑admin users only see their own brands
    if current_user.role != RoleEnum.admin:
        query = query.where(Brand.owner_id == current_user.id)
    result = await session.execute(query)
    brands = result.scalars().all()
    return [BrandRead.model_validate(b) for b in brands]


@router.get("/{brand_id}", response_model=BrandRead)
async def get_brand(
    brand_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Return a brand if the user has permission to view it."""
    brand = await session.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    # Verify tenant and owner permissions
    if brand.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised to view this brand")
    if current_user.role != RoleEnum.admin and brand.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised to view this brand")
    return BrandRead.model_validate(brand)


@router.put("/{brand_id}", response_model=BrandRead)
async def update_brand(
    brand_id: str,
    brand_in: BrandUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Update a brand's details."""
    brand = await session.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    # verify tenant and owner
    if brand.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised to update this brand")
    if current_user.role != RoleEnum.admin and brand.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised to update this brand")
    for attr, value in brand_in.model_dump(exclude_unset=True).items():
        setattr(brand, attr, value)
    await session.commit()
    await session.refresh(brand)
    return BrandRead.model_validate(brand)


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand(
    brand_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a brand."""
    brand = await session.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    if brand.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised to delete this brand")
    if current_user.role != RoleEnum.admin and brand.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised to delete this brand")
    await session.delete(brand)
    await session.commit()
    return