from sqlalchemy.orm import Session
from app.models.communication import Communication
from app.models.communication_template import CommunicationTemplate
from app.models.circular import Circular
from app.schemas.correspondence import CommunicationCreate, CommunicationTemplateCreate, CircularCreate
from typing import Optional, List
import datetime

# Communications
def create_communication(db: Session, comm_data: CommunicationCreate, institution_id: int, sender_id: int):
    db_comm = Communication(
        institution_id=institution_id,
        sender_id=sender_id,
        channel=comm_data.channel,
        subject=comm_data.subject,
        content=comm_data.content,
        recipient_type=comm_data.recipient_type,
        recipient_filter=comm_data.recipient_filter,
        status="sent" # In a real system, this would trigger background tasks
    )
    db.add(db_comm)
    db.commit()
    db.refresh(db_comm)
    return db_comm

def get_communications(db: Session, institution_id: int):
    return db.query(Communication).filter(Communication.institution_id == institution_id, Communication.deleted_at == None).all()

# Templates
def create_template(db: Session, template_data: CommunicationTemplateCreate, institution_id: int):
    db_template = CommunicationTemplate(
        institution_id=institution_id,
        name=template_data.name,
        description=template_data.description,
        subject_template=template_data.subject_template,
        content_template=template_data.content_template,
        category=template_data.category,
        variables=template_data.variables
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

def get_templates(db: Session, institution_id: int):
    return db.query(CommunicationTemplate).filter(CommunicationTemplate.institution_id == institution_id, CommunicationTemplate.deleted_at == None).all()

# Circulars
def create_circular(db: Session, circular_data: CircularCreate, institution_id: int, posted_by: int):
    db_circular = Circular(
        institution_id=institution_id,
        title=circular_data.title,
        content=circular_data.content,
        attachment_path=circular_data.attachment_path,
        target_audience=circular_data.target_audience,
        posted_by=posted_by,
        expiry_date=circular_data.expiry_date
    )
    db.add(db_circular)
    db.commit()
    db.refresh(db_circular)
    return db_circular

def get_circulars(db: Session, institution_id: int, audience: Optional[str] = None):
    query = db.query(Circular).filter(Circular.institution_id == institution_id, Circular.deleted_at == None)
    # In a real system, we'd filter by JSON audience, but for now just return all
    return query.all()
