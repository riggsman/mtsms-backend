import os
import pytest

from server import app


@pytest.mark.integration
def test_mounted_route_families_have_ordered_suite_files():
    mounted_paths = {r.path for r in app.routes}

    required_route_families = {
        "/auth/v1/": "test_01_auth_and_tenant_context.py",
        "/api/v1/tenant-settings": "test_02_tenant_system_setup.py",
        "/api/v1/users": "test_03_user_role_lifecycle.py",
        "/api/v1/students": "test_04_academic_master_data.py",
        "/api/v1/schedules": "test_05_schedule_enrollment_records.py",
        "/api/v1/assignments": "test_06_learning_ops.py",
        "/api/v1/payments": "test_07_finance_ops.py",
        "/api/v1/payroll/": "test_08_payroll_flow.py",
        "/api/v1/system/": "test_09_system_admin_services.py",
    }

    tests_dir = os.path.dirname(__file__)
    missing = []
    for family_prefix, suite_file in required_route_families.items():
        family_is_mounted = any(path.startswith(family_prefix) for path in mounted_paths)
        if not family_is_mounted:
            continue
        suite_path = os.path.join(tests_dir, suite_file)
        if not os.path.exists(suite_path):
            missing.append((family_prefix, suite_file))

    assert not missing, f"Missing suite files for mounted families: {missing}"
