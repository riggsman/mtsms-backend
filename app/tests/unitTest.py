from app.apis.tenant import create_tenant
from app.database.sessionManager import get_tenant_db
from app.schemas.tenant import TenantRequest


def test_create_student():
    db = get_tenant_db("tenant_1")
    student_data = {"name": "John Doe", "email": "john@example.com"}
    student = create_student(db=db, student=StudentRequest(**student_data))
    assert student.name == "John Doe"

def test_create_tenant():
    db = sessionLocal()
    tenant_data = {"name": "school_a", "database_url": "sqlite:///./tenant_school_a.db"}
    tenant = create_tenant(db=db, tenant=TenantRequest(**tenant_data))
    assert tenant.name == "school_a"
    db.close()