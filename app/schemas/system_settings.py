from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class FirebaseMessagingConfig(BaseModel):
  """
  Configuration for Firebase Cloud Messaging used for web push notifications.

  Field names follow the frontend (camelCase) so the JSON round-trips cleanly.
  """

  enabled: bool = False
  apiKey: Optional[str] = None
  authDomain: Optional[str] = None
  projectId: Optional[str] = None
  messagingSenderId: Optional[str] = None
  appId: Optional[str] = None
  vapidKey: Optional[str] = None


class SystemSettingsRequest(BaseModel):
  """
  Body for updating system settings from the admin UI.

  Uses camelCase names to match the React component state.
  """

  maintenanceMode: Optional[bool] = None
  allowNewRegistrations: Optional[bool] = None
  maxTenants: Optional[int] = None
  sessionTimeout: Optional[int] = None
  emailNotifications: Optional[bool] = None
  firebaseMessaging: Optional[FirebaseMessagingConfig] = None


class SystemSettingsResponse(BaseModel):
  """
  Response model sent back to the frontend.
  """

  id: int
  maintenanceMode: bool
  allowNewRegistrations: bool
  maxTenants: int
  sessionTimeout: int
  emailNotifications: bool
  firebaseMessaging: Optional[FirebaseMessagingConfig] = None
  created_at: Optional[datetime] = None
  updated_at: Optional[datetime] = None


class SystemSettingsState(BaseModel):
  """
  Public-facing system settings state for frontend use.
  Contains only essential settings that need to be checked by the frontend.
  """
  maintenanceMode: bool
  allowNewRegistrations: bool
  emailNotifications: bool
