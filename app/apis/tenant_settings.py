from sqlalchemy.orm import Session
from typing import Optional
from app.models.tenant import Tenant
from app.models.tenant_settings import TenantSettings
from app.schemas.tenant_settings import TenantSettingsRequest, TenantSettingsResponse, MatriculeFormatConfig
from app.constants.program_levels import sanitize_enabled_program_levels
from app.exceptions import NotFoundError, ValidationError
import json
import datetime

def get_tenant_category(db: Session, institution_id: int) -> Optional[Tenant]:
    """Get tenant settings by institution_id"""
    print("INSTITUTION ID FROM CLIENT ", institution_id)
    return db.query(Tenant).filter(
        Tenant.id == institution_id
    ).first()
    
def get_tenant_settings(db: Session, institution_id: int) -> Optional[TenantSettings]:
    """Get tenant settings by institution_id"""
    print("INSTITUTION ID FROM CLIENT ", institution_id)
    return db.query(TenantSettings).filter(
        TenantSettings.institution_id == institution_id
    ).first()


def matricule_format_as_dict(raw) -> dict:
    """Normalize matricule_format from DB (JSON dict, JSON string, or None)."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def create_or_update_tenant_settings(
    db: Session, 
    institution_id: int, 
    settings: TenantSettingsRequest
) -> TenantSettings:
    """Create or update tenant settings"""
    existing = get_tenant_settings(db, institution_id)
    
    # Prepare matricule_format as JSON
    # Check if matricule_format is provided in the request
    has_matricule_format_in_request = settings.matricule_format is not None
    
    matricule_format_json = None
    if settings.matricule_format:
        # Convert to dict for JSON storage
        matricule_format_dict = settings.matricule_format.dict()
        matricule_format_json = json.dumps(matricule_format_dict)
    
    if existing:
        # Update existing settings
        if has_matricule_format_in_request:
            # If matricule_format is provided in the request, update it and set flag to True
            existing.matricule_format = matricule_format_json
            existing.is_matricule_format_set = True
        # Update email_reminder_time if provided
        if settings.email_reminder_time is not None:
            existing.email_reminder_time = settings.email_reminder_time
        if settings.branches_enabled is not None:
            existing.branches_enabled = settings.branches_enabled
        if settings.payroll_auto_generate_codes is not None:
            existing.payroll_auto_generate_codes = bool(settings.payroll_auto_generate_codes)
        if settings.current_semester_id is not None:
            existing.current_semester_id = settings.current_semester_id
        if settings.enabled_program_levels is not None:
            existing.enabled_program_levels = sanitize_enabled_program_levels(
                settings.enabled_program_levels,
                default_all=False,
            )
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new settings
        # Set is_matricule_format_set to True if matricule_format is provided in the request
        new_settings = TenantSettings(
            institution_id=institution_id,
            matricule_format=matricule_format_json,
            is_matricule_format_set=True if has_matricule_format_in_request else False,
            email_reminder_time=settings.email_reminder_time if settings.email_reminder_time is not None else 30,
            branches_enabled=bool(settings.branches_enabled) if settings.branches_enabled is not None else False,
            payroll_auto_generate_codes=bool(settings.payroll_auto_generate_codes) if settings.payroll_auto_generate_codes is not None else False,
            current_semester_id=settings.current_semester_id,
            enabled_program_levels=sanitize_enabled_program_levels(
                settings.enabled_program_levels,
                default_all=True,
            ),
        )
        db.add(new_settings)
        db.commit()
        db.refresh(new_settings)
        return new_settings

def is_matricule_format_configured(db: Session, institution_id: int) -> bool:
    """Check if matricule format is configured for the tenant"""
    settings = get_tenant_settings(db, institution_id)
    if not settings or not settings.matricule_format or not settings.is_matricule_format_set:
        print("Matricule format is not configured. Please configure it in Tenant Settings before creating students. matricle_format: ", settings.matricule_format, " is_matricule_format_set: ", settings.is_matricule_format_set)
        return False
    
    try:
        format_config = matricule_format_as_dict(settings.matricule_format)
        return format_config.get('is_configured', False) and len(format_config.get('segments', [])) == 4
    except (TypeError, AttributeError):
        return False

def generate_student_id(db: Session, institution_id: int, student_data: dict) -> str:
    """
    Generate student ID based on configured matricule format
    
    Args:
        db: Database session
        institution_id: Institution ID
        student_data: Dictionary containing student data (class_id, academic_year, school_id, branch_id, department_id, etc.)
    
    Returns:
        Generated student ID string
    """
    settings = get_tenant_settings(db, institution_id)
    
    if not settings or not settings.matricule_format:
        raise ValidationError(
            "Matricule format is not configured. Please configure it in Tenant Settings before creating students."
        )
    
    try:
        format_config = matricule_format_as_dict(settings.matricule_format)
        segments = format_config.get('segments', [])
        
        if not format_config.get('is_configured', False) or len(segments) != 4:
            raise ValidationError(
                "Matricule format is not properly configured. Please configure all 4 segments in Tenant Settings."
            )
        
        return _build_matricule(db, institution_id, student_data, segments, use_preview=False)
        
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        raise ValidationError(f"Error generating student ID: {str(e)}. Please check matricule format configuration.")


def preview_student_id(db: Session, institution_id: int, student_data: dict) -> str:
    """
    Preview student ID based on configured matricule format WITHOUT incrementing sequence.
    Format: TENANT_INITIALS + ACADEMIC_YEAR + SCHOOL_INITIAL + SEQUENCE
    Example: RUI26CSC001
    
    Args:
        db: Database session
        institution_id: Institution ID
        student_data: Dictionary containing student data (tenant_initial, school_initial, academic_year, etc.)
    
    Returns:
        Preview of student ID string
    """
    tenant_initial = student_data.get('tenant_initial')
    school_initial = student_data.get('school_initial') or student_data.get('school_code')
    academic_year = student_data.get('academic_year')
    
    if tenant_initial and school_initial and academic_year:
        year_suffix = str(academic_year)[-2:]
        
        from app.helpers.matricule_number_generator import preview_next_sequence
        sequence = preview_next_sequence(
            str(tenant_initial).upper(),
            year_suffix,
            '',
            str(school_initial).upper()
        )
        
        return f"{str(tenant_initial).upper()}{year_suffix}{str(school_initial).upper()}{sequence}"
    
    settings = get_tenant_settings(db, institution_id)
    
    if not settings or not settings.matricule_format:
        raise ValidationError(
            "Matricule format is not configured. Please configure it in Tenant Settings before creating students."
        )
    
    try:
        format_config = matricule_format_as_dict(settings.matricule_format)
        segments = format_config.get('segments', [])
        
        if not format_config.get('is_configured', False) or len(segments) != 4:
            raise ValidationError(
                "Matricule format is not properly configured. Please configure all 4 segments in Tenant Settings."
            )
        
        return _build_matricule(db, institution_id, student_data, segments, use_preview=True)
        
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        raise ValidationError(f"Error generating student ID preview: {str(e)}. Please check matricule format configuration.")


def allocate_student_matricule(db: Session, institution_id: int, student_data: dict) -> str:
    """
    Allocate and return the next student ID (matricule).
    Format: TENANT_INITIALS + ACADEMIC_YEAR + SCHOOL_INITIAL + SEQUENCE
    Example: RUI26CSC001
    
    Args:
        db: Database session
        institution_id: Institution ID
        student_data: Dictionary containing student data (tenant_initial, school_initial, academic_year, etc.)
    
    Returns:
        Allocated student ID string
    """
    tenant_initial = student_data.get('tenant_initial')
    school_initial = student_data.get('school_initial') or student_data.get('school_code')
    academic_year = student_data.get('academic_year')
    
    if tenant_initial and school_initial and academic_year:
        year_suffix = str(academic_year)[-2:]
        
        from app.helpers.matricule_number_generator import get_next_sequence
        sequence = get_next_sequence(
            str(tenant_initial).upper(),
            year_suffix,
            '',
            str(school_initial).upper()
        )
        
        return f"{str(tenant_initial).upper()}{year_suffix}{str(school_initial).upper()}{sequence}"
    
    settings = get_tenant_settings(db, institution_id)
    
    if not settings or not settings.matricule_format:
        raise ValidationError(
            "Matricule format is not configured. Please configure it in Tenant Settings before creating students."
        )
    
    try:
        format_config = matricule_format_as_dict(settings.matricule_format)
        segments = format_config.get('segments', [])
        
        if not format_config.get('is_configured', False) or len(segments) != 4:
            raise ValidationError(
                "Matricule format is not properly configured. Please configure all 4 segments in Tenant Settings."
            )
        
        return _build_matricule(db, institution_id, student_data, segments, use_preview=False)
        
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        raise ValidationError(f"Error allocating student ID: {str(e)}. Please check matricule format configuration.")


def _build_matricule(db: Session, institution_id: int, student_data: dict, segments: list, use_preview: bool = False) -> str:
    """Internal helper to build matricule from segments"""
    generated_id_parts = []
    segment_count = len(segments)
    
    for idx, segment in enumerate(segments):
        seg_type = segment.get('type', 'constant')
        length = segment.get('length', 4)
        separator = segment.get('separator', '')
        
        if seg_type == 'constant':
            value = segment.get('value', '')
            # Truncate or pad to required length
            if len(value) < length:
                value = value.ljust(length, '0')
            else:
                value = value[:length]
            generated_id_parts.append(value)
        elif seg_type == 'variable':
            pattern = segment.get('pattern', 'sequence')
            
            if pattern == 'year':
                # Use current year or academic year
                year = student_data.get('academic_year', datetime.datetime.now().year)
                value = str(year)[-length:] if length <= 2 else str(year)
                generated_id_parts.append(value.zfill(length))
            
            elif pattern == 'sequence':
                # Use context-aware sequence from matricule_number_generator
                from app.helpers.matricule_number_generator import get_next_sequence, preview_next_sequence
                
                school_initial = student_data.get('school_initial', '')
                year = student_data.get('academic_year', datetime.datetime.now().year)
                year_suffix = str(year)[-2:]
                branch_initial = student_data.get('branch_initial', '')
                dept_code = student_data.get('department_code', '')
                
                if use_preview:
                    sequence = preview_next_sequence(school_initial, year_suffix, branch_initial, dept_code)
                else:
                    sequence = get_next_sequence(school_initial, year_suffix, branch_initial, dept_code)
                generated_id_parts.append(sequence.zfill(length))
            
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
                # Use department code directly if provided, otherwise lookup from department_id
                department_code = student_data.get('department_code')
                if department_code:
                    value = str(department_code).strip().upper()[:length]
                    generated_id_parts.append(value.ljust(length, '0')[:length])
                else:
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
            
            elif pattern == 'school_initial':
                # Use school initial directly if provided, otherwise lookup from school_id
                school_initial = student_data.get('school_initial')
                if school_initial:
                    value = str(school_initial).strip().upper()[:length]
                    generated_id_parts.append(value.ljust(length, '0')[:length])
                else:
                    school_id = student_data.get('school_id')
                    if school_id:
                        from app.models.school import School
                        school = db.query(School).filter(School.id == school_id).first()
                        if school and school.code:
                            value = school.code.strip().upper()[:length]
                            generated_id_parts.append(value.ljust(length, '0')[:length])
                        else:
                            generated_id_parts.append('0' * length)
                    else:
                        generated_id_parts.append('0' * length)
            
            elif pattern == 'branch_initial':
                # Use branch initial if available and branch is provided
                branch_id = student_data.get('branch_id')
                if branch_id:
                    from app.models.branch import Branch
                    branch = db.query(Branch).filter(Branch.id == branch_id).first()
                    if branch and branch.name:
                        # Take first letter of branch name, uppercase
                        value = branch.name.strip()[0].upper()
                        value = value.ljust(length, '0')[:length]
                        generated_id_parts.append(value)
                    else:
                        generated_id_parts.append('0' * length)
                else:
                    # Branch not provided, skip this segment (don't append anything)
                    # Also skip the separator for this segment
                    continue
            
            else:
                # Default: use zeros
                generated_id_parts.append('0' * length)
        
        # Add separator AFTER each segment except the last one
        if separator and idx < segment_count - 1:
            generated_id_parts.append(separator)
    
    return ''.join(generated_id_parts)


def render_first_matricule_segment_prefix(segment: dict) -> str:
    """
    Build the prefix (initials) for lecturer employee_id from matricule_format.segments[0],
    using the same rules as the first segment of student matricule generation.
    """
    seg_type = segment.get("type", "constant")
    length = int(segment.get("length") or 4)
    length = max(1, min(length, 32))

    if seg_type == "constant":
        value = segment.get("value") or ""
        value = str(value).strip()
        if not value:
            raise ValidationError(
                "Lecturer matricule: the first matricule segment must have a constant value "
                "(tenant initials) in Tenant Settings → Matricule."
            )
        if len(value) < length:
            value = value.ljust(length, "0")
        else:
            value = value[:length]
        return value

    if seg_type == "variable":
        pattern = segment.get("pattern", "sequence")
        if pattern == "year":
            year = datetime.datetime.now().year
            value = str(year)[-length:] if length <= 4 else str(year)
            return value.zfill(length)
        raise ValidationError(
            "Lecturer matricule: the first segment must be constant (initials) or variable type 'year'. "
            "Other variable patterns are not supported for lecturer prefix."
        )

    raise ValidationError("Lecturer matricule: invalid first segment type in matricule format.")


def allocate_next_lecturer_employee_id(db: Session, institution_id: int) -> str:
    """
    Atomically allocate the next lecturer employee_id (matricule):
    prefix from tenant_settings.matricule_format.segments[0] + sequential numeric suffix.
    Persists lecturer_matricule_last_sequence on tenant_settings for progression.
    """
    from app.models.teacher import Teacher

    if not is_matricule_format_configured(db, institution_id):
        raise ValidationError(
            "Matricule format is not fully configured. Configure all four segments in Tenant Settings "
            "before auto-generating lecturer matricules."
        )

    settings = (
        db.query(TenantSettings)
        .filter(TenantSettings.institution_id == institution_id)
        .with_for_update()
        .first()
    )
    if not settings:
        raise ValidationError(
            "Tenant settings not found for this institution. Save Tenant Settings once before adding lecturers."
        )

    format_config = matricule_format_as_dict(settings.matricule_format)
    segments = format_config.get("segments") or []
    if not segments:
        raise ValidationError("Matricule format has no segments. Configure matricule format in Tenant Settings.")

    prefix = render_first_matricule_segment_prefix(segments[0])
    suffix_len = 3

    last = settings.lecturer_matricule_last_sequence
    if last is None:
        last = 0

    for _ in range(10000):
        next_seq = last + 1
        candidate = f"{prefix}{str(next_seq).zfill(suffix_len)}"
        clash = (
            db.query(Teacher)
            .filter(
                Teacher.employee_id == candidate,
                Teacher.deleted_at.is_(None),
            )
            .first()
        )
        last = next_seq
        settings.lecturer_matricule_last_sequence = last
        if not clash:
            db.flush()
            return candidate
        db.flush()

    raise ValidationError("Could not allocate a unique lecturer matricule; try again or contact support.")
