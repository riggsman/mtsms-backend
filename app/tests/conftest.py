"""
Pytest configuration and fixtures for API tests
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.sessionManager import BaseModel_Base
from server import app
from app.models.user import User
from app.models.tenant import Tenant
from app.authentication.authenticator import hash_password
from app.database.base import get_db_session
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    BaseModel_Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        BaseModel_Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db, test_admin_user):
    """Create a test client"""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    def override_get_current_user():
        return test_admin_user
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_tenant] = override_get_current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_tenant(db):
    """Create a test tenant"""
    tenant = Tenant(
        name="test_school",
        database_url="sqlite:///./test_tenant.db"
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant

@pytest.fixture
def test_admin_user(db):
    """Create a test admin user"""
    user = User(
        institution_id=1,
        firstname="Admin",
        lastname="User",
        email="admin@test.com",
        phone="+1234567890",
        username="admin",
        password=hash_password("admin123"),
        role="admin",
        is_active="active",
        gender="Male",
        address="Test Address"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def test_staff_user(db):
    """Create a test staff user"""
    user = User(
        institution_id=1,
        firstname="Staff",
        lastname="User",
        email="staff@test.com",
        phone="+1234567891",
        username="staff",
        password=hash_password("staff123"),
        role="staff",
        is_active="active",
        gender="Female",
        address="Test Address"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def admin_token(client, test_admin_user):
    """Get admin authentication token"""
    response = client.post(
        "/auth/v1/login",
        json={
            "username": "admin",
            "password": "admin123"
        },
        headers={"X-Tenant-Name": "test_school"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.fixture
def staff_token(client, test_staff_user):
    """Get staff authentication token"""
    response = client.post(
        "/auth/v1/login",
        json={
            "username": "staff",
            "password": "staff123"
        },
        headers={"X-Tenant-Name": "test_school"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]
