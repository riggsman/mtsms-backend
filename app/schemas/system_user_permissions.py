from typing import List, Optional

from pydantic import BaseModel, Field


class SystemUserPermissionRow(BaseModel):
    id: int
    username: str
    email: str
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    roles: List[str]
    system_permissions: List[str] = Field(default_factory=list)


class SystemUserPermissionsListResponse(BaseModel):
    items: List[SystemUserPermissionRow]
    known_permissions: List[str] = Field(
        default_factory=lambda: ["database_config"],
        description="Keys the UI may grant to system_admin users",
    )


class SystemUserPermissionsUpdate(BaseModel):
    system_permissions: List[str] = Field(default_factory=list)
