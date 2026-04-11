"""
Tests for tenant management endpoints
"""
import pytest

def test_create_tenant(sysadmin_client, sysadmin_token):
    """Test creating a new tenant as system admin"""
    import time
    unique_name = f"new_school_{int(time.time() * 1000)}"
    response = sysadmin_client.post(
        "/api/v1/tenants",
        json={
            "name": unique_name,
            "category": "HI"
        },
        headers={"Authorization": f"Bearer {sysadmin_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == unique_name
    assert data["category"] == "HI"

def test_get_all_tenants(sysadmin_client, sysadmin_token, test_tenant):
    """Test getting all tenants"""
    response = sysadmin_client.get(
        "/api/v1/tenants",
        headers={"Authorization": f"Bearer {sysadmin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1

def test_get_tenant_by_id(sysadmin_client, sysadmin_token, test_tenant):
    """Test getting a tenant by ID"""
    response = sysadmin_client.get(
        f"/api/v1/tenants/{test_tenant.id}",
        headers={"Authorization": f"Bearer {sysadmin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_tenant.id

def test_update_tenant(sysadmin_client, sysadmin_token, test_tenant):
    """Test updating a tenant"""
    response = sysadmin_client.put(
        f"/api/v1/tenants/{test_tenant.id}",
        json={"name": "updated_school"},
        headers={"Authorization": f"Bearer {sysadmin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "updated_school"

def test_create_tenant_access_denied(client, admin_token):
    """Test that tenant admin cannot create another tenant"""
    import time
    unique_name = f"unauthorized_school_{int(time.time() * 1000)}"
    response = client.post(
        "/api/v1/tenants",
        json={
            "name": unique_name,
            "category": "SI"
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code == 403
