from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Dict, Any

from app.constants.program_levels import (
    DEFAULT_ENABLED_PROGRAM_LEVELS,
    sanitize_enabled_program_levels,
)
from datetime import datetime
import json

class MatriculeSegment(BaseModel):
    """Configuration for a single segment of the matricule format"""
    type: str  # "constant" or "variable"
    value: Optional[str] = None  # Value if constant
    pattern: Optional[str] = None  # Pattern if variable (e.g., "year", "sequence", "class_code")
    length: Optional[int] = None  # Length for variable segments
    separator: Optional[str] = None  # Separator after this segment (e.g., "-", "/", "")

class MatriculeFormatConfig(BaseModel):
    """Complete matricule format configuration"""
    segments: List[MatriculeSegment]  # 4 segments
    is_configured: bool = False

class TenantSettingsRequest(BaseModel):
    institution_id: Optional[int] = None  # Optional - will be extracted from current user if not provided
    matricule_format: Optional[MatriculeFormatConfig] = None
    email_reminder_time: Optional[int] = None  # Minutes before class to send reminder
    branches_enabled: Optional[bool] = None  # Multi-campus mode
    payroll_auto_generate_codes: Optional[bool] = None
    current_semester_id: Optional[int] = Field(None, ge=1)
    enabled_program_levels: Optional[List[str]] = Field(
        None,
        description="Degree program levels offered by this tenant (HND, BTECH, BSC, MTECH, MSC, MBA)",
    )


class TenantSettings(BaseModel):
    id: int
    institution_id: int
    matricule_format: Optional[Any] = None  # Accept dict or JSON string from DB
    is_matricule_format_set: bool = False  # Flag to indicate if matricule format is configured
    logo: Optional[str] = None  # Path to tenant logo file
    email_reminder_time: Optional[int] = 30  # Minutes before class to send reminder (default: 30)
    branches_enabled: bool = False
    payroll_auto_generate_codes: bool = False
    current_semester_id: Optional[int] = None
    enabled_program_levels: List[str] = Field(
        default_factory=lambda: list(DEFAULT_ENABLED_PROGRAM_LEVELS)
    )
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None




    class Config:
        from_attributes = True
    
    @model_validator(mode='before')
    @classmethod
    def parse_matricule_format(cls, data):
        """Parse JSON string matricule_format from database to dict"""
        # Handle ORM object - convert to dict first
        if hasattr(data, '__dict__') and not isinstance(data, dict):
            # Convert ORM object to dict
            data = {
                'id': getattr(data, 'id', None),
                'institution_id': getattr(data, 'institution_id', None),
                'matricule_format': getattr(data, 'matricule_format', None),
                'is_matricule_format_set': getattr(data, 'is_matricule_format_set', False),
                'logo': getattr(data, 'logo', None),
                # 'category': getattr(data, 'category', None),
                'email_reminder_time': getattr(data, 'email_reminder_time', 30),
                'branches_enabled': getattr(data, 'branches_enabled', False),
                'payroll_auto_generate_codes': getattr(data, 'payroll_auto_generate_codes', False),
                'current_semester_id': getattr(data, 'current_semester_id', None),
                'enabled_program_levels': getattr(data, 'enabled_program_levels', None),
                'created_at': getattr(data, 'created_at', None),
                'updated_at': getattr(data, 'updated_at', None)
            }
        
        # Handle dict (either from ORM conversion or direct dict)
        if isinstance(data, dict):
            matricule_format = data.get('matricule_format')
            if isinstance(matricule_format, str):
                try:
                    # Parse JSON string to dict
                    data['matricule_format'] = json.loads(matricule_format)
                except (json.JSONDecodeError, TypeError):
                    # If parsing fails, set to None
                    data['matricule_format'] = None
            
            # Ensure email_reminder_time has a default value if None
            if data.get('email_reminder_time') is None:
                data['email_reminder_time'] = 30

            raw_levels = data.get('enabled_program_levels')
            if isinstance(raw_levels, str):
                try:
                    raw_levels = json.loads(raw_levels)
                except (json.JSONDecodeError, TypeError):
                    raw_levels = None
            data['enabled_program_levels'] = sanitize_enabled_program_levels(
                raw_levels if isinstance(raw_levels, list) else None,
                default_all=True,
            )
        
        return data

class TenantSettingsResponse(TenantSettings):
    category: str
   
    