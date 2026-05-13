from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import json
from app.database.base import get_db_session
from app.dependencies.auth import get_current_user, require_any_role_admin
from app.models.user import User
from app.models.role import UserRole
from app.models.service_configuration import ServiceConfiguration
from app.models.subscription_service import SubscriptionService
from app.schemas.service_configuration import (
    ServiceConfigurationRequest,
    ServiceConfigurationResponse,
    ServiceConfigurationBulkRequest,
    ServiceConfigurationUpdateRequest,
    ServiceConfigurationUpdateItem,
)
from app.helpers.pagination import PaginatedResponse
from app.helpers.user_roles import user_is_system_admin

service_configurations = APIRouter()


@service_configurations.post(
    "/admin/service-configurations",
    response_model=ServiceConfigurationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Service Configurations"],
)
def create_service_configuration(
    payload: ServiceConfigurationRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new service configuration.
    System-level only (system_admin / system_super_admin).
    """
    if not user_is_system_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system admin or system super admin can manage service configurations",
        )
    # Check if configuration already exists for this service/key/tenant combination
    query = db.query(ServiceConfiguration).filter(
        ServiceConfiguration.service_name == payload.service_name,
        ServiceConfiguration.configuration_key == payload.configuration_key,
        ServiceConfiguration.deleted_at.is_(None),
    )
    
    if payload.tenant_id:
        query = query.filter(ServiceConfiguration.tenant_id == payload.tenant_id)
    else:
        query = query.filter(ServiceConfiguration.tenant_id.is_(None))
    
    existing = query.first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Configuration '{payload.configuration_key}' already exists for service '{payload.service_name}'",
        )

    # Create new service configuration
    new_config = ServiceConfiguration(
        service_name=payload.service_name,
        configuration_key=payload.configuration_key,
        configuration_value=payload.configuration_value,
        description=payload.description,
        is_active=payload.is_active,
        tenant_id=payload.tenant_id,
    )

    db.add(new_config)
    db.commit()
    db.refresh(new_config)

    return ServiceConfigurationResponse(
        id=new_config.id,
        service_name=new_config.service_name,
        configuration_key=new_config.configuration_key,
        configuration_value=new_config.configuration_value,
        description=new_config.description,
        is_active=new_config.is_active,
        tenant_id=new_config.tenant_id,
        created_at=new_config.created_at,
        updated_at=new_config.updated_at,
    )


@service_configurations.post(
    "/admin/service-configurations/bulk",
    response_model=List[ServiceConfigurationResponse],
    status_code=status.HTTP_201_CREATED,
    tags=["Service Configurations"],
)
def create_bulk_service_configurations(
    payload: ServiceConfigurationBulkRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Create multiple service configurations at once.
    System-level only (system_admin / system_super_admin).
    """
    if not user_is_system_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system admin or system super admin can manage service configurations",
        )
    created_configs = []
    
    for key, value in payload.configurations.items():
        # Check if already exists
        query = db.query(ServiceConfiguration).filter(
            ServiceConfiguration.service_name == payload.service_name,
            ServiceConfiguration.configuration_key == key,
            ServiceConfiguration.deleted_at.is_(None),
        )
        
        if payload.tenant_id:
            query = query.filter(ServiceConfiguration.tenant_id == payload.tenant_id)
        else:
            query = query.filter(ServiceConfiguration.tenant_id.is_(None))
        
        existing = query.first()
        
        if existing:
            # Update existing
            existing.configuration_value = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            existing.description = payload.description
            existing.is_active = True
            db.commit()
            db.refresh(existing)
            created_configs.append(
                ServiceConfigurationResponse(
                    id=existing.id,
                    service_name=existing.service_name,
                    configuration_key=existing.configuration_key,
                    configuration_value=existing.configuration_value,
                    description=existing.description,
                    is_active=existing.is_active,
                    tenant_id=existing.tenant_id,
                    created_at=existing.created_at,
                    updated_at=existing.updated_at,
                )
            )
        else:
            # Create new
            config_value = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            new_config = ServiceConfiguration(
                service_name=payload.service_name,
                configuration_key=key,
                configuration_value=config_value,
                description=payload.description,
                is_active=True,
                tenant_id=payload.tenant_id,
            )
            db.add(new_config)
            db.commit()
            db.refresh(new_config)
            created_configs.append(
                ServiceConfigurationResponse(
                    id=new_config.id,
                    service_name=new_config.service_name,
                    configuration_key=new_config.configuration_key,
                    configuration_value=new_config.configuration_value,
                    description=new_config.description,
                    is_active=new_config.is_active,
                    tenant_id=new_config.tenant_id,
                    created_at=new_config.created_at,
                    updated_at=new_config.updated_at,
                )
            )
    
    return created_configs


