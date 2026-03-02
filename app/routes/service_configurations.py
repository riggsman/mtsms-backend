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
    current_user: User = Depends(
        require_any_role_admin(
            UserRole.ADMIN,
            UserRole.SUPER_ADMIN,
        )
    ),
):
    """
    Create a new service configuration.
    Admin and super_admin only.
    """
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
    current_user: User = Depends(
        require_any_role_admin(
            UserRole.ADMIN,
            UserRole.SUPER_ADMIN,
        )
    ),
):
    """
    Create multiple service configurations at once.
    Admin and super_admin only.
    """
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
    current_user: User = Depends(
        require_any_role_admin(
            UserRole.ADMIN,
            UserRole.SUPER_ADMIN,
        )
    ),
):
    """
    Update service configurations based on service_id and subscription_type.
    Admin and super_admin only.
    """
    updated_configs = []
    
    for config_item in payload.configurations:
        # Get the subscription service to get its name
        subscription_service = (
            db.query(SubscriptionService)
            .filter(
                SubscriptionService.id == config_item.service_id,
                SubscriptionService.deleted_at.is_(None),
            )
            .first()
        )
        
        if not subscription_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription service with ID {config_item.service_id} not found",
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
    
    return updated_configs


@service_configurations.get(
    "/admin/service-configurations",
    response_model=PaginatedResponse[ServiceConfigurationResponse],
    tags=["Service Configurations"],
)
def list_service_configurations(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    tenant_id: Optional[int] = Query(None, description="Filter by tenant ID"),
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
    List service configurations with pagination.
    Admin and super_admin only.
    """
    query = db.query(ServiceConfiguration).filter(
        ServiceConfiguration.deleted_at.is_(None)
    )

    if service_name:
        query = query.filter(ServiceConfiguration.service_name == service_name)
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
