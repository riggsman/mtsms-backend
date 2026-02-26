# Backend API Tests

This directory contains comprehensive tests for the FastAPI backend.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run tests:
```bash
pytest
```

3. Run with coverage:
```bash
pytest --cov=app --cov-report=html
```

4. Run specific test file:
```bash
pytest app/tests/test_auth.py
```

## Test Structure

- `conftest.py` - Pytest fixtures and configuration
- `test_auth.py` - Authentication endpoint tests
- `test_users.py` - User management endpoint tests
- `test_schedules.py` - Schedule management endpoint tests
- `test_courses.py` - Course management endpoint tests
- `test_complaints.py` - Complaint management endpoint tests
- `test_assignments.py` - Assignment management endpoint tests

## Test Coverage

The tests cover:
- ✅ Authentication (login, token verification)
- ✅ User CRUD operations
- ✅ Schedule CRUD operations
- ✅ Course CRUD operations
- ✅ Complaint CRUD operations
- ✅ Assignment CRUD and submission operations
- ✅ Authorization and role-based access control
- ✅ Error handling and validation

## Running Tests in CI/CD

Add to your CI/CD pipeline:
```yaml
- name: Run tests
  run: |
    pytest --cov=app --cov-report=xml
```
