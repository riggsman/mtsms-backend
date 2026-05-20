from typing import Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CacheVersionResponse(BaseModel):
    """
    Response model for cache version endpoint.
    Returns the current cache version timestamp.
    """
    cache_version: str
    timestamp: str


class ForceCacheInvalidateResponse(BaseModel):
    """
    Response model for force cache invalidate endpoint.
    Returns the new cache version after invalidation.
    """
    success: bool
    cache_version: str
    message: str


class FirebaseMessagingConfig(BaseModel):
  """
  Configuration for Firebase Cloud Messaging used for web push notifications.

  Field names follow the frontend (camelCase) so the JSON round-trips cleanly.
  """

  enabled: bool = False
  apiKey: Optional[str] = None
  authDomain: Optional[str] = None
  projectId: Optional[str] = None
  storageBucket: Optional[str] = None
  messagingSenderId: Optional[str] = None
  appId: Optional[str] = None
  vapidKey: Optional[str] = None
  storageBucket: Optional[str] = None
  measurementId: Optional[str] = None
  serviceAccountUploaded: Optional[bool] = None


class FirebaseWebAppConfig(BaseModel):
  """Subset of Firebase JS `initializeApp` options built from system_settings (public keys only)."""

  apiKey: str
  authDomain: str
  projectId: str
  messagingSenderId: str
  appId: str
  storageBucket: Optional[str] = None
  measurementId: Optional[str] = None


class FirebaseWebClientBundle(BaseModel):
  """
  Public bundle for browser + service worker: web SDK config and VAPID key for getToken.
  Served from GET /api/v1/system/firebase-web-config (no auth).
  """

  enabled: bool = False
  web: Optional[FirebaseWebAppConfig] = None
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
  cacheTimeout: Optional[int] = None
  inactivityTimeout: Optional[int] = None
  maintenanceCheckInterval: Optional[int] = None
  accessTokenExpireMinutes: Optional[int] = None
  refreshTokenExpireDays: Optional[int] = None
  firebaseMessaging: Optional[FirebaseMessagingConfig] = None
  platformSupportEmail: Optional[str] = None
  platformSupportPhone: Optional[str] = None
  platformSupportHours: Optional[str] = None


class SystemSettingsResponse(BaseModel):
  """
  Response model sent back to the frontend.
  """

  model_config = ConfigDict(from_attributes=True)

  id: int
  maintenanceMode: bool
  allowNewRegistrations: bool
  maxTenants: int
  sessionTimeout: int
  emailNotifications: bool
  cacheTimeout: Optional[int] = None
  inactivityTimeout: Optional[int] = None
  maintenanceCheckInterval: Optional[int] = None
  accessTokenExpireMinutes: int = 60
  refreshTokenExpireDays: int = 7
  logoUrl: Optional[str] = None
  cacheVersion: Optional[str] = None
  firebaseMessaging: Optional[FirebaseMessagingConfig] = None
  platformSupportEmail: Optional[str] = None
  platformSupportPhone: Optional[str] = None
  platformSupportHours: Optional[str] = None
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
  cacheTimeout: Optional[int] = None
  inactivityTimeout: Optional[int] = None
  maintenanceCheckInterval: Optional[int] = None


class EffectiveTimeoutsResponse(BaseModel):
  """
  Response model for effective timeout configuration.
  Returns the timeout values that should be used by the system,
  with database values taking precedence over environment variables.
  """
  cacheTimeout: int
  inactivityTimeout: int
  maintenanceCheckInterval: int
  accessTokenExpireMinutes: int
  refreshTokenExpireDays: int
  cache_version: str
  source: str  # "database" or "environment"


class ForceTimeoutsApplyResponse(BaseModel):
  """
  Response model for force apply timeouts endpoint.
  """
  success: bool
  cache_version: str
  timeouts: EffectiveTimeoutsResponse
  message: str
