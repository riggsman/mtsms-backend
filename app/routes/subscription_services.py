from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
import json
from app.database.base import get_db_session
from app.dependencies.auth import get_current_user, require_any_role_admin
from app.models.user import User
from app.models.role import UserRole
from app.models.subscription_service import SubscriptionService
from app.schemas.subscription_service import (
    SubscriptionServiceRequest,
    SubscriptionServiceResponse,
)
from app.helpers.pagination import PaginatedResponse

subscription_services = APIRouter()


@subscription_services.post(
    "/admin/subscription-services",
    response_model=SubscriptionServiceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Subscription Services"],
)
def create_subscription_service(
    payload: SubscriptionServiceRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(
        require_any_role_admin(
            UserRole.ADMIN,
            UserRole.SUPER_ADMIN,
        )
    ),
):
    """
    Create a new subscription service.
    Admin and super_admin only.
    """
    # Check if service name already exists
    existing = (
        db.query(SubscriptionService)
        .filter(
            SubscriptionService.name == payload.name,
            SubscriptionService.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Subscription service with name '{payload.name}' already exists",
        )

    # Validate billing period
    valid_periods = ["monthly", "yearly", "one-time"]
    if payload.billing_period not in valid_periods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Billing period must be one of: {', '.join(valid_periods)}",
        )

    # Convert features dict to JSON string for storage
    features_json = None
    if payload.features:
        try:
            features_json = json.dumps(payload.features)
        except (TypeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid features format: {str(e)}",
            )

    # Create new subscription service
    new_service = SubscriptionService(
        name=payload.name,
        description=payload.description,
        price=payload.price,
        currency=payload.currency,
        billing_period=payload.billing_period,
        is_active=payload.is_active,
        features=features_json,
    )

    db.add(new_service)
    db.commit()
    db.refresh(new_service)

    # Parse features back to dict for response
    features_dict = None
    if new_service.features:
        try:
            features_dict = json.loads(new_service.features)
        except (json.JSONDecodeError, TypeError):
            features_dict = None

    return SubscriptionServiceResponse(
        id=new_service.id,
        name=new_service.name,
        description=new_service.description,
        price=new_service.price,
        currency=new_service.currency,
        billing_period=new_service.billing_period,
        is_active=new_service.is_active,
        features=features_dict,
        created_at=new_service.created_at,
        updated_at=new_service.updated_at,
    )


@subscription_services.get(
    "/admin/subscription-services",
    response_model=PaginatedResponse[SubscriptionServiceResponse],
    tags=["Subscription Services"],
)
def list_subscription_services(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db_session),
    current_user: User = Depends(
        require_any_role_admin(
            UserRole.ADMIN,
            UserRole.SUPER_ADMIN,
        )
    ),
):
    """
    List subscription services with pagination.
    Admin and super_admin only.
    """
    query = db.query(SubscriptionService).filter(
        SubscriptionService.deleted_at.is_(None)
    )

    if is_active is not None:
        query = query.filter(SubscriptionService.is_active == is_active)

    total = query.count()
    services = (
        query.order_by(SubscriptionService.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Parse features JSON for each service
    result_services = []
    for service in services:
        features_dict = None
        if service.features:
            try:
                features_dict = json.loads(service.features)
            except (json.JSONDecodeError, TypeError):
                features_dict = None

        result_services.append(
            SubscriptionServiceResponse(
                id=service.id,
                name=service.name,
                description=service.description,
                price=service.price,
                currency=service.currency,
                billing_period=service.billing_period,
                is_active=service.is_active,
                features=features_dict,
                created_at=service.created_at,
                updated_at=service.updated_at,
            )
        )

    return PaginatedResponse.create(
        items=result_services,
        total=total,
        page=page,
        page_size=page_size,
    )
