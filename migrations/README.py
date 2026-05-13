"""
Migrations Index
================

This directory contains database migrations for the MTSMS project.

To run a migration:
    python migrations/add_cache_version_column.py

To rollback a migration:
    python migrations/rollback_cache_version_column.py

Available Migrations:
---------------------

1. add_cache_version_column.py
   - Adds cache_version column to system_settings table
   - Purpose: Enable frontend cache synchronization protocol
   - Date: 2026-04-16
   - Status: NEW

Rollback:
    python migrations/rollback_cache_version_column.py

"""
