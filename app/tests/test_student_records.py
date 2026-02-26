"""
Tests for student record management endpoints
"""
import pytest

def test_create_student_record(client, admin_token):
    """Test creating a new student record"""
    response = client.post(
        "/api/v1/student-records",
        json={
            "student_id": "STU001",
            "course_code": "MATH101",
            "semester": "Fall 2024",
            "assignment": 15.0,
            "ca": 12.0,
            "exam": 50.0
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["student_id"] == "STU001"
    assert data["course_code"] == "MATH101"
    assert "total_score" in data
    assert "letter_grade" in data
    assert "gpa" in data

def test_get_student_records(client, admin_token):
    """Test getting list of student records"""
    # First create a record
    client.post(
        "/api/v1/student-records",
        json={
            "student_id": "STU001",
            "course_code": "MATH101",
            "semester": "Fall 2024",
            "assignment": 15.0,
            "ca": 12.0,
            "exam": 50.0
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    
    response = client.get(
        "/api/v1/student-records",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0

def test_update_student_record(client, admin_token):
    """Test updating a student record"""
    # Create a record first
    create_response = client.post(
        "/api/v1/student-records",
        json={
            "student_id": "STU001",
            "course_code": "MATH101",
            "semester": "Fall 2024",
            "assignment": 15.0,
            "ca": 12.0,
            "exam": 50.0
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    record_id = create_response.json()["id"]
    
    response = client.put(
        f"/api/v1/student-records/{record_id}",
        json={
            "exam": 60.0
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["exam"] == 60.0
    # Total should be recalculated
    assert "total_score" in data
