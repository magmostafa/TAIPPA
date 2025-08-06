"""Pydantic schemas for TAIPPA API.

These models define the shape of request payloads and response bodies for
FastAPI.  They are separate from the database models to decouple the
external API surface from the internal storage representation.

Each schema class uses `model_config` to enable ORM mode for compatibility
with SQLAlchemy objects.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from .models import RoleEnum, CampaignStatus
from .models import SubscriptionStatus, Lead


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: RoleEnum = RoleEnum.client
    # Optional tenant identifier for multi‑tenant setups.  When creating
    # users via the admin interface you can specify which tenant they belong to.
    tenant_id: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserRead(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class UserInDB(UserBase):
    id: str
    hashed_password: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class UserUpdate(BaseModel):
    full_name: Optional[str] = None


class BrandBase(BaseModel):
    name: str
    description: Optional[str] = None
    industry: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    target_audience: Optional[str] = None
    budget: Optional[float] = None


class BrandCreate(BrandBase):
    pass


class BrandUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    target_audience: Optional[str] = None
    budget: Optional[float] = None


class BrandRead(BrandBase):
    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class CampaignBase(BaseModel):
    title: str
    brief: str
    status: CampaignStatus = CampaignStatus.draft
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = None


class CampaignCreate(CampaignBase):
    brand_id: str


class CampaignUpdate(BaseModel):
    title: Optional[str] = None
    brief: Optional[str] = None
    status: Optional[CampaignStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = None
    analysis: Optional[str] = None


class CampaignRead(CampaignBase):
    id: str
    brand_id: str
    analysis: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class InfluencerBase(BaseModel):
    handle: str
    name: str
    platform: str
    followers: Optional[int] = None
    engagement_rate: Optional[float] = None
    # Enriched fields
    bio: Optional[str] = None
    topics: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None
    avg_likes: Optional[int] = None
    avg_comments: Optional[int] = None
    audience_country: Optional[str] = None
    audience_gender: Optional[str] = None
    audience_age: Optional[str] = None
    last_updated: Optional[datetime] = None


class InfluencerCreate(InfluencerBase):
    pass


class InfluencerUpdate(BaseModel):
    handle: Optional[str] = None
    name: Optional[str] = None
    platform: Optional[str] = None
    followers: Optional[int] = None
    engagement_rate: Optional[float] = None
    bio: Optional[str] = None
    topics: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None
    avg_likes: Optional[int] = None
    avg_comments: Optional[int] = None
    audience_country: Optional[str] = None
    audience_gender: Optional[str] = None
    audience_age: Optional[str] = None
    last_updated: Optional[datetime] = None


class InfluencerRead(InfluencerBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

# Subscription and billing schemas

class SubscriptionPlanBase(BaseModel):
    name: str
    price: float
    description: Optional[str] = None
    features: Optional[str] = None
    active: Optional[bool] = True
    # Optional Stripe price ID used for payment processing.  Admins can
    # populate this field when creating a plan to tie it to a Stripe price.
    stripe_price_id: Optional[str] = None


class SubscriptionPlanCreate(SubscriptionPlanBase):
    pass


class SubscriptionPlanRead(SubscriptionPlanBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class SubscriptionBase(BaseModel):
    plan_id: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[SubscriptionStatus] = SubscriptionStatus.active


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionRead(SubscriptionBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class LeadBase(BaseModel):
    name: str
    email: EmailStr
    company: Optional[str] = None
    message: Optional[str] = None
    status: Optional[Lead.LeadStatus] = None
    notes: Optional[str] = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    status: Optional[Lead.LeadStatus] = None
    notes: Optional[str] = None


class LeadRead(LeadBase):
    id: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

# Tenant schemas for multi‑tenant support
class TenantBase(BaseModel):
    name: str
    domain: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None

    # Additional white‑label customisation fields.  A tenant can override
    # the default platform branding using these optional settings.
    site_name: Optional[str] = None
    tagline: Optional[str] = None
    footer_message: Optional[str] = None
    features: Optional[str] = None
    custom_css: Optional[str] = None


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None

    # Allow updating white‑label customisation fields.  All fields are
    # optional so clients can supply only those they wish to change.
    site_name: Optional[str] = None
    tagline: Optional[str] = None
    footer_message: Optional[str] = None
    features: Optional[str] = None
    custom_css: Optional[str] = None


class TenantRead(TenantBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }