from __future__ import annotations

from typing import Any, Dict, Optional


def auth_headers(token: Optional[str] = None, tenant: str = "test_school", institution_id: Optional[int] = 1) -> Dict[str, str]:
    headers: Dict[str, str] = {"X-Tenant-Name": tenant}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if institution_id is not None:
        headers["X-Institution-Id"] = str(institution_id)
    return headers


def request_json(client, method: str, path: str, token: Optional[str] = None, tenant: str = "test_school", json: Any = None):
    return client.request(method, path, json=json, headers=auth_headers(token=token, tenant=tenant))
