"""
FastAPI stub for alembic to work without full fastapi installation
"""
from typing import Optional, Any

class Depends:
    def __init__(self, dependency=None):
        pass

class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str = None):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)

class FastAPI:
    def __init__(self, **kwargs):
        pass
    
    def include_router(self, router, **kwargs):
        pass
    
    def add_middleware(self, middleware_class, **kwargs):
        pass

class Request:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class Response:
    def __init__(self, content=None, status_code: int = 200, **kwargs):
        self.content = content
        self.status_code = status_code

# Stub modules
UploadFile = Any
Query = lambda **kwargs: kwargs

def FastAPIClass(**kwargs):
    return FastAPI()

# Stub for Depends
DependsClass = lambda x: x

# Make this importable
import sys
sys.modules['fastapi'] = type(sys)('fastapi')
sys.modules['fastapi'].Depends = Depends
sys.modules['fastapi'].HTTPException = HTTPException
sys.modules['fastapi'].FastAPI = FastAPI
sys.modules['fastapi'].Request = Request
sys.modules['fastapi'].Response = Response
sys.modules['fastapi'].UploadFile = UploadFile
sys.modules['fastapi'].Query = Query
sys.modules['fastapi.responses'] = type(sys)('fastapi.responses')
sys.modules['fastapi.responses'].Response = Response
sys.modules['fastapi.middleware'] = type(sys)('fastapi.middleware')
sys.modules['fastapi.middleware.cors'] = type(sys)('fastapi.middleware.cors')
sys.modules['fastapi.middleware.cors'].CORSMiddleware = type('CORSMiddleware', (), {
    '__init__': lambda self, app, **kwargs: None
})
sys.modules['fastapi.staticfiles'] = type(sys)('fastapi.staticfiles')
sys.modules['pydantic'] = type(sys)('pydantic')
sys.modules['pydantic'].BaseModel = type('BaseModel', (), {
    '__init__': lambda self, **kwargs: None
})
sys.modules['pydantic'].Field = lambda **kw: None
sys.modules['pydantic'].validator = lambda *args, **kw: lambda f: f