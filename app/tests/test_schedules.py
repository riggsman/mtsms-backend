"""
Tests for schedule management endpoints
"""
import pytest

def test_create_schedule(client, admin_token):
    """Test creating a new schedule"""
    response = client.post(
        "/api/v1/schedules",
        json={
            "course_name": "Mathematics 101",
            "instructor": "Prof. Smith",
            "day": "Monday",
            "start_time": "09:00",
            "end_time": "10:30",
            "room": "Room 101",
            "capacity": 30,
            "description": "Introduction to Algebra"
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["course_name"] == "Mathematics 101"
    assert data["day"] == "Monday"

def test_get_schedules(client, admin_token):
    """Test getting list of schedules"""
    # First create a schedule
    client.post(
        "/api/v1/schedules",
        json={
            "course_name": "Mathematics 101",
            "instructor": "Prof. Smith",
            "day": "Monday",
            "start_time": "09:00",
            "end_time": "10:30",
            "room": "Room 101"
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    
    response = client.get(
        "/api/v1/schedules",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0

def test_get_schedule_by_id(client, admin_token):
    """Test getting a specific schedule"""
    # Create a schedule first
    create_response = client.post(
        "/api/v1/schedules",
        json={
            "course_name": "Mathematics 101",
            "instructor": "Prof. Smith",
            "day": "Monday",
            "start_time": "09:00",
            "end_time": "10:30",
            "room": "Room 101"
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    schedule_id = create_response.json()["id"]
    
    response = client.get(
        f"/api/v1/schedules/{schedule_id}",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == schedule_id

def test_update_schedule(client, admin_token):
    """Test updating a schedule"""
    # Create a schedule first
    create_response = client.post(
        "/api/v1/schedules",
        json={
            "course_name": "Mathematics 101",
            "instructor": "Prof. Smith",
            "day": "Monday",
            "start_time": "09:00",
            "end_time": "10:30",
            "room": "Room 101"
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    schedule_id = create_response.json()["id"]
    
    response = client.put(
        f"/api/v1/schedules/{schedule_id}",
        json={
            "room": "Room 202"
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["room"] == "Room 202"

def test_delete_schedule(client, admin_token):
    """Test deleting a schedule"""
    # Create a schedule first
    create_response = client.post(
        "/api/v1/schedules",
        json={
            "course_name": "Mathematics 101",
            "instructor": "Prof. Smith",
            "day": "Monday",
            "start_time": "09:00",
            "end_time": "10:30",
            "room": "Room 101"
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    schedule_id = create_response.json()["id"]
    
    response = client.delete(
        f"/api/v1/schedules/{schedule_id}",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 204

def test_get_schedules_by_instructor(client, admin_token):
    """Test getting schedules by instructor"""
    # Create schedules for different instructors
    client.post(
        "/api/v1/schedules",
        json={
            "course_name": "Mathematics 101",
            "instructor": "Prof. Smith",
            "day": "Monday",
            "start_time": "09:00",
            "end_time": "10:30",
            "room": "Room 101"
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    
    response = client.get(
        "/api/v1/schedules/instructor/Prof. Smith",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all(s["instructor"] == "Prof. Smith" for s in data)
