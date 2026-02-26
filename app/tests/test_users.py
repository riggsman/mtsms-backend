"""
Tests for user management endpoints
"""
import pytest
from app.models.user import User

def test_create_user(client, admin_token):
    """Test creating a new user"""
    response = client.post(
        "/api/v1/users",
        json={
            "firstname": "John",
            "lastname": "Doe",
            "email": "john.doe@test.com",
            "phone": "+1234567890",
            "username": "johndoe",
            "password": "password123",
            "role": "staff",
            "gender": "Male",
            "address": "123 Test St"
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "johndoe"
    assert data["email"] == "john.doe@test.com"
    assert "password" not in data

def test_get_users(client, admin_token, test_admin_user):
    """Test getting list of users"""
    response = client.get(
        "/api/v1/users",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0

def test_get_user_by_id(client, admin_token, test_admin_user):
    """Test getting a specific user"""
    response = client.get(
        f"/api/v1/users/{test_admin_user.id}",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_admin_user.id
    assert data["username"] == "admin"

def test_update_user(client, admin_token, test_admin_user):
    """Test updating a user"""
    response = client.put(
        f"/api/v1/users/{test_admin_user.id}",
        json={
            "firstname": "Updated",
            "lastname": "Admin"
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["firstname"] == "Updated"

def test_delete_user(client, admin_token, test_admin_user):
    """Test deleting a user"""
    response = client.delete(
        f"/api/v1/users/{test_admin_user.id}",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 204

def test_create_user_unauthorized(client, staff_token):
    """Test that staff cannot create users"""
    response = client.post(
        "/api/v1/users",
        json={
            "firstname": "John",
            "lastname": "Doe",
            "email": "john.doe@test.com",
            "phone": "+1234567890",
            "username": "johndoe",
            "password": "password123",
            "role": "staff",
            "gender": "Male",
            "address": "123 Test St"
        },
        headers={
            "Authorization": f"Bearer {staff_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 403
