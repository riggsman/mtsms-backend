"""
Tests for authentication endpoints
"""
import pytest
from fastapi.testclient import TestClient

def test_login_success(client, test_admin_user):
    """Test successful login"""
    response = client.post(
        "/auth/v1/login",
        json={
            "username": "admin",
            "password": "admin123"
        },
        headers={"X-Tenant-Name": "test_school"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(client, test_admin_user):
    """Test login with invalid credentials"""
    response = client.post(
        "/auth/v1/login",
        json={
            "username": "admin",
            "password": "wrongpassword"
        },
        headers={"X-Tenant-Name": "test_school"}
    )
    assert response.status_code == 401

def test_login_missing_tenant(client, test_admin_user):
    """Test login without tenant header"""
    response = client.post(
        "/auth/v1/login",
        json={
            "username": "admin",
            "password": "admin123"
        }
    )
    assert response.status_code == 400

def test_verify_token_valid(client, admin_token):
    """Test token verification with valid token"""
    response = client.post(
        "/auth/v1/verify_token",
        json={"access_token": admin_token}
    )
    assert response.status_code == 200
    data = response.json()
    assert "valid" in data or "username" in data

def test_verify_token_invalid(client):
    """Test token verification with invalid token"""
    response = client.post(
        "/auth/v1/verify_token",
        json={"access_token": "invalid_token"}
    )
    assert response.status_code in [400, 401]
