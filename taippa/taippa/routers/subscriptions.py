"""Endpoints for subscription plans and subscriptions."""

from __future__ import annotations

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_session
from ..models import SubscriptionPlan, Subscription, User, RoleEnum, SubscriptionStatus
from ..schemas import (
    SubscriptionPlanCreate,
    SubscriptionPlanRead,
    SubscriptionRead,
    SubscriptionCreate,
)
from ..auth import get_current_active_user, require_role

# Optional payment processor integration
import os
try:
    import stripe
except ImportError:
    stripe = None  # Stripe is optional; if not installed payment endpoints will raise


router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/plans", response_model=List[SubscriptionPlanRead])
async def list_plans(
    session: AsyncSession = Depends(get_session),
):
    """Return all active subscription plans."""
    result = await session.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.active == True)
    )
    plans = result.scalars().all()
    return [SubscriptionPlanRead.model_validate(p) for p in plans]


@router.post("/plans", response_model=SubscriptionPlanRead, status_code=status.HTTP_201_CREATED)
async def create_plan(
    plan_in: SubscriptionPlanCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(RoleEnum.admin)),
):
    """Create a new subscription plan.  Admin only."""
    plan = SubscriptionPlan(**plan_in.model_dump(exclude_unset=True))
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return SubscriptionPlanRead.model_validate(plan)


@router.get("/me", response_model=SubscriptionRead | None)
async def get_my_subscription(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Return the current user's active subscription, if any."""
    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.active,
        )
    )
    sub = result.scalars().first()
    if sub:
        return SubscriptionRead.model_validate(sub)
    return None


@router.post("/subscribe", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
async def subscribe_to_plan(
    sub_in: SubscriptionCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Subscribe the current user to a plan.

    If an active subscription already exists it will be cancelled and replaced.
    """
    # verify plan exists and is active
    plan = await session.get(SubscriptionPlan, sub_in.plan_id)
    if not plan or not plan.active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    # cancel existing subscription
    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.active,
        )
    )
    existing = result.scalars().first()
    if existing:
        existing.status = SubscriptionStatus.cancelled
        existing.end_date = datetime.utcnow()
    # create new subscription
    sub = Subscription(
        user_id=current_user.id,
        plan_id=sub_in.plan_id,
        start_date=sub_in.start_date or datetime.utcnow(),
        end_date=sub_in.end_date,
        status=sub_in.status or SubscriptionStatus.active,
        tenant_id=current_user.tenant_id,
    )
    session.add(sub)
    await session.commit()
    await session.refresh(sub)
    return SubscriptionRead.model_validate(sub)


@router.post("/cancel", response_model=SubscriptionRead)
async def cancel_my_subscription(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Cancel the current user's active subscription."""
    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.active,
            Subscription.tenant_id == current_user.tenant_id,
        )
    )
    sub = result.scalars().first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription")
    sub.status = SubscriptionStatus.cancelled
    sub.end_date = datetime.utcnow()
    await session.commit()
    await session.refresh(sub)
    return SubscriptionRead.model_validate(sub)


# Payment integration: create a Stripe checkout session for the given plan.
# This endpoint returns a URL to redirect the user to Stripe for payment.
@router.post("/checkout/{plan_id}")
async def create_checkout_session(
    plan_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Initiate a payment checkout session for a subscription plan.

    The plan must have an associated `stripe_price_id`.  When called, this
    endpoint constructs a Stripe Checkout session in subscription mode for the
    authenticated user.  The client should redirect the user to the returned
    URL to complete payment.  On success the Stripe webhook will activate the
    subscription on our side.
    """
    if stripe is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe library not installed",
        )
    # lookup plan
    db_plan = await session.get(SubscriptionPlan, plan_id)
    if not db_plan or not db_plan.active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if not db_plan.stripe_price_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plan is not configured for payment",
        )
    # configure Stripe API key
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe.api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe secret key not configured",
        )
    # Determine base domain for redirects; default to request's host
    # Use STRIPE_SUCCESS_DOMAIN env var if provided
    domain = os.getenv("STRIPE_SUCCESS_DOMAIN")
    if not domain:
        # derive from request; note: request.url includes path
        base_url = str(request.url).rsplit("/", 1)[0]
        domain = base_url
    try:
        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": db_plan.stripe_price_id, "quantity": 1}],
            customer_email=current_user.email,
            success_url=f"{domain}/pricing.html?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{domain}/pricing.html?cancelled=1",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout session: {e}",
        )
    return {"url": checkout_session.url}


# Stripe webhook endpoint to handle payment events and activate subscriptions.
@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Handle Stripe webhook events.

    This endpoint verifies the Stripe signature and processes checkout
    completion events.  When a subscription is successfully created in
    Stripe, we create a corresponding subscription record in our database
    for the associated user and plan.
    """
    if stripe is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stripe library not installed")
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            # Without a webhook secret we still attempt to parse the JSON
            event = stripe.Event.construct_from(
                stripe.util.json.loads(payload.decode()), stripe.api_key
            )
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload")
    # Handle the checkout.session.completed event
    if event["type"] == "checkout.session.completed":
        session_obj = event["data"]["object"]
        # Extract customer_email and price ID
        customer_email: Optional[str] = session_obj.get("customer_details", {}).get("email") or session_obj.get("customer_email")
        # line_items not available in session; we need to fetch subscription or use metadata
        # We'll attempt to extract from subscription created
        subscription_id = session_obj.get("subscription")
        if customer_email and subscription_id:
            try:
                stripe_sub = stripe.Subscription.retrieve(subscription_id, expand=["items.data.price"])
                price_id = stripe_sub["items"]["data"][0]["price"]["id"]
            except Exception:
                price_id = None
            # find user and plan
            result_user = await session.execute(select(User).where(User.email == customer_email))
            user = result_user.scalars().first()
            result_plan = await session.execute(select(SubscriptionPlan).where(SubscriptionPlan.stripe_price_id == price_id))
            plan = result_plan.scalars().first()
            if user and plan:
                # cancel any existing subscription
                result_sub = await session.execute(
                    select(Subscription).where(Subscription.user_id == user.id, Subscription.status == SubscriptionStatus.active)
                )
                existing = result_sub.scalars().first()
                if existing:
                    existing.status = SubscriptionStatus.cancelled
                    existing.end_date = datetime.utcnow()
                # create new subscription record
                new_sub = Subscription(
                    user_id=user.id,
                    plan_id=plan.id,
                    start_date=datetime.utcnow(),
                    status=SubscriptionStatus.active,
                    tenant_id=user.tenant_id,
                )
                session.add(new_sub)
                await session.commit()
    # Return 200 to acknowledge receipt
    return {"status": "success"}