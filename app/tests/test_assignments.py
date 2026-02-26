"""
Tests for assignment management endpoints
"""
import pytest
from datetime import date, timedelta

def test_create_assignment(client, admin_token):
    """Test creating a new assignment"""
    due_date = (date.today() + timedelta(days=7)).isoformat()
    response = client.post(
        "/api/v1/assignments",
        json={
            "course_code": "MATH101",
            "title": "Algebra Assignment 1",
            "description": "Complete exercises 1-10",
            "due_date": due_date,
            "late_penalty": 10,
            "created_by": "Prof. Smith"
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Algebra Assignment 1"
    assert data["course_code"] == "MATH101"

def test_get_assignments(client, admin_token):
    """Test getting list of assignments"""
    # First create an assignment
    due_date = (date.today() + timedelta(days=7)).isoformat()
    client.post(
        "/api/v1/assignments",
        json={
            "course_code": "MATH101",
            "title": "Algebra Assignment 1",
            "description": "Complete exercises 1-10",
            "due_date": due_date,
            "created_by": "Prof. Smith"
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    
    response = client.get(
        "/api/v1/assignments",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0

def test_submit_assignment(client, admin_token):
    """Test submitting an assignment"""
    # First create an assignment
    due_date = (date.today() + timedelta(days=7)).isoformat()
    create_response = client.post(
        "/api/v1/assignments",
        json={
            "course_code": "MATH101",
            "title": "Algebra Assignment 1",
            "description": "Complete exercises 1-10",
            "due_date": due_date,
            "created_by": "Prof. Smith"
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assignment_id = create_response.json()["id"]
    
    # Submit assignment
    response = client.post(
        "/api/v1/assignments/submit",
        json={
            "assignment_id": assignment_id,
            "student_id": "STU001",
            "submission_file": "base64_encoded_file_data"
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["student_id"] == "STU001"
    assert data["assignment_id"] == assignment_id

def test_get_student_submissions(client, admin_token):
    """Test getting student submissions"""
    # Create and submit assignment
    due_date = (date.today() + timedelta(days=7)).isoformat()
    create_response = client.post(
        "/api/v1/assignments",
        json={
            "course_code": "MATH101",
            "title": "Algebra Assignment 1",
            "description": "Complete exercises 1-10",
            "due_date": due_date,
            "created_by": "Prof. Smith"
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assignment_id = create_response.json()["id"]
    
    client.post(
        "/api/v1/assignments/submit",
        json={
            "assignment_id": assignment_id,
            "student_id": "STU001",
            "submission_file": "base64_encoded_file_data"
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    
    response = client.get(
        "/api/v1/assignments/submissions/student/STU001",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all(s["student_id"] == "STU001" for s in data)
