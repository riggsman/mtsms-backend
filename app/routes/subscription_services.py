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
from app.helpers.user_roles import user_is_system_admin

subscription_services = APIRouter()


def _update_service_from_payload(service: SubscriptionService, payload: SubscriptionServiceRequest) -> None:
    """
    Apply incoming request fields to an existing SubscriptionService instance.
    Shared between create and update handlers.
    """
    service.name = payload.name
    service.description = payload.description
    service.price = payload.price
    service.currency = payload.currency
    service.billing_period = payload.billing_period
    service.is_active = payload.is_active
    # Safely read freemium/premium flags from the request; default to False
    service.is_freemium_enabled = bool(getattr(payload, "freemium_enabled", False) or False)
    service.is_premium_enabled = bool(getattr(payload, "premium_enabled", False) or False)

    # Convert features dict to JSON string for storage.
    # If no explicit features are provided, default to using the
    # service name as the key so it matches the element name used
    # in the student Academics UI and service configuration.
    features_payload = payload.features
    if features_payload is None:
        # e.g. {"Download Results": {"enabled": True}}
        features_payload = {payload.name: {"enabled": True}}

    service.features = json.dumps(features_payload)


@subscription_services.post(
    "/admin/subscription-services",
    response_model=SubscriptionServiceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Subscription Services"],
)
def create_subscription_service(
    payload: SubscriptionServiceRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new subscription service.
    System-level only (system_admin / system_super_admin).
    """
    # Authorize system_xxxx roles similar to system_settings APIs
    if not user_is_system_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system admin or system super admin can manage subscription services",
        )
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

    # Validate features format early
    if payload.features:
        try:
            json.dumps(payload.features)
        except (TypeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid features format: {str(e)}",
            )

    # Create new subscription service
    new_service = SubscriptionService()
    _update_service_from_payload(new_service, payload)

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
        freemium_enabled=new_service.is_freemium_enabled,
        premium_enabled=new_service.is_premium_enabled,
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
    page_size: int = Query(10, ge=1, le=1000),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    List subscription services with pagination.
    System-level only (system_admin / system_super_admin).
    """
    if not user_is_system_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system admin or system super admin can list subscription services",
        )
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
                freemium_enabled=getattr(service, "is_freemium_enabled", False),
                premium_enabled=getattr(service, "is_premium_enabled", False),
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


@subscription_services.put(
    "/admin/subscription-services/{service_id}",
    response_model=SubscriptionServiceResponse,
    tags=["Subscription Services"],
)
def update_subscription_service(
    service_id: int,
    payload: SubscriptionServiceRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Update an existing subscription service (including freemium/premium flags).
    System-level only (system_admin / system_super_admin).
    """
    if not user_is_system_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system admin or system super admin can manage subscription services",
        )
    service: Optional[SubscriptionService] = (
        db.query(SubscriptionService)
        .filter(
            SubscriptionService.id == service_id,
            SubscriptionService.deleted_at.is_(None),
        )
        .first()
    )

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription service with ID {service_id} not found",
        )

    # Validate billing period
    valid_periods = ["monthly", "yearly", "one-time"]
    if payload.billing_period not in valid_periods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Billing period must be one of: {', '.join(valid_periods)}",
        )

    # Validate features format early
    if payload.features:
        try:
            json.dumps(payload.features)
        except (TypeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid features format: {str(e)}",
            )

    # Apply updates
    _update_service_from_payload(service, payload)

    db.add(service)
    db.commit()
    db.refresh(service)

    # Parse features back to dict for response
    features_dict = None
    if service.features:
        try:
            features_dict = json.loads(service.features)
        except (json.JSONDecodeError, TypeError):
            features_dict = None

    return SubscriptionServiceResponse(
        id=service.id,
        name=service.name,
        description=service.description,
        price=service.price,
        currency=service.currency,
        billing_period=service.billing_period,
        is_active=service.is_active,
        freemium_enabled=service.is_freemium_enabled,
        premium_enabled=service.is_premium_enabled,
        features=features_dict,
        created_at=service.created_at,
        updated_at=service.updated_at,
    )
