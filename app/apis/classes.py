from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.classes import Class
from app.models.user import User
from app.schemas.classes import ClassRequest, ClassResponse, ClassUpdate
from app.exceptions import NotFoundError, ConflictError
from app.helpers.pagination import paginate_query
from app.helpers.activity_logger import log_create_activity, log_update_activity, log_delete_activity

def create_class(db: Session, class_data: ClassRequest, institution_id: Optional[int] = None, current_user: Optional[User] = None) -> Class:
    """Create a new class"""
    final_institution_id = class_data.institution_id or institution_id
    
    if not final_institution_id:
        from app.exceptions import ValidationError
        raise ValidationError("institution_id is required to create a class")
    
    # Map category to institution_level if category is provided but institution_level is not
    # Category (HI/SI) should map to institution_level
    if class_data.category and not class_data.institution_level:
        class_data.institution_level = class_data.category
    
    # Validate institution_level
    if class_data.institution_level not in ["HI", "SI"]:
        from app.exceptions import ValidationError
        raise ValidationError("institution_level must be 'HI' (Higher Institution) or 'SI' (Secondary Institution)")
    
    # Also set category from institution_level if category is not provided
    if not class_data.category:
        class_data.category = class_data.institution_level
    
    # Check if class code already exists for this institution
    existing = db.query(Class).filter(
        Class.code == class_data.code,
        Class.institution_id == final_institution_id,
        Class.deleted_at.is_(None)
    ).first()
    if existing:
        raise ConflictError(f"Class with code {class_data.code} already exists for this institution")
    
    # Create class - mark as custom
    class_dict = class_data.dict(exclude={'institution_id'})
    class_dict['institution_id'] = final_institution_id
    class_dict['is_custom'] = True  # All created classes are custom
    new_class = Class(**class_dict)
    db.add(new_class)
    db.commit()
    db.refresh(new_class)
    
    # Enrich with level information
    new_class = _enrich_class_with_level(db, new_class)
    
    # Log activity if current_user is provided
    if current_user:
        try:
            class_name = f"{class_data.name} ({class_data.code})"
            log_create_activity(
                db=db,
                current_user=current_user,
                entity_type="class",
                entity_id=new_class.id,
                entity_name=class_name,
                institution_id=final_institution_id,
                content=f"Created class: {class_name} - {class_data.institution_level}"
            )
        except Exception as e:
            print(f"Error logging class creation activity: {e}")
    
    return new_class

def _enrich_class_with_level(db: Session, class_obj: Class) -> Class:
    """Helper function to add level information to class object"""
    if class_obj.level_id:
        try:
            # Try to get level from levels table if it exists
            from sqlalchemy import inspect, text
            inspector = inspect(db.bind)
            tables = inspector.get_table_names()
            
            if 'levels' in tables:
                # Query level information - handle both string and integer IDs
                try:
                    level_result = db.execute(
                        text("SELECT level, code FROM levels WHERE id = :level_id"),
                        {"level_id": class_obj.level_id}
                    ).first()
                except:
                    # Try with string ID if integer fails
                    level_result = db.execute(
                        text("SELECT level, code FROM levels WHERE id = :level_id"),
                        {"level_id": str(class_obj.level_id)}
                    ).first()
                
                if level_result:
                    setattr(class_obj, 'level', level_result[0])  # level name
                    setattr(class_obj, 'level_code', level_result[1])  # level code
                else:
                    setattr(class_obj, 'level', None)
                    setattr(class_obj, 'level_code', None)
            else:
                setattr(class_obj, 'level', None)
                setattr(class_obj, 'level_code', None)
        except Exception as e:
            # If level lookup fails, just set to None
            setattr(class_obj, 'level', None)
            setattr(class_obj, 'level_code', None)
    else:
        setattr(class_obj, 'level', None)
        setattr(class_obj, 'level_code', None)
    
    return class_obj

def get_class(db: Session, class_id: int) -> Class:
    """Get a class by ID"""
    class_obj = db.query(Class).filter(
        Class.id == class_id,
        Class.deleted_at.is_(None)
    ).first()
    if not class_obj:
        raise NotFoundError(f"Class with ID {class_id} not found")
    
    # Enrich with level information
    class_obj = _enrich_class_with_level(db, class_obj)
    return class_obj

def get_default_classes(institution_level: str = "HI") -> List[dict]:
    """Get default class definitions"""
    HI_DEFAULT_CLASSES = [
        {"name": "Level 1", "code": "L1", "institution_level": "HI"},
        {"name": "Level 2", "code": "L2", "institution_level": "HI"},
        {"name": "Level 3", "code": "L3", "institution_level": "HI"},
        {"name": "Level 4", "code": "L4", "institution_level": "HI"},
        {"name": "Level 5", "code": "L5", "institution_level": "HI"},
    ]
    
    SI_DEFAULT_CLASSES = [
        {"name": "Grade 7", "code": "G7", "institution_level": "SI"},
        {"name": "Grade 8", "code": "G8", "institution_level": "SI"},
        {"name": "Grade 9", "code": "G9", "institution_level": "SI"},
        {"name": "Grade 10", "code": "G10", "institution_level": "SI"},
        {"name": "Grade 11", "code": "G11", "institution_level": "SI"},
        {"name": "Grade 12", "code": "G12", "institution_level": "SI"},
    ]
    
    if institution_level == "SI":
        return SI_DEFAULT_CLASSES
    return HI_DEFAULT_CLASSES

