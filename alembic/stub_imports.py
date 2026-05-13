# Stub to bypass fastapi import for alembic
# This file must be imported before app.database.sessionManager
import sys
from types import ModuleType

# Create minimal stub modules
fastapi_stub = ModuleType('fastapi')
fastapi_stub.Dependencies = type('Depends', (), {'__init__': lambda self, dep=None: None})
fastapi_stub.HTTPException = type('HTTPException', (Exception,), {
    '__init__': lambda self, status_code=500, detail=None: None
})
fastapi_stub.UploadFile = type('UploadFile', (), {})
fastapi_stub.Query = lambda **kw: kw

starlette_stub = ModuleType('starlette')
starlette_stub.Request = type('Request', (), {})

# Register stubs
sys.modules['fastapi'] = fastapi_stub
sys.modules['fastapi.dependencies'] = fastapi_stub
sys.modules['starlette'] = starlette_stub

# Now we can import the real sessionManager
from app.database.sessionManager import BaseModel_Base, Base