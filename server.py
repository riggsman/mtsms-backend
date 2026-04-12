from fastapi import FastAPI, Request
from fastapi.responses import Response
from app.database.base import DefaultBase, engine,DefaultSessionLocal
from app.database.sessionManager import BaseModel_Base
from app.dependencies import auth
from app.routes import (
    login,
    register_user,
    tenants,
    students,
    teachers,
    courses,
    schedules,
    activities,
    announcements,
    assignments,
    users,
    notes,
    classes,
    enrollments,
    student_records,
    complaints,
    tenant_settings,
    system_admin,
    system_config,
    contact,
    system_settings,
    subscription_services,
    service_configurations,
    uploads,
    departments,
    email_logs,
    reminders,
    payments,
    branches,
    fee_structure,
    # schools,  # Disabled - schools table was dropped by migrations
    student_payments,
    certificates,
)
from fastapi.middleware.cors import CORSMiddleware
from app.conf.config import settings
from scripts.populate_classes import seed_default_classes

# Initialize FastAPI app
app = FastAPI(
    title="School Management System",
    description="A multi-tenant school management system using FastAPI.",
    version="1.0.0",
)

# CORS middleware - handle OPTIONS before any other processing
@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    # Log all requests
    print(f"[SERVER] {request.method} {request.url.path}")
    
    # Handle preflight OPTIONS requests
    if request.method == "OPTIONS":
        print(f"[SERVER] CORS preflight for: {request.url.path}")
        response = Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
            }
        )
        return response
    
    # Process other requests
    response = await call_next(request)
    
    # Add CORS headers to response
    response.headers["Access-Control-Allow-Origin"] = "*"
    
    return response

#CREATING DIRECTORIES
import os
from pathlib import Path

# UPLOAD_DIR = Path("uploads")
# os.makedirs(UPLOAD_DIR, exist_ok=True)
# LOGO_DIR = UPLOAD_DIR / "logos"
# os.makedirs(LOGO_DIR, exist_ok=True)
# PROFILE_PICTURE_DIR = UPLOAD_DIR / "profile_pictures"
# os.makedirs(PROFILE_PICTURE_DIR, exist_ok=True)
# NOTES_DIR = UPLOAD_DIR / "notes"
# os.makedirs(NOTES_DIR, exist_ok=True)
# PDF_DIR = UPLOAD_DIR / NOTES_DIR / "pdf"
# os.makedirs(PDF_DIR, exist_ok=True)
# WORD_DIR = UPLOAD_DIR / NOTES_DIR / "word"
# os.makedirs(WORD_DIR, exist_ok=True)

# Include routers
# Authentication routes
app.include_router(login.login, prefix="/auth/v1", tags=["Authentication"])
app.include_router(register_user.register, prefix="/api/v1", tags=["Registration"])

# Core entity routes
app.include_router(tenants.tenant, prefix="/api/v1", tags=["tenants"])
app.include_router(students.student, prefix="/api/v1", tags=["students"])
app.include_router(teachers.teacher, prefix="/api/v1", tags=["teachers"])
app.include_router(courses.course, prefix="/api/v1", tags=["courses"])
app.include_router(departments.department_router, prefix="/api/v1", tags=["departments"])
app.include_router(schedules.schedule, prefix="/api/v1", tags=["schedules"])
app.include_router(activities.activity, prefix="/api/v1", tags=["activities"])
app.include_router(users.user, prefix="/api/v1", tags=["users"])
app.include_router(classes.class_router, prefix="/api/v1", tags=["classes"])
app.include_router(enrollments.enrollment, prefix="/api/v1", tags=["enrollments"])
app.include_router(student_records.student_record, prefix="/api/v1", tags=["student-records"])

# Academic routes
app.include_router(assignments.assignment, prefix="/api/v1", tags=["assignments"])
app.include_router(notes.note_router, prefix="/api/v1", tags=["notes"])
app.include_router(announcements.announcement_router, prefix="/api/v1", tags=["announcements"])

# Support routes
app.include_router(complaints.complaint, prefix="/api/v1", tags=["complaints"])

# Configuration routes
app.include_router(tenant_settings.tenant_settings_router, prefix="/api/v1", tags=["tenant-settings"])
app.include_router(branches.router, prefix="/api/v1", tags=["branches"])

# File upload routes
app.include_router(uploads.upload_router, prefix="/api/v1", tags=["uploads"])

# System admin routes (global database)
app.include_router(system_admin.system_admin, prefix="/api/v1", tags=["system-admin"])
app.include_router(system_config.system_config, prefix="/api/v1", tags=["system-config"])

# Public / general routes
app.include_router(contact.contact, prefix="/api/v1", tags=["contact"])


app.include_router(system_settings.system_settings, prefix="/api/v1", tags=["system-settings"])

# Subscription services routes
app.include_router(
    subscription_services.subscription_services,
    prefix="/api/v1",
    tags=["subscription-services"],
)

# Service configurations routes
app.include_router(
    service_configurations.service_configurations,
    prefix="/api/v1",
    tags=["service-configurations"],
)

# Email logs routes
app.include_router(email_logs.router, prefix="/api/v1", tags=["email-logs"])

# Reminder routes
app.include_router(reminders.reminder_router, prefix="/api/v1", tags=["reminders"])

# Payment routes
app.include_router(payments.payment, prefix="/api/v1", tags=["payments"])

# Fee Structure routes
app.include_router(fee_structure.fee_structure, prefix="/api/v1", tags=["fee-structure"])

# Schools routes (Engineering, Business, Biomedical with levels) - DISABLED
# app.include_router(schools.router, prefix="/api/v1", tags=["schools"])

# Student Payments routes
app.include_router(student_payments.router, prefix="/api/v1", tags=["student-payments"])

# Certificate routes (transcripts and result slips)
app.include_router(certificates.certificate_router, prefix="/api/v1", tags=["certificates"])

# Import models to register them with metadata for table creation
# from app.models.school import School, SchoolFee  # Tables dropped by migrations
from app.models.fee_structure import FeeStructure, FeeInstallment
from app.models.student_payment import StudentPayment, StudentPaymentInstallment

# Create metadata database tables (if they don't exist)
@app.on_event("startup")
def startup():
    DefaultBase.metadata.create_all(bind=engine)
    BaseModel_Base.metadata.create_all(bind=engine)
    # Seed default data
    with DefaultSessionLocal() as session:
        seed_default_classes(session)
    
    # Start schedule reminder scheduler
    try:
        from app.authentication.authenticator import verify_password, hash_password
        from app.tasks.schedule_reminder_task import start_schedule_reminder_scheduler
        print("SYSTEM ADMIN PASSWORD ", hash_password("admin123"))  # Example usage of hash_password to ensure it's working
        start_schedule_reminder_scheduler()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to start reminder scheduler: {str(e)}")

@app.on_event("shutdown")
def shutdown():
    """Stop background tasks on shutdown"""
    try:
        from app.tasks.schedule_reminder_task import stop_schedule_reminder_scheduler
        stop_schedule_reminder_scheduler()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error stopping reminder scheduler: {str(e)}")

# Health check endpoint
@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok", "message": "School Management System is running!"}

@app.get("/api/v1/health", tags=["health"])
def api_health_check():
    return {"status": "ok", "message": "API is running!"}

@app.get("/api/v1/test-cors", tags=["health"])
def test_cors():
    """Test endpoint to verify CORS is working"""
    return {"status": "ok", "message": "CORS test successful!"}