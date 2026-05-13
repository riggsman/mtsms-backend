from __future__ import annotations


def assert_ok(response, expected: int = 200):
    assert response.status_code == expected, response.text


def assert_auth_denied(response):
    assert response.status_code in (401, 403), response.text


def assert_validation_error(response):
    assert response.status_code in (400, 422), response.text
