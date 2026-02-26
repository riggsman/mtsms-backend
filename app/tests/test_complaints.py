"""
Tests for complaint management endpoints
"""
import pytest

def test_create_complaint(client, admin_token):
    """Test creating a new complaint"""
    response = client.post(
        "/api/v1/complaints",
        json={
            "student_id": "STU001",
            "complaint_type": "academic",
            "caption": "Grade Issue",
            "contents": "I believe my grade is incorrect",
            "is_anonymous": False,
            "screenshots": []
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["complaint_type"] == "academic"
    assert data["status"] == "pending"

def test_get_complaints(client, admin_token):
    """Test getting list of complaints"""
    # First create a complaint
    client.post(
        "/api/v1/complaints",
        json={
            "student_id": "STU001",
            "complaint_type": "academic",
            "caption": "Grade Issue",
            "contents": "I believe my grade is incorrect",
            "is_anonymous": False
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    
    response = client.get(
        "/api/v1/complaints",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0

def test_update_complaint_status(client, admin_token):
    """Test updating complaint status"""
    # Create a complaint first
    create_response = client.post(
        "/api/v1/complaints",
        json={
            "student_id": "STU001",
            "complaint_type": "academic",
            "caption": "Grade Issue",
            "contents": "I believe my grade is incorrect",
            "is_anonymous": False
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    complaint_id = create_response.json()["id"]
    
    response = client.put(
        f"/api/v1/complaints/{complaint_id}",
        json={
            "status": "addressed",
            "resolved_by": "Admin User",
            "resolver_role": "admin"
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "addressed"
    assert data["resolved_by"] == "Admin User"

def test_get_student_complaints(client, admin_token):
    """Test getting complaints for a specific student"""
    # Create complaints for a student
    client.post(
        "/api/v1/complaints",
        json={
            "student_id": "STU001",
            "complaint_type": "academic",
            "caption": "Grade Issue",
            "contents": "I believe my grade is incorrect",
            "is_anonymous": False
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    
    response = client.get(
        "/api/v1/complaints/student/STU001",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all(c["student_id"] == "STU001" for c in data)
