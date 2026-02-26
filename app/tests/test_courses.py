"""
Tests for course management endpoints
"""
import pytest

def test_create_course(client, admin_token):
    """Test creating a new course"""
    response = client.post(
        "/api/v1/courses",
        json={
            "name": "Mathematics 101",
            "code": "MATH101",
            "description": "Introduction to Algebra",
            "department_id": 1,
            "credits": 3
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == "MATH101"
    assert data["name"] == "Mathematics 101"

def test_get_courses(client, admin_token):
    """Test getting list of courses"""
    # First create a course
    client.post(
        "/api/v1/courses",
        json={
            "name": "Mathematics 101",
            "code": "MATH101",
            "department_id": 1,
            "credits": 3
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    
    response = client.get(
        "/api/v1/courses",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0

def test_get_course_by_id(client, admin_token):
    """Test getting a specific course"""
    # Create a course first
    create_response = client.post(
        "/api/v1/courses",
        json={
            "name": "Mathematics 101",
            "code": "MATH101",
            "department_id": 1,
            "credits": 3
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    course_id = create_response.json()["id"]
    
    response = client.get(
        f"/api/v1/courses/{course_id}",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == course_id

def test_update_course(client, admin_token):
    """Test updating a course"""
    # Create a course first
    create_response = client.post(
        "/api/v1/courses",
        json={
            "name": "Mathematics 101",
            "code": "MATH101",
            "department_id": 1,
            "credits": 3
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    course_id = create_response.json()["id"]
    
    response = client.put(
        f"/api/v1/courses/{course_id}",
        json={
            "name": "Advanced Mathematics 101"
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Advanced Mathematics 101"

def test_delete_course(client, admin_token):
    """Test deleting a course"""
    # Create a course first
    create_response = client.post(
        "/api/v1/courses",
        json={
            "name": "Mathematics 101",
            "code": "MATH101",
            "department_id": 1,
            "credits": 3
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    course_id = create_response.json()["id"]
    
    response = client.delete(
        f"/api/v1/courses/{course_id}",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 204
