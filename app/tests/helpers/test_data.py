"""Deterministic request payload builders used by tests."""

from __future__ import annotations


def auth_login_payload(username: str = "admin", password: str = "admin123") -> dict:
    return {"username": username, "password": password}


def verify_token_payload(access_token: str) -> dict:
    return {"access_token": access_token}


def refresh_token_payload(refresh_token: str) -> dict:
    return {"refresh_token": refresh_token}


def tenant_settings_update_payload() -> dict:
    return {
        "email_reminder_time": 15,
        "branches_enabled": False,
        "payroll_auto_generate_codes": False,
    }


def branch_create_payload() -> dict:
    return {"name": "Main Campus", "code": "MAIN", "sort_order": 1, "is_active": True}


def payroll_generate_codes_payload(teacher_id: int, course_code: str) -> dict:
    return {"teacher_id": teacher_id, "course_code": course_code}


def payroll_clock_in_payload(course_code: str, clock_in_code: str) -> dict:
    return {"course_code": course_code, "clock_in_code": clock_in_code}


def payroll_clock_out_payload(course_code: str, clock_out_code: str) -> dict:
    return {"course_code": course_code, "clock_out_code": clock_out_code}
