from sqlalchemy.orm import Session
from typing import Optional
from app.models.tenant_settings import TenantSettings
from app.schemas.tenant_settings import TenantSettingsRequest, TenantSettingsResponse, MatriculeFormatConfig
from app.exceptions import NotFoundError, ValidationError
import json
import datetime

def get_tenant_settings(db: Session, institution_id: int) -> Optional[TenantSettings]:
    """Get tenant settings by institution_id"""
    return db.query(TenantSettings).filter(
        TenantSettings.institution_id == institution_id
    ).first()

def create_or_update_tenant_settings(
    db: Session, 
    institution_id: int, 
    settings: TenantSettingsRequest
) -> TenantSettings:
    """Create or update tenant settings"""
    existing = get_tenant_settings(db, institution_id)
    
    # Prepare matricule_format as JSON
    matricule_format_json = None
    if settings.matricule_format:
        # Convert to dict for JSON storage
        matricule_format_dict = settings.matricule_format.dict()
        matricule_format_json = json.dumps(matricule_format_dict)
    
    if existing:
        # Update existing settings
        if settings.matricule_format:
            existing.matricule_format = matricule_format_json
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new settings
        new_settings = TenantSettings(
            institution_id=institution_id,
            matricule_format=matricule_format_json
        )
        db.add(new_settings)
        db.commit()
        db.refresh(new_settings)
        return new_settings

def is_matricule_format_configured(db: Session, institution_id: int) -> bool:
    """Check if matricule format is configured for the tenant"""
    settings = get_tenant_settings(db, institution_id)
    if not settings or not settings.matricule_format:
        return False
    
    try:
        format_config = json.loads(settings.matricule_format)
        return format_config.get('is_configured', False) and len(format_config.get('segments', [])) == 4
    except (json.JSONDecodeError, TypeError):
        return False

def generate_student_id(db: Session, institution_id: int, student_data: dict) -> str:
    """
    Generate student ID based on configured matricule format
    
    Args:
        db: Database session
        institution_id: Institution ID
        student_data: Dictionary containing student data (class_id, academic_year, etc.)
    
    Returns:
        Generated student ID string
    """
    settings = get_tenant_settings(db, institution_id)
    
    if not settings or not settings.matricule_format:
        raise ValidationError(
            "Matricule format is not configured. Please configure it in Tenant Settings before creating students."
        )
    
    try:
        format_config = json.loads(settings.matricule_format)
        segments = format_config.get('segments', [])
        
        if not format_config.get('is_configured', False) or len(segments) != 4:
            raise ValidationError(
                "Matricule format is not properly configured. Please configure all 4 segments in Tenant Settings."
            )
        
        generated_id_parts = []
        
        for segment in segments:
            seg_type = segment.get('type', 'constant')
            separator = segment.get('separator', '')
            
            if seg_type == 'constant':
                value = segment.get('value', '')
                generated_id_parts.append(value)
            elif seg_type == 'variable':
                pattern = segment.get('pattern', 'sequence')
                length = segment.get('length', 4)
                
                if pattern == 'year':
                    # Use current year or academic year
                    year = student_data.get('academic_year', datetime.datetime.now().year)
                    value = str(year)[-2:] if length == 2 else str(year)
                    generated_id_parts.append(value.zfill(length))
                
                elif pattern == 'sequence':
                    # Get next sequence number for this institution
                    from app.models.student import Student
                    last_student = db.query(Student).filter(
                        Student.institution_id == institution_id,
                        Student.deleted_at.is_(None)
                    ).order_by(Student.id.desc()).first()
                    
                    next_seq = 1
                    if last_student:
                        # Try to extract sequence from last student_id
                        try:
                            # Simple approach: get last numeric part
                            import re
                            numbers = re.findall(r'\d+', last_student.student_id)
                            if numbers:
                                next_seq = int(numbers[-1]) + 1
                        except (ValueError, AttributeError):
                            next_seq = 1
                    
                    generated_id_parts.append(str(next_seq).zfill(length))
                
                elif pattern == 'class_code':
                    # Use class code if available
                    class_id = student_data.get('class_id')
                    if class_id:
                        from app.models.classes import Class
                        class_obj = db.query(Class).filter(Class.id == class_id).first()
                        if class_obj and class_obj.code:
                            value = class_obj.code[:length]
                            generated_id_parts.append(value.ljust(length, '0')[:length])
                        else:
                            generated_id_parts.append('0' * length)
                    else:
                        generated_id_parts.append('0' * length)
                
                elif pattern == 'department_code':
                    # Use department code if available
                    department_id = student_data.get('department_id')
                    if department_id:
                        from app.models.department import Department
                        dept = db.query(Department).filter(Department.id == department_id).first()
                        if dept and dept.code:
                            value = dept.code[:length]
                            generated_id_parts.append(value.ljust(length, '0')[:length])
                        else:
                            generated_id_parts.append('0' * length)
                    else:
                        generated_id_parts.append('0' * length)
                
                else:
                    # Default: use zeros
                    generated_id_parts.append('0' * length)
            
            # Add separator if not last segment
            if separator and len(generated_id_parts) < len(segments):
                generated_id_parts.append(separator)
        
        generated_id = ''.join(generated_id_parts)
        
        # Check for uniqueness
        from app.models.student import Student
        existing = db.query(Student).filter(
            Student.student_id == generated_id,
            Student.institution_id == institution_id,
            Student.deleted_at.is_(None)
        ).first()
        
        if existing:
            # If duplicate, append sequence number
            counter = 1
            while existing:
                generated_id = ''.join(generated_id_parts[:-1] if generated_id_parts[-1].isdigit() else generated_id_parts) + str(counter).zfill(2)
                existing = db.query(Student).filter(
                    Student.student_id == generated_id,
                    Student.institution_id == institution_id,
                    Student.deleted_at.is_(None)
                ).first()
                counter += 1
        
        return generated_id
        
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        raise ValidationError(f"Error generating student ID: {str(e)}. Please check matricule format configuration.")