@service_configurations.put(
    "/admin/service-configurations",
    response_model=List[ServiceConfigurationResponse],
    tags=["Service Configurations"],
)
def update_service_configurations(
    payload: ServiceConfigurationUpdateRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Update service configurations based on service_id and subscription_type.
    System-level only (system_admin / system_super_admin).

    This endpoint also synchronizes the corresponding flags on the
    SubscriptionService model (`is_freemium_enabled`, `is_premium_enabled`)
    so the service table reflects the current availability.

    Accepts both numeric service IDs and button IDs from serviceButtons.js.
    When a button ID is passed (e.g., "quick_pay_fees"), it will
    look up the corresponding SubscriptionService by name.
    """
    if not user_is_system_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system admin or system super admin can manage service configurations",
        )
    updated_configs = []

    for config_item in payload.configurations:
        # --- Resolve the subscription service ---
        subscription_service = None

        # Try to interpret service_id as integer (numeric ID)
        try:
            service_id_int = int(config_item.service_id)
            subscription_service = (
                db.query(SubscriptionService)
                .filter(
                    SubscriptionService.id == service_id_int,
                    SubscriptionService.deleted_at.is_(None),
                )
                .first()
            )
        except (ValueError, TypeError):
            # Not an integer → treat as button ID (string)
            pass

        # If not found by numeric ID, try to find by button ID (service name)
        if not subscription_service:
            # The button ID might be stored as service_name in SubscriptionService
            subscription_service = (
                db.query(SubscriptionService)
                .filter(
                    SubscriptionService.name == config_item.service_id,
                    SubscriptionService.deleted_at.is_(None),
                )
                .first()
            )

        if not subscription_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription service with ID '{config_item.service_id}' not found",
            )

        # Use subscription service name as service_name
        service_name = subscription_service.name

        # Use subscription_type as configuration_key
        configuration_key = f"subscription_type_{config_item.subscription_type}"

        # Store is_enabled as configuration_value (as JSON boolean string)
        configuration_value = json.dumps({"is_enabled": config_item.is_enabled})

        # Check if configuration already exists
        query = db.query(ServiceConfiguration).filter(
            ServiceConfiguration.service_name == service_name,
            ServiceConfiguration.configuration_key == configuration_key,
            ServiceConfiguration.deleted_at.is_(None),
        )

        existing = query.first()

        if existing:
            # Update existing configuration
            existing.configuration_value = configuration_value
            existing.is_active = config_item.is_enabled
            db.add(existing)
            db.commit()
            db.refresh(existing)
            updated_configs.append(
                ServiceConfigurationResponse(
                    id=existing.id,
                    service_name=existing.service_name,
                    configuration_key=existing.configuration_key,
                    configuration_value=existing.configuration_value,
                    description=existing.description,
                    is_active=existing.is_active,
                    tenant_id=existing.tenant_id,
                    created_at=existing.created_at,
                    updated_at=existing.updated_at,
                )
            )
        else:
            # Create new configuration
            new_config = ServiceConfiguration(
                service_name=service_name,
                configuration_key=configuration_key,
                configuration_value=configuration_value,
                description=f"Subscription type: {config_item.subscription_type}",
                is_active=config_item.is_enabled,
                tenant_id=None,  # Global config
            )
            db.add(new_config)
            db.commit()
            db.refresh(new_config)
            updated_configs.append(
                ServiceConfigurationResponse(
                    id=new_config.id,
                    service_name=new_config.service_name,
                    configuration_key=new_config.configuration_key,
                    configuration_value=new_config.configuration_value,
                    description=new_config.description,
                    is_active=new_config.is_active,
                    tenant_id=new_config.tenant_id,
                    created_at=new_config.created_at,
                    updated_at=new_config.updated_at,
                )
            )

        # --- Synchronize flags on SubscriptionService itself ---
        # If subscription_type == 'freemium' or 'premium', update respective flag.
        if config_item.subscription_type.lower() == "freemium":
            subscription_service.is_freemium_enabled = config_item.is_enabled
        elif config_item.subscription_type.lower() == "premium":
            subscription_service.is_premium_enabled = config_item.is_enabled

        db.add(subscription_service)
        db.commit()
        db.refresh(subscription_service)

    return updated_configs


@service_configurations.get(
    "/admin/service-configurations",
    response_model=PaginatedResponse[ServiceConfigurationResponse],
    tags=["Service Configurations"],
)
def list_service_configurations(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000),
    service_name: Optional[str] = Query(None, description="Filter by service name or button ID"),
    tenant_id: Optional[int] = Query(None, description="Filter by tenant ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    List service configurations with pagination.
    System-level only (system_admin / system_super_admin).
    
    Supports filtering by service_name (which can be a button ID from serviceButtons.js).
    """
    if not user_is_system_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system admin or system super admin can list service configurations",
        )
    query = db.query(ServiceConfiguration).filter(
        ServiceConfiguration.deleted_at.is_(None)
    )
    
    if service_name:
        # Allow filtering by service name OR button ID (which is stored in configuration_key)
        query = query.filter(
            (ServiceConfiguration.service_name == service_name) |
            (ServiceConfiguration.configuration_key == service_name)
        )
    if tenant_id is not None:
        query = query.filter(ServiceConfiguration.tenant_id == tenant_id)
    if is_active is not None:
        query = query.filter(ServiceConfiguration.is_active == is_active)
    
    total = query.count()
    configs = (
        query.order_by(ServiceConfiguration.service_name, ServiceConfiguration.configuration_key)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    
    result_configs = [
        ServiceConfigurationResponse(
            id=config.id,
            service_name=config.service_name,
            configuration_key=config.configuration_key,
            configuration_value=config.configuration_value,
            description=config.description,
            is_active=config.is_active,
            tenant_id=config.tenant_id,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )
        for config in configs
    ]
    
    return PaginatedResponse.create(
        items=result_configs,
        total=total,
        page=page,
        page_size=page_size,
    )


@service_configurations.get(
    "/tenant/check-service-access",
    tags=["Service Configurations"],
)
def check_service_access_for_tenant(
    service_name: str = Query(..., description="Name of the service or button ID to check access for"),
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Public tenant endpoint used by the student UI to check if a given
    service is currently enabled (freemium or premium) in the admin
    subscription management screen.

    Accepts either:
    - A service name (e.g., "Download Results")
    - A button ID from serviceButtons.js (e.g., "quick_pay_fees")
    
    For now this checks global configuration only and does not
    differentiate per-tenant subscription plans – if the service is
    enabled for *any* subscription type, students can use it.
    """
    # First try to find by service name
    subscription_service = (
        db.query(SubscriptionService)
        .filter(
            SubscriptionService.name == service_name,
            SubscriptionService.deleted_at.is_(None),
        )
        .first()
    )
    
    # If not found by name, try to find by button ID in configuration_key
    if not subscription_service:
        config_by_id = (
            db.query(ServiceConfiguration)
            .filter(
                ServiceConfiguration.configuration_key == service_name,
                ServiceConfiguration.deleted_at.is_(None),
            )
            .first()
        )
        if config_by_id:
            # Get the subscription service by name from the config
            subscription_service = (
                db.query(SubscriptionService)
                .filter(
                    SubscriptionService.name == config_by_id.service_name,
                    SubscriptionService.deleted_at.is_(None),
                )
                .first()
            )
    
    if not subscription_service:
        # Service not defined → no access
        return {"service_name": service_name, "has_access": False}

    # Look for any active configuration entries for this service
    configs = (
        db.query(ServiceConfiguration)
        .filter(
            ServiceConfiguration.service_name == subscription_service.name,
            ServiceConfiguration.configuration_key.in_(
                ["subscription_type_freemium", "subscription_type_premium"]
            ),
            ServiceConfiguration.deleted_at.is_(None),
        )
        .all()
    )
    
    has_access = False
    # Base amount comes from the SubscriptionService "price" field
    amount = None
    if subscription_service.price is not None:
        try:
            amount = float(subscription_service.price)
        except (TypeError, ValueError):
            amount = None
    
    # Track whether freemium is enabled and any configured max free downloads
    is_freemium_enabled = False
    max_free_download = None
    
    for cfg in configs:
        # configuration_value is stored as JSON string like {"is_enabled": true}
        try:
            value = json.loads(cfg.configuration_value) if cfg.configuration_value else {}
        except Exception:
            value = {}
        
        is_enabled = bool(value.get("is_enabled", cfg.is_active))
        
        if is_enabled:
            has_access = True
            
            # If this is the freemium configuration, read max_free_download if provided
            if cfg.configuration_key == "subscription_type_freemium":
                is_freemium_enabled = True
                raw_max_free = value.get("max_free_download")
                try:
                    if raw_max_free is not None:
                        max_free_download = int(raw_max_free)
                except (TypeError, ValueError):
                    max_free_download = None
    
    response = {
        "service_name": service_name,
        "has_access": has_access,
    }
    
    # Only include amount if we successfully parsed a number
    if amount is not None:
        response["amount"] = amount
    
    # Include freemium/max-free metadata if available
    if is_freemium_enabled:
        response["is_freemium_enabled"] = True
    if max_free_download is not None:
        response["max_free_download"] = max_free_download
    
    return response
