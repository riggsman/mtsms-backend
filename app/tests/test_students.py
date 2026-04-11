"""
Tests for student management endpoints
"""
import pytest

@pytest.fixture
def test_student_data():
    return {
        "firstname": "Student",
        "lastname": "One",
        "dob": "2000-01-01",
        "gender": "Male",
        "address": "Student Address",
        "email": "student1@test.com",
        "phone": "+1234567893",
        "student_id": "STU001",
        "class_id": 1,
        "level": "100",
        "department_id": 1,
        "academic_year_id": 1,
        "guardian_id": 1
    }

def test_create_student(client, admin_token, test_student_data):
    """Test creating a new student"""
    response = client.post(
        "/api/v1/students",
        json=test_student_data,
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school",
            "X-Institution-Id": "1"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["student_id"] == "STU001"
    assert data["email"] == "student1@test.com"

def test_list_students(client, admin_token):
    """Test listing students"""
    response = client.get(
        "/api/v1/students",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school",
            "X-Institution-Id": "1"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data

def test_get_student_unauthorized(client, staff_token, test_student_data):
    """Test that staff can create student but maybe not delete (depending on roles)"""
    # Assuming staff can create students based on require_any_role(ADMIN, STAFF, SUPER_ADMIN)
    response = client.post(
        "/api/v1/students",
        json={**test_student_data, "email": "staff_created@test.com", "student_id": "STU002"},
        headers={
            "Authorization": f"Bearer {staff_token}",
            "X-Tenant-Name": "test_school",
            "X-Institution-Id": "1"
        }
    )
    assert response.status_code == 201

def test_student_id_duplication(client, admin_token, test_student_data):
    """Test edge case: duplicate student_id"""
    # First creation
    client.post(
        "/api/v1/students",
        json=test_student_data,
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school",
            "X-Institution-Id": "1"
        }
    )
    # Second creation with same student_id
    response = client.post(
        "/api/v1/students",
        json={**test_student_data, "email": "another@test.com"},
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school",
            "X-Institution-Id": "1"
        }
    )
    assert response.status_code == 409
