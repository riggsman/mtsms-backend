"""
Tests for teacher/lecturer management endpoints
"""
import pytest

def test_create_teacher(client, admin_token):
    """Test creating a new teacher"""
    response = client.post(
        "/api/v1/teachers",
        json={
            "firstname": "John",
            "lastname": "Smith",
            "email": "john.smith@test.com",
            "phone": "+1234567890",
            "dob": "1980-01-15",
            "gender": "Male",
            "address": "123 Teacher St",
            "department_id": 1,
            "employee_id": "TCH001",
            "qualification": "Ph.D. in Mathematics",
            "specialization": "Algebra"
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["employee_id"] == "TCH001"
    assert data["email"] == "john.smith@test.com"

def test_get_teachers(client, admin_token):
    """Test getting list of teachers"""
    # First create a teacher
    client.post(
        "/api/v1/teachers",
        json={
            "firstname": "John",
            "lastname": "Smith",
            "email": "john.smith@test.com",
            "phone": "+1234567890",
            "dob": "1980-01-15",
            "gender": "Male",
            "address": "123 Teacher St",
            "department_id": 1,
            "employee_id": "TCH001"
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    
    response = client.get(
        "/api/v1/teachers",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0
