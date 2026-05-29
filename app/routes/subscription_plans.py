import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database.base import get_db_session as get_db
from app.models.subscription_plan import SubscriptionPlan
from app.schemas.subscription_plan import (
    SubscriptionPlanCreate,
    SubscriptionPlanResponse,
    SubscriptionPlanUpdate,
)

router = APIRouter()

DEFAULT_PLANS = [
    {
        "name": "Freemium",
        "description": "Free tier with basic features",
        "price": 0,
        "billing_period": "monthly",
        "is_active": True,
        "features": json.dumps(["Basic features", "Email support"]),
    },
    {
        "name": "Premium",
        "description": "Full access to all features",
        "price": 99,
        "billing_period": "monthly",
        "is_active": True,
        "features": json.dumps(
            ["All features", "Priority support", "Advanced analytics"]
        ),
    },
]


def _seed_default_plans(db: Session) -> None:
    for row in DEFAULT_PLANS:
        existing = (
            db.query(SubscriptionPlan)
            .filter(SubscriptionPlan.name == row["name"])
            .first()
        )
        if existing:
            continue
        db.add(SubscriptionPlan(**row))
    db.commit()


def ensure_default_subscription_plans(db: Session) -> None:
    """Idempotent seed used on startup and when the catalog is empty."""
    _seed_default_plans(db)


def _active_filter(query):
    return query.filter(
        or_(
            SubscriptionPlan.is_active.is_(True),
            SubscriptionPlan.is_active.is_(None),
        )
    )


@router.get(
    "/admin/subscription-plans",
    response_model=List[SubscriptionPlanResponse],
)
def list_subscription_plans(
    active_only: bool = Query(False, description="When true, return only active plans"),
    seed_if_empty: bool = Query(
        True, description="Seed Freemium/Premium when the catalog is empty"
    ),
    db: Session = Depends(get_db),
):
    """List subscription plans for admin UI and tenant onboarding."""
    query = db.query(SubscriptionPlan)
    if active_only:
        query = _active_filter(query)

    plans = query.order_by(SubscriptionPlan.price.asc()).all()
    if not plans and seed_if_empty:
        ensure_default_subscription_plans(db)
        query = db.query(SubscriptionPlan)
        if active_only:
            query = _active_filter(query)
        plans = query.order_by(SubscriptionPlan.price.asc()).all()

    return plans


@router.post(
    "/admin/subscription-plans",
    response_model=SubscriptionPlanResponse,
)
def create_subscription_plan(
    payload: SubscriptionPlanCreate,
    db: Session = Depends(get_db),
):
    """Create a new subscription plan."""
    name = payload.name.strip()
    existing = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Plan with this name already exists")
    plan = SubscriptionPlan(
        name=name,
        price=payload.price,
        billing_period=payload.billing_period,
        description=payload.description,
        features=payload.features,
        is_active=payload.is_active,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.put(
    "/admin/subscription-plans/{plan_id}",
    response_model=SubscriptionPlanResponse,
)
def update_subscription_plan(
    plan_id: int,
    payload: SubscriptionPlanUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing subscription plan."""
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        data["name"] = data["name"].strip()
        conflict = (
            db.query(SubscriptionPlan)
            .filter(
                SubscriptionPlan.name == data["name"],
                SubscriptionPlan.id != plan_id,
            )
            .first()
        )
        if conflict:
            raise HTTPException(status_code=400, detail="Plan with this name already exists")

    for key, value in data.items():
        setattr(plan, key, value)

    db.commit()
    db.refresh(plan)
    return plan