def get_classes(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    institution_id: Optional[int] = None,
    institution_level: Optional[str] = None,
    department_id: Optional[int] = None
) -> tuple[List[Class], int]:
    """
    Get list of classes with pagination.
    Priority: Custom classes first, then fallback to default classes if no custom classes exist.
    """
    # First, get custom classes for the institution
    query = db.query(Class).filter(
        Class.deleted_at.is_(None),
        Class.is_custom == True  # Only get custom classes
    )
    
    if institution_id is not None:
        query = query.filter(Class.institution_id == institution_id)
    
    if institution_level:
        # Filter by institution_level (which corresponds to category HI/SI)
        query = query.filter(Class.institution_level == institution_level)
    
    if department_id:
        query = query.filter(Class.department_id == department_id)
    
    # Get custom classes
    custom_classes, custom_total = paginate_query(query, page=(skip // limit) + 1, page_size=limit)
    
    # Enrich classes with level information and ensure category is set
    enriched_classes = []
    for class_obj in custom_classes:
        enriched_class = _enrich_class_with_level(db, class_obj)
        # Ensure category is set from institution_level if not already set
        if not enriched_class.category and enriched_class.institution_level:
            enriched_class.category = enriched_class.institution_level
        enriched_classes.append(enriched_class)
    
    # If we have custom classes, return them
    if enriched_classes and len(enriched_classes) > 0:
        return enriched_classes, custom_total
    
    # If no custom classes exist, return default classes as fallback
    # Convert default classes to Class-like objects for consistency
    default_classes_list = []
    if institution_level:
        default_definitions = get_default_classes(institution_level)
    else:
        # If no level specified, return both HI and SI defaults
        default_definitions = get_default_classes("HI") + get_default_classes("SI")
    
    # Create Class objects from default definitions
    # These are virtual objects (not in DB) but have the same structure
    for idx, default_def in enumerate(default_definitions):
        # Skip if institution_level filter is set and doesn't match
        if institution_level and default_def["institution_level"] != institution_level:
            continue
            
        # Create a Class-like object (we'll use a dict that matches ClassResponse schema)
        # Use the actual institution_id passed in (should be set for tenant users)
        default_class = type('Class', (), {
            'id': -(idx + 1),  # Negative ID to indicate it's a default class
            'institution_id': institution_id if institution_id is not None else 0,  # Use actual institution_id for tenant isolation
            'name': default_def["name"],
            'code': default_def["code"],  # Code displayed in code section
            'institution_level': default_def["institution_level"],
            'category': default_def["institution_level"],  # Set category from institution_level
            'is_custom': False,
            'level_id': None,
            'level': None,  # Level name displayed in level section
            'level_code': None,  # Level code if available
            'department_id': None,
            'academic_year_id': None,
            'capacity': None,
            'created_at': None,
            'updated_at': None
        })()
        default_classes_list.append(default_class)
    
    # Apply pagination to default classes
    start_idx = skip
    end_idx = skip + limit
    paginated_defaults = default_classes_list[start_idx:end_idx]
    
    return paginated_defaults, len(default_classes_list)

def update_class(db: Session, class_id: int, class_update: ClassUpdate, current_user: Optional[User] = None) -> Class:
    """Update a class"""
    class_obj = get_class(db, class_id)
    
    update_data = class_update.dict(exclude_unset=True)
    
    # Validate institution_level if being updated
    if "institution_level" in update_data:
        if update_data["institution_level"] not in ["HI", "SI"]:
            from app.exceptions import ValidationError
            raise ValidationError("institution_level must be 'HI' (Higher Institution) or 'SI' (Secondary Institution)")
    
    # Check code uniqueness if being updated
    if "code" in update_data:
        existing = db.query(Class).filter(
            Class.code == update_data["code"],
            Class.institution_id == class_obj.institution_id,
            Class.id != class_id,
            Class.deleted_at.is_(None)
        ).first()
        if existing:
            raise ConflictError(f"Class with code {update_data['code']} already exists for this institution")
    
    for field, value in update_data.items():
        setattr(class_obj, field, value)
    
    db.commit()
    db.refresh(class_obj)
    
    # Enrich with level information
    class_obj = _enrich_class_with_level(db, class_obj)
    
    # Log activity if current_user is provided
    if current_user:
        try:
            class_name = f"{class_obj.name} ({class_obj.code})"
            log_update_activity(
                db=db,
                current_user=current_user,
                entity_type="class",
                entity_id=class_obj.id,
                entity_name=class_name,
                institution_id=class_obj.institution_id,
                content=f"Updated class: {class_name}"
            )
        except Exception as e:
            print(f"Error logging class update activity: {e}")
    
    return class_obj

def delete_class(db: Session, class_id: int, current_user: Optional[User] = None) -> bool:
    """Soft delete a class"""
    class_obj = get_class(db, class_id)
    class_name = f"{class_obj.name} ({class_obj.code})"
    institution_id = class_obj.institution_id
    from datetime import datetime
    class_obj.deleted_at = datetime.utcnow()
    db.commit()
    
    # Log activity if current_user is provided
    if current_user:
        try:
            log_delete_activity(
                db=db,
                current_user=current_user,
                entity_type="class",
                entity_id=class_id,
                entity_name=class_name,
                institution_id=institution_id,
                content=f"Deleted class: {class_name}"
            )
        except Exception as e:
            print(f"Error logging class deletion activity: {e}")
    
    return True
