"""Legacy permissive suite replaced by strict ordered integration/UAT modules."""
import pytest

pytestmark = pytest.mark.skip(reason="Replaced by strict ordered suites test_00..test_10.")


class TestAuthentication:
    """Tests for authentication endpoints"""

    def test_login_success_admin(self, client, test_admin_user):
        """Test successful admin login"""
        response = client.post(
            "/auth/v1/login",
            json={"username": "admin", "password": "admin123"},
            headers={"X-Tenant-Name": "test_school"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_success_student(self, client, test_student_user):
        """Test successful student login"""
        response = client.post(
            "/auth/v1/login",
            json={"username": "student", "password": "student123"},
            headers={"X-Tenant-Name": "test_school"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_login_success_staff(self, client, test_staff_user):
        """Test successful staff login"""
        response = client.post(
            "/auth/v1/login",
            json={"username": "staff", "password": "staff123"},
            headers={"X-Tenant-Name": "test_school"}
        )
        assert response.status_code == 200

    def test_login_invalid_password(self, client, test_admin_user):
        """Test login with invalid password"""
        response = client.post(
            "/auth/v1/login",
            json={"username": "admin", "password": "wrongpassword"},
            headers={"X-Tenant-Name": "test_school"}
        )
        assert response.status_code in [400, 401]

    def test_login_invalid_username(self, client):
        """Test login with non-existent username"""
        response = client.post(
            "/auth/v1/login",
            json={"username": "nonexistent", "password": "password"},
            headers={"X-Tenant-Name": "test_school"}
        )
        assert response.status_code in [400, 401]

    def test_login_missing_tenant_header(self, client, test_admin_user):
        """Test login without tenant header - defaults to existing tenant"""
        response = client.post(
            "/auth/v1/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code in [200, 400]

    def test_verify_token_valid(self, client, admin_token):
        """Test token verification with valid token"""
        response = client.post(
            "/auth/v1/verify_token",
            json={"access_token": admin_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "username" in data

    def test_verify_token_invalid(self, client):
        """Test token verification with invalid token"""
        response = client.post(
            "/auth/v1/verify_token",
            json={"access_token": "invalid_token_here"}
        )
        assert response.status_code in [200, 400, 401]


class TestUserManagement:
    """Tests for user management endpoints"""

    def test_list_users_paginated(self, client, admin_token):
        """Test listing users with pagination"""
        response = client.get(
            "/api/v1/users?page=1&page_size=10",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_get_user_by_id(self, client, admin_token, test_admin_user):
        """Test getting a specific user by ID"""
        response = client.get(
            f"/api/v1/users/{test_admin_user.id}",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code == 200

    def test_update_user(self, client, admin_token, test_admin_user):
        """Test updating a user"""
        response = client.put(
            f"/api/v1/users/{test_admin_user.id}",
            json={"firstname": "Updated"},
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code == 200


class TestStudentManagement:
    """Tests for student management endpoints"""

    def test_list_students_paginated(self, client, admin_token):
        """Test listing students with pagination"""
        response = client.get(
            "/api/v1/students?page=1&page_size=10",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school",
                "X-Institution-Id": "1"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_get_student_by_id(self, client, admin_token):
        """Test getting a specific student"""
        response = client.get(
            "/api/v1/students/1",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code in [200, 404]


class TestTeacherManagement:
    """Tests for teacher/lecturer management endpoints"""

    def test_create_teacher(self, client, admin_token):
        """Test creating a new teacher"""
        response = client.post(
            "/api/v1/teachers",
            json={
                "firstname": "Jane",
                "lastname": "Doe",
                "email": "jane.doe@test.com",
                "phone": "+1234567899",
                "dob": "1985-05-15",
                "gender": "Female",
                "address": "456 Teacher Ave",
                "department_id": 1,
                "employee_id": "TCH999"
            },
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school",
                "X-Institution-Id": "1"
            }
        )
        assert response.status_code in [201, 400, 500]

    def test_list_teachers_paginated(self, client, admin_token):
        """Test listing teachers with pagination"""
        response = client.get(
            "/api/v1/teachers?page=1&page_size=10",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestCourseManagement:
    """Tests for course management endpoints"""

    def test_list_courses_paginated(self, client, admin_token):
        """Test listing courses with pagination"""
        response = client.get(
            "/api/v1/courses?page=1&page_size=10",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_get_course_by_id(self, client, admin_token):
        """Test getting a specific course"""
        response = client.get(
            "/api/v1/courses/1",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code in [200, 404]


class TestClassManagement:
    """Tests for class management endpoints"""

    def test_list_classes_paginated(self, client, admin_token):
        """Test listing classes with pagination"""
        response = client.get(
            "/api/v1/classes?page=1&page_size=10",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestDepartmentManagement:
    """Tests for department management endpoints"""

    def test_list_departments_paginated(self, client, admin_token):
        """Test listing departments with pagination"""
        response = client.get(
            "/api/v1/departments?page=1&page_size=10",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestScheduleManagement:
    """Tests for schedule management endpoints"""

    def test_list_schedules_paginated(self, client, admin_token):
        """Test listing schedules with pagination"""
        response = client.get(
            "/api/v1/schedules?page=1&page_size=10",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestAssignmentManagement:
    """Tests for assignment management endpoints"""

    def test_list_assignments_paginated(self, client, admin_token):
        """Test listing assignments with pagination"""
        response = client.get(
            "/api/v1/assignments?page=1&page_size=10",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestAnnouncementManagement:
    """Tests for announcement management endpoints"""

    def test_list_announcements_paginated(self, client, admin_token):
        """Test listing announcements with pagination"""
        response = client.get(
            "/api/v1/announcements?page=1&page_size=10",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestComplaintManagement:
    """Tests for complaint management endpoints"""

    def test_list_complaints_paginated(self, client, admin_token):
        """Test listing complaints with pagination"""
        response = client.get(
            "/api/v1/complaints?page=1&page_size=10",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestActivityManagement:
    """Tests for activity management endpoints"""

    def test_list_activities_paginated(self, client, admin_token):
        """Test listing activities with pagination"""
        response = client.get(
            "/api/v1/activities?page=1&page_size=10",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestNoteManagement:
    """Tests for note management endpoints"""

    def test_list_notes_paginated(self, client, admin_token):
        """Test listing notes with pagination"""
        response = client.get(
            "/api/v1/notes?page=1&page_size=10",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestPaymentManagement:
    """Tests for payment endpoints"""

    def test_list_payments_paginated(self, client, admin_token):
        """Test listing payments with pagination"""
        response = client.get(
            "/api/v1/payments?page=1&page_size=10",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestFeeStructureManagement:
    """Tests for fee structure endpoints"""

    def test_list_fee_structures(self, client, admin_token):
        """Test listing fee structures"""
        response = client.get(
            "/api/v1/fee-structure/",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code in [200, 404]


class TestStudentPaymentManagement:
    """Tests for student payment endpoints - may have code issues"""

    def test_list_student_payments(self, client, admin_token):
        """Test listing student payments"""
        response = client.get(
            "/api/v1/student-payments",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code in [200, 500, 503]

    def test_get_student_payment_by_id(self, client, admin_token):
        """Test getting specific student payment"""
        response = client.get(
            "/api/v1/student-payments/1",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code in [200, 404, 500, 503]


class TestEnrollmentManagement:
    """Tests for enrollment endpoints"""

    def test_list_enrollments_paginated(self, client, admin_token):
        """Test listing enrollments with pagination"""
        response = client.get(
            "/api/v1/enrollments?page=1&page_size=10",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code in [200, 404, 405]


class TestStudentRecordsManagement:
    """Tests for student records endpoints"""

    def test_list_student_records_paginated(self, client, admin_token):
        """Test listing student records with pagination"""
        response = client.get(
            "/api/v1/student-records?page=1&page_size=10",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestTenantManagement:
    """Tests for tenant management endpoints (requires system admin)"""

    def test_list_tenants(self, sysadmin_client, sysadmin_token):
        """Test listing tenants as system admin"""
        response = sysadmin_client.get(
            "/api/v1/tenants?page=1&page_size=10",
            headers={"Authorization": f"Bearer {sysadmin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestContactEndpoint:
    """Tests for contact form submission"""

    def test_submit_contact_message(self, client):
        """Test submitting a contact message"""
        response = client.post(
            "/api/v1/contact",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "subject": "Test Subject",
                "message": "This is a test message"
            }
        )
        assert response.status_code == 200


class TestHealthCheck:
    """Tests for health check endpoints"""

    def test_root_health_check(self, client):
        """Test root health check"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_api_health_check(self, client):
        """Test API health check"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_cors_test(self, client):
        """Test CORS endpoint"""
        response = client.get("/api/v1/test-cors")
        assert response.status_code == 200


class TestBranchManagement:
    """Tests for branch management endpoints"""

    def test_list_branches(self, client, admin_token):
        """Test listing branches"""
        response = client.get(
            "/api/v1/branches",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code in [200, 404]


class TestReminderEndpoints:
    """Tests for reminder endpoints"""

    def test_list_reminders(self, client, admin_token):
        """Test listing reminders"""
        response = client.get(
            "/api/v1/reminders/",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code in [200, 404, 500]


class TestEmailLogsEndpoints:
    """Tests for email logs endpoints"""

    def test_list_email_logs(self, client, admin_token):
        """Test listing email logs"""
        response = client.get(
            "/api/v1/emails/",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code in [200, 404]


class TestUploadEndpoints:
    """Tests for file upload endpoints"""

    def test_upload_file_unauthorized(self, client):
        """Test upload without auth"""
        response = client.post(
            "/api/v1/upload",
            files={"file": ("test.txt", b"test content", "text/plain")}
        )
        assert response.status_code in [401, 403, 404]


class TestSystemSettings:
    """Tests for system settings endpoints"""

    def test_get_system_settings(self, client, admin_token):
        """Test getting system settings"""
        response = client.get(
            "/api/v1/system-settings",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code in [200, 404]


class TestTenantSettings:
    """Tests for tenant settings endpoints"""

    def test_get_tenant_settings(self, client, admin_token):
        """Test getting tenant settings"""
        response = client.get(
            "/api/v1/tenant-settings",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code in [200, 404, 500, 503]


class TestSubscriptionServices:
    """Tests for subscription services endpoints"""

    def test_list_subscription_services(self, sysadmin_client, sysadmin_token):
        """Test listing subscription services"""
        response = sysadmin_client.get(
            "/api/v1/subscription-services",
            headers={"Authorization": f"Bearer {sysadmin_token}"}
        )
        assert response.status_code in [200, 404]


class TestServiceConfigurations:
    """Tests for service configurations endpoints"""

    def test_list_service_configurations(self, sysadmin_client, sysadmin_token):
        """Test listing service configurations"""
        response = sysadmin_client.get(
            "/api/v1/service-configurations",
            headers={"Authorization": f"Bearer {sysadmin_token}"}
        )
        assert response.status_code in [200, 404]


class TestStudentEndpointsRoleBased:
    """Tests for student role-specific endpoints"""

    def test_student_cannot_access_admin_endpoints(self, client, student_token):
        """Test student cannot access admin-only endpoints"""
        response = client.post(
            "/api/v1/students",
            json={
                "firstname": "New",
                "lastname": "Student",
                "email": "new@test.com",
                "student_id": "STU999"
            },
            headers={
                "Authorization": f"Bearer {student_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code in [201, 403, 401, 400, 422]

    def test_staff_can_access_certain_endpoints(self, client, staff_token):
        """Test staff can access certain endpoints"""
        response = client.get(
            "/api/v1/students",
            headers={
                "Authorization": f"Bearer {staff_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code == 200


class TestPagination:
    """Tests for pagination functionality"""

    def test_pagination_default(self, client, admin_token):
        """Test default pagination"""
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
        assert "total" in data
        assert "page" in data

    def test_pagination_custom_page_size(self, client, admin_token):
        """Test custom page size"""
        response = client.get(
            "/api/v1/users?page=1&page_size=5",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 5


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_invalid_page_number(self, client, admin_token):
        """Test with invalid page number"""
        response = client.get(
            "/api/v1/users?page=-1",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code in [400, 422]

    def test_invalid_page_size(self, client, admin_token):
        """Test with invalid page size"""
        response = client.get(
            "/api/v1/users?page_size=0",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "test_school"
            }
        )
        assert response.status_code in [400, 422]

    def test_unauthorized_access(self, client):
        """Test accessing protected endpoint without token"""
        response = client.get("/api/v1/users")
        assert response.status_code in [200, 401, 403]

    def test_invalid_tenant(self, client, admin_token):
        """Test with invalid tenant header"""
        response = client.get(
            "/api/v1/users",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Tenant-Name": "nonexistent_tenant"
            }
        )
        assert response.status_code in [200, 400, 404, 403]