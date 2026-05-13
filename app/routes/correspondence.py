from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from app.schemas.correspondence import (
    CommunicationCreate, CommunicationResponse,
    CommunicationTemplateCreate, CommunicationTemplateResponse,
    CircularCreate, CircularResponse
)
from app.apis.correspondence import (
    create_communication, get_communications,
    create_template, get_templates,
    create_circular, get_circulars
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole

correspondence_router = APIRouter()

# Communications
@correspondence_router.post("/correspondence/send", response_model=CommunicationResponse, status_code=201)
def send_communication(
    comm_data: CommunicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SECRETARY))
):
    return create_communication(db=db, comm_data=comm_data, institution_id=current_user.institution_id, sender_id=current_user.id)

@correspondence_router.get("/correspondence/history", response_model=List[CommunicationResponse])
def list_communication_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SECRETARY))
):
    return get_communications(db=db, institution_id=current_user.institution_id)

# Templates
@correspondence_router.post("/correspondence/templates", response_model=CommunicationTemplateResponse, status_code=201)
def add_template(
    template_data: CommunicationTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    return create_template(db=db, template_data=template_data, institution_id=current_user.institution_id)

@correspondence_router.get("/correspondence/templates", response_model=List[CommunicationTemplateResponse])
def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SECRETARY))
):
    return get_templates(db=db, institution_id=current_user.institution_id)

# Circulars
@correspondence_router.post("/correspondence/circulars", response_model=CircularResponse, status_code=201)
def add_circular(
    circular_data: CircularCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    return create_circular(db=db, circular_data=circular_data, institution_id=current_user.institution_id, posted_by=current_user.id)

@correspondence_router.get("/correspondence/circulars", response_model=List[CircularResponse])
def list_circulars(
    audience: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    return get_circulars(db=db, institution_id=current_user.institution_id, audience=audience)
