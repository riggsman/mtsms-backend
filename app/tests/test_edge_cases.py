"""
End-to-end and edge case tests for API
"""
import pytest

def test_invalid_tenant_header(client):
    """Test using a non-existent tenant name"""
    response = client.get(
        "/api/v1/users",
        headers={"X-Tenant-Name": "non_existent_tenant"}
    )
    # The system might return 404 if tenant database not found or 400 for invalid tenant
    assert response.status_code in [400, 404]

def test_expired_or_invalid_token(client):
    """Test using an invalid bearer token"""
    response = client.get(
        "/api/v1/users",
        headers={
            "Authorization": "Bearer invalid_token_here",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code in [401, 403]

def test_missing_auth_header(client):
    """Test accessing protected route without auth header"""
    response = client.get(
        "/api/v1/users",
        headers={"X-Tenant-Name": "test_school"}
    )
    assert response.status_code == 401

def test_rbac_student_accessing_admin_route(client, student_token):
    """Test that a student cannot access admin-only routes like user management"""
    response = client.get(
        "/api/v1/users",
        headers={
            "Authorization": f"Bearer {student_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 403

def test_validation_errors(client, admin_token):
    """Test creating a resource with missing required fields"""
    response = client.post(
        "/api/v1/users",
        json={"username": "missing_fields"}, # Missing email, lastname, etc.
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 422 # Pydantic validation error

def test_sql_injection_attempt(client, admin_token):
    """Edge case: attempt a basic SQL injection in a query parameter"""
    response = client.get(
        "/api/v1/users?username=' OR '1'='1",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    # Should handle it gracefully, likely return empty list or 200 with no matches
    assert response.status_code in [200, 400, 422]

def test_large_payload(client, admin_token):
    """Edge case: very large payload"""
    large_name = "A" * 10000
    response = client.post(
        "/api/v1/users",
        json={
            "firstname": large_name,
            "lastname": "Doe",
            "email": "large@test.com",
            "username": "largeuser",
            "password": "password123"
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    # Pydantic or DB constraints should catch this
    assert response.status_code in [400, 422]
