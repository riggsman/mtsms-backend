from pydantic import BaseModel, model_validator
from typing import Optional, List, Dict, Any
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
    matricule_format: Optional[MatriculeFormatConfig] = None

class TenantSettingsResponse(BaseModel):
    id: int
    institution_id: int
    matricule_format: Optional[Any] = None  # Accept dict or JSON string from DB
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
        
        return data
