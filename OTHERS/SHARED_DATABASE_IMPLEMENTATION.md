# Shared Database Architecture Implementation

## Overview
This document describes the implementation of a toggleable shared database architecture that works alongside the existing multi-tenant architecture.

## Architecture Modes

### 1. Multi-Tenant Mode (Default)
- Each tenant has its own separate database
- Data is completely isolated per tenant
- Tenant name is required in request headers (`X-Tenant-Name`)

### 2. Shared Database Mode
- All tenants share a single database
- Data is separated by `tenant_id` fields in tables
- Tenant name is optional in request headers

## Implementation Details

### Backend Changes

#### 1. System Configuration Model (`app/models/system_config.py`)
- Stores system-wide configuration settings
- Key setting: `database_mode` (values: `shared` or `multi_tenant`)

#### 2. Session Manager Updates (`app/database/sessionManager.py`)
- `get_database_mode()`: Retrieves current database mode from config
- `set_database_mode()`: Updates database mode (super_admin only)
- `get_shared_db()`: Returns shared database session
- `get_tenant_db()`: Returns tenant-specific database session
- `get_db_session_for_mode()`: Automatically routes to correct database based on mode

#### 3. Tenant Dependency Updates (`app/dependencies/tenantDependency.py`)
- `get_tenant()`: Now optional in shared mode, required in multi-tenant mode
- `get_db()`: Automatically routes to shared or tenant database based on mode

#### 4. API Endpoints (`app/routes/system_config.py`)
- `GET /api/v1/database-mode`: Get current database mode (super_admin only)
- `PUT /api/v1/database-mode`: Update database mode (super_admin only)
- Additional endpoints for general system configuration management

### Frontend Changes

#### 1. API Service (`src/services/api.js`)
- `systemConfigAPI.getDatabaseMode()`: Fetch current mode
- `systemConfigAPI.updateDatabaseMode()`: Update mode

#### 2. Database Configuration Component (`src/components/adminViews/database_config.jsx`)
- UI for super_admin to view and toggle database mode
- Shows current mode and description
- Warning messages about data migration requirements
- Accessible only to super_admin role

#### 3. Navigation Updates
- Added "Database Configuration" menu item in sidebar (super_admin only)
- Route: `/admin/database-config`

## Usage

### For System Administrators

1. **Access Database Configuration**
   - Login as super_admin
   - Navigate to "Database Configuration" in the sidebar
   - View current mode and description

2. **Change Database Mode**
   - Select desired mode from dropdown
   - Review warning messages
   - Click "Save Changes"
   - Confirm the change (warning about data migration)

### For Developers

#### Using the Database Session

The `get_db()` dependency automatically handles routing:

```python
from app.dependencies.tenantDependency import get_db

@router.get("/items")
def get_items(db: Session = Depends(get_db)):
    # In shared mode: uses shared database
    # In multi-tenant mode: uses tenant-specific database
    items = db.query(Item).all()
    return items
```

#### Checking Mode Programmatically

```python
from app.database.sessionManager import get_database_mode

mode = get_database_mode()
if mode == 'shared':
    # Handle shared mode logic
    pass
else:
    # Handle multi-tenant mode logic
    pass
```

## Important Notes

### Data Migration
⚠️ **WARNING**: Changing between modes may require data migration:
- **Multi-tenant → Shared**: Need to consolidate data from multiple databases into one
- **Shared → Multi-tenant**: Need to split data from one database into multiple

### Backward Compatibility
- Existing multi-tenant implementation remains fully functional
- All existing routes work with both modes
- Default mode is `multi_tenant` if not configured

### Security
- Only `super_admin` role can access database configuration
- Mode changes require explicit confirmation
- All API endpoints are protected by authentication

## Database Schema

### System Config Table (Global Database)
```sql
CREATE TABLE system_config (
    id INT PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value VARCHAR(500),
    description VARCHAR(500),
    created_at DATETIME,
    updated_at DATETIME
);
```

### Initial Setup
Run the table creation script to create the `system_config` table:
```bash
python scripts/create_tables.py
```

## Testing

1. **Test Multi-Tenant Mode** (Default)
   - Verify tenant-specific databases are used
   - Verify tenant name is required in headers

2. **Test Shared Mode**
   - Change mode to `shared` via UI
   - Verify shared database is used
   - Verify tenant name is optional in headers

3. **Test Mode Switching**
   - Switch between modes multiple times
   - Verify system handles mode changes correctly

## Future Enhancements

1. **Automatic Data Migration**: Implement scripts to migrate data between modes
2. **Mode-Specific Features**: Add features that work differently in each mode
3. **Performance Monitoring**: Track performance differences between modes
4. **Tenant ID Filtering**: In shared mode, automatically filter queries by tenant_id
