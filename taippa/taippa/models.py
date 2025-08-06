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

# New model for multi‑tenant support.  A tenant represents an isolated client
# environment within the TAIPPA platform.  All user accounts and data
# objects belong to a tenant, enabling data isolation and customisation.
class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(
        String(length=36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(length=100), unique=True)
    domain: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String(length=20), nullable=True)
    secondary_color: Mapped[str | None] = mapped_column(String(length=20), nullable=True)

    # Enterprise white‑label customisation fields.  These optional fields allow
    # tenants to configure the appearance and messaging of their instance of
    # TAIPPA.  They can override the site name displayed in navigation bars,
    # define a tagline shown on landing pages, specify a custom footer message
    # and provide arbitrary feature flags or settings encoded as JSON.  A
    # tenant can also supply custom CSS to further tweak the look and feel.
    site_name: Mapped[str | None] = mapped_column(String(length=100), nullable=True)
    tagline: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    footer_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    features: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_css: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

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
    """Enumeration of user roles.

    The system defines several built‑in roles: `admin` (full access), `client`
    (owns brands and campaigns), `team_member` (collaborates on campaigns) and
    `viewer` (read‑only access).
    """

    admin = "admin"
    client = "client"
    team_member = "team_member"
    viewer = "viewer"


class User(Base):
    """Represents a user of the TAIPPA platform.

    Users authenticate via username/email and password.  A hashed password is
    stored, not the plain text.  Each user has one or more roles which
    determine their permissions within the system.
    """

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
    # tenant relationship: each user belongs to a tenant, enabling multi‑tenant
    # data isolation.  Clients may have their own tenant while super admins can
    # manage multiple tenants.
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")

    # relationships
    brands: Mapped[list[Brand]] = relationship(
        "Brand", back_populates="owner", cascade="all, delete-orphan"
    )


class Brand(Base):
    """Represents a brand profile within the system.

    Brands belong to clients and can be associated with multiple campaigns.
    A brand holds metadata about the company's identity and target audience.
    """

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

    # relationships
    owner: Mapped[User] = relationship("User", back_populates="brands")
    campaigns: Mapped[list[Campaign]] = relationship(
        "Campaign", back_populates="brand", cascade="all, delete-orphan"
    )

    # Multi‑tenant: link brand to tenant for isolation
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
    """Represents an influencer marketing campaign.

    Campaigns belong to brands and can have multiple milestones and metrics.  The
    `brief` field stores the free‑form brief provided by the client, while
    `analysis` stores the structured analysis generated by the AI engine.
    """

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
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # relationships
    brand: Mapped[Brand] = relationship("Brand", back_populates="campaigns")

    # Multi‑tenant: link campaign to tenant for isolation
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="campaigns")


class Influencer(Base):
    """Represents an influencer profile in the system.

    In a full implementation this model would include social media metrics,
    engagement statistics, pricing, and historical collaboration data.  Only a
    handful of fields are defined here for demonstration purposes.
    """

    __tablename__ = "influencers"

    id: Mapped[str] = mapped_column(
        String(length=36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    handle: Mapped[str] = mapped_column(String(length=100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(length=100))
    platform: Mapped[str] = mapped_column(String(length=50))
    followers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    engagement_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Additional enrichment fields.  These fields are populated by the influencer
    # discovery and enrichment pipeline to provide deeper insights and
    # filtering capabilities.  All fields are optional because data may not
    # be available for every influencer.
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    topics: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(String(length=100), nullable=True)
    language: Mapped[str | None] = mapped_column(String(length=50), nullable=True)
    avg_likes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_comments: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audience_country: Mapped[str | None] = mapped_column(String(length=100), nullable=True)
    audience_gender: Mapped[str | None] = mapped_column(String(length=50), nullable=True)
    audience_age: Mapped[str | None] = mapped_column(String(length=100), nullable=True)
    last_updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Multi‑tenant: link influencer to tenant for isolation
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="influencers")


# New models for subscription billing and lead capture

class SubscriptionStatus(str, enum.Enum):
    """Possible states for a subscription."""

    active = "active"
    cancelled = "cancelled"


class SubscriptionPlan(Base):
    """Represents a subscription plan offered to users.

    Plans define pricing and feature sets.  Users subscribe to a single plan at a time.
    """

    __tablename__ = "subscription_plans"

    id: Mapped[str] = mapped_column(
        String(length=36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(length=100), unique=True)
    price: Mapped[float] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    features: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Stripe price identifier used for billing.  This field stores the ID of the
    # corresponding price object in Stripe.  When integrating with a payment
    # gateway you can create products and prices in Stripe's dashboard and
    # reference the price ID here.  The backend uses this ID when initiating
    # checkout sessions.
    stripe_price_id: Mapped[str | None] = mapped_column(String(length=100), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Subscription(Base):
    """Represents a user's subscription to a plan.

    A subscription links a user to a plan and records start/end dates and status.
    """

    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(
        String(length=36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("subscription_plans.id"), index=True)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.active
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Multi‑tenant: link subscription to tenant for isolation.  Although plans may be
    # global, subscriptions belong to a tenant via the user.
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    tenant: Mapped["Tenant"] = relationship("Tenant")


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
    # lead status for sales pipeline
    class LeadStatus(str, enum.Enum):
        new = "new"
        contacted = "contacted"
        qualified = "qualified"
        won = "won"
        lost = "lost"

    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus), default=LeadStatus.new
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Multi‑tenant: link lead to tenant for isolation
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="leads")