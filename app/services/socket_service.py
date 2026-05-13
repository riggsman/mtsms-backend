"""
Socket.IO Server Module for Real-time Cache Invalidation Events

This module provides real-time communication with all connected clients
when system settings are updated (especially force apply).

Usage:
    from app.services.socket_service import socket_manager
    
    # In your route handler:
    socket_manager.emit_cache_invalidated({
        'cache_version': '1234567890',
        'maintenance_mode': True,
        'triggered_by': user_id
    })
"""

import logging
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)


class SocketManager:
    """
    Singleton manager for Socket.IO server events.
    Handles emitting events to all connected clients.
    """
    
    _instance: Optional['SocketManager'] = None
    _sio = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def init(self, sio):
        """Initialize with Socket.IO server instance"""
        self._sio = sio
        self._initialized = True
        logger.info("[SocketManager] Initialized with Socket.IO server")
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized and self._sio is not None
    
    def emit_cache_invalidated(self, data: Dict[str, Any]) -> bool:
        """
        Emit cache invalidation event to all connected clients.
        
        Args:
            data: Dictionary containing:
                - cache_version: The new cache version
                - maintenance_mode: Boolean indicating maintenance mode state
                - triggered_by: User ID who triggered the event
                - timestamp: ISO timestamp of the event
                
        Returns:
            True if event was emitted successfully, False otherwise
        """
        if not self.is_initialized:
            logger.warning("[SocketManager] Not initialized - cannot emit event")
            return False
        
        try:
            event_data = {
                'event': 'cache_invalidated',
                'data': data,
                'message': 'System settings have been updated. Please refresh.'
            }
            
            # Emit to all connected clients in 'system' namespace (admins)
            self._sio.emit('cache_invalidated', event_data, namespace='/system')
            
            # Emit to all connected clients in default namespace (tenants)
            self._sio.emit('cache_invalidated', event_data)
            
            logger.info(f"[SocketManager] Emitted cache_invalidated event: {data}")
            return True
            
        except Exception as e:
            logger.error(f"[SocketManager] Error emitting event: {e}")
            return False
    
    def emit_maintenance_mode_changed(self, enabled: bool, triggered_by: int = None) -> bool:
        """
        Emit maintenance mode change event to all connected clients.
        
        Args:
            enabled: Boolean indicating if maintenance mode is now enabled
            triggered_by: User ID who triggered the change
        """
        data = {
            'maintenance_mode': enabled,
            'triggered_by': triggered_by,
            'timestamp': __import__('datetime').datetime.utcnow().isoformat()
        }
        
        return self.emit_cache_invalidated(data)
    
    def emit_settings_updated(self, settings: Dict[str, Any], triggered_by: int = None) -> bool:
        """
        Emit settings updated event to all connected clients.
        
        Args:
            settings: Dictionary of updated settings
            triggered_by: User ID who triggered the update
        """
        data = {
            'settings': settings,
            'triggered_by': triggered_by,
            'timestamp': __import__('datetime').datetime.utcnow().isoformat()
        }
        
        if not self.is_initialized:
            logger.warning("[SocketManager] Not initialized - cannot emit event")
            return False
        
        try:
            event_data = {
                'event': 'settings_updated',
                'data': data,
                'message': 'System settings have been updated.'
            }
            
            self._sio.emit('settings_updated', event_data, namespace='/system')
            self._sio.emit('settings_updated', event_data)
            
            logger.info(f"[SocketManager] Emitted settings_updated event: {list(settings.keys())}")
            return True
            
        except Exception as e:
            logger.error(f"[SocketManager] Error emitting settings_updated: {e}")
            return False
    
    def get_connected_clients_count(self) -> int:
        """Get the number of connected clients"""
        if not self.is_initialized:
            return 0
        
        try:
            # Count clients across all namespaces
            system_count = len(self._sio.manager.get_participants('/system', 'default') or [])
            default_count = len(self._sio.manager.get_participants('/', 'default') or [])
            return system_count + default_count
        except Exception as e:
            logger.error(f"[SocketManager] Error getting client count: {e}")
            return 0


# Global instance
socket_manager = SocketManager()


def get_socket_manager() -> SocketManager:
    """Get the global socket manager instance"""
    return socket_manager
