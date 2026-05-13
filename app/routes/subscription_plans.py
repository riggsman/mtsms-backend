from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.base import get_db_session as get_db
from app.models.subscription_plan import SubscriptionPlan
from typing import List

router = APIRouter()


@router.get("/admin/subscription-plans")
def list_subscription_plans(db: Session = Depends(get_db)):
    """List all active subscription plans."""
    plans = (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.is_active == True)
        .order_by(SubscriptionPlan.price.asc())
        .all()
    )
    return plans


@router.post("/admin/subscription-plans")
def create_subscription_plan(
    name: str,
    price: float = 0,
    billing_period: str = "monthly",
    description: str = None,
    features: str = None,
    db: Session = Depends(get_db),
):
    """Create a new subscription plan."""
    existing = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Plan with this name already exists")
    plan = SubscriptionPlan(
        name=name,
        price=price,
        billing_period=billing_period,
        description=description,
        features=features,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.put("/admin/subscription-plans/{plan_id}")
def update_subscription_plan(
    plan_id: int,
    name: str = None,
    price: float = None,
    billing_period: str = None,
    description: str = None,
    features: str = None,
    is_active: bool = None,
    db: Session = Depends(get_db),
):
    """Update an existing subscription plan."""
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if name is not None:
        plan.name = name
    if price is not None:
        plan.price = price
    if billing_period is not None:
        plan.billing_period = billing_period
    if description is not None:
        plan.description = description
    if features is not None:
        plan.features = features
    if is_active is not None:
        plan.is_active = is_active
    db.commit()
    db.refresh(plan)
    return plan
