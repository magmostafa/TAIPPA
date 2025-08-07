"""Database models for TAIPPA.

These ORM classes define the persistent data structures used by the platform.
The models are deliberately kept simple in this skeleton; additional fields
should be added as needed to support the full feature set described in the
specification.

SQLAlchemy 2.0 type annotations are used throughout to provide static typing
and clarity.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, String, Text, DateTime, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


# ---------------------------------------------------------------------------
# Tenancy and User Models
# ---------------------------------------------------------------------------

class Tenant(Base):
    """Represents an isolated client environment. All users and data objects
    belong to a tenant, enabling data isolation and customisation.
    """

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(
        String(length=36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(length=100), unique=True)
    domain: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String(length=20), nullable=True)
    secondary_color: Mapped[str | None] = mapped_column(String(length=20), nullable=True)

    # Enterprise white‑label customisation fields
    site_name: Mapped[str | None] = mapped_column(String(length=100), nullable=True)
    tagline: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    footer_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    features: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_css: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 default=datetime.utcnow,
                                                 onupdate=datetime.utcnow)

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="tenant", cascade="all, delete-orphan"
    )
    brands: Mapped[list["Brand"]] = relationship(
        "Brand", back_populates="tenant", cascade="all, delete-orphan"
    )
    campaigns: Mapped[list["Campaign"]] = relationship(
        "Campaign", back_populates="tenant", cascade="all, delete-orphan"
    )
    influencers: Mapped[list["Influencer"]] = relationship(
        "Influencer", back_populates="tenant", cascade="all, delete-orphan"
    )
    leads: Mapped[list["Lead"]] = relationship(
        "Lead", back_populates="tenant", cascade="all, delete-orphan"
    )


class RoleEnum(str, enum.Enum):
    """Enumeration of user roles."""

    admin = "admin"
    client = "client"
    team_member = "team_member"
    viewer = "viewer"


class User(Base):
    """Represents a user of the TAIPPA platform."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(length=36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(length=320), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(length=255))
    full_name: Mapped[str | None] = mapped_column(String(length=100), nullable=True)
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), default=RoleEnum.client)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")

    # relationships
    brands: Mapped[list["Brand"]] = relationship(
        "Brand", back_populates="owner", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Brand & Campaign Models
# ---------------------------------------------------------------------------

class Brand(Base):
    """Represents a brand profile within the system."""

    __tablename__ = "brands"

    id: Mapped[str] = mapped_column(
        String(length=36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(length=100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(String(length=100), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(length=320), nullable=True)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    owner: Mapped["User"] = relationship("User", back_populates="brands")
    campaigns: Mapped[list["Campaign"]] = relationship(
        "Campaign", back_populates="brand", cascade="all, delete-orphan"
    )

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="brands")


class CampaignStatus(str, enum.Enum):
    """Enumerates possible campaign states."""

    draft = "draft"
    active = "active"
    paused = "paused"
    completed = "completed"
    archived = "archived"


class Campaign(Base):
    """Represents an influencer marketing campaign."""

    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(
        String(length=36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), index=True)
    title: Mapped[str] = mapped_column(String(length=150))
    brief: Mapped[str] = mapped_column(Text)
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus), default=CampaignStatus.draft
    )
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),
                                                        nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),
                                                      nullable=True)
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    analysis: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    brand: Mapped["Brand"] = relationship("Brand", back_populates="campaigns")

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="campaigns")


# ---------------------------------------------------------------------------
# Influencer & Subscription Models
# ---------------------------------------------------------------------------

class Influencer(Base):
    """Represents an influencer profile in the system."""

    __tablename__ = "influencers"

    id: Mapped[str] = mapped_column(
        String(length=36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    handle: Mapped[str] = mapped_column(String(length=100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(length=100))
    platform: Mapped[str] = mapped_column(String(length=50))
    followers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    engagement_rate: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Enrichment fields
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    topics: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(String(length=100), nullable=True)
    language: Mapped[str | None] = mapped_column(String(length=50), nullable=True)
    avg_likes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_comments: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audience_country: Mapped[str | None] = mapped_column(String(length=100),
                                                         nullable=True)
    audience_gender: Mapped[str | None] = mapped_column(String(length=50),
                                                        nullable=True)
    audience_age: Mapped[str | None] = mapped_column(String(length=100),
                                                     nullable=True)
    last_updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),
                                                          nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="influencers")


class SubscriptionStatus(str, enum.Enum):
    """Possible states for a subscription."""

    active = "active"
    cancelled = "cancelled"


class SubscriptionPlan(Base):
    """Represents a subscription plan offered to users."""

    __tablename__ = "subscription_plans"

    id: Mapped[str] = mapped_column(
        String(length=36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(length=100), unique=True)
    price: Mapped[float] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    features: Mapped[str | None] = mapped_column(Text, nullable=True)
    stripe_price_id: Mapped[str | None] = mapped_column(String(length=100),
                                                        nullable=True)
    active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Subscription(Base):
    """Represents a user's subscription to a plan."""

    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(
        String(length=36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("subscription_plans.id"),
                                         index=True)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 default=datetime.utcnow)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),
                                                      nullable=True)
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.active
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Link subscription to tenant via the user (subscriptions belong to a tenant)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    tenant: Mapped["Tenant"] = relationship("Tenant")


# ---------------------------------------------------------------------------
# Lead Models
# ---------------------------------------------------------------------------

class LeadStatus(str, enum.Enum):
    """Lead statuses for the sales pipeline."""

    new = "new"
    contacted = "contacted"
    qualified = "qualified"
    won = "won"
    lost = "lost"


class Lead(Base):
    """Represents a marketing lead captured from the website."""

    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(
        String(length=36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(length=100))
    email: Mapped[str] = mapped_column(String(length=320))
    company: Mapped[str | None] = mapped_column(String(length=100), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus), default=LeadStatus.new
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="leads")
