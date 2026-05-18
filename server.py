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
    feature_matrix,
    subscription_plans,
    uploads,
    departments,
    email_logs,
    reminders,
    payments,
    branches,
    fee_structure,
    schools,
    student_payments,
    certificates,
    specializations,
    payroll,
    student_dashboard,
    staff_dashboard,
    leave_requests,
    utility_requests,
    notifications,
    academic_year_management,
    academic_calendar,
    promotions,
    hr,
    correspondence,
    parent_portal,
)
from fastapi.middleware.cors import CORSMiddleware
from app.conf.config import settings
from app.services.startup_seed import run_startup_seed

# Initialize FastAPI app
app = FastAPI(
    title="School Management System",
    description="A multi-tenant school management system using FastAPI.",
    version="1.0.0",
)

# CORS middleware - allow Authorization header
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "X-Tenant-Name", "X-Requested-With", "X-Institution-Id"],
)

# Socket.IO setup - try to initialize, fallback gracefully
sio = None

try:
    import socketio
    sio = socketio.AsyncServer(
        async_mode='asgi',
        cors_allowed_origins='*',
        logger=False,
        engineio_logger=False,
    )
    # Store sio for later use in routes
    app.state.sio = sio
    print("[SERVER] Socket.IO enabled")
except ImportError:
    print("[SERVER] Socket.IO not installed")
except Exception as e:
    print(f"[SERVER] Socket.IO error: {e}")

# Export for uvicorn
# Use: uvicorn server:app --host 0.0.0.0 --port 8000 --reload

from app.middleware.analytics_middleware import analytics_middleware as platform_analytics_middleware
from app.middleware.platform_error_handlers import register_platform_error_handlers

register_platform_error_handlers(app)


@app.middleware("http")
async def platform_analytics_http_middleware(request: Request, call_next):
    return await platform_analytics_middleware(request, call_next)


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
                "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Tenant-Name, X-Requested-With, X-Institution-Id",
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
app.include_router(specializations.specialization_router, prefix="/api/v1", tags=["specializations"])
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

app.include_router(
    feature_matrix.feature_matrix,
    prefix="/api/v1",
    tags=["feature-matrix"],
)

# Subscription plans routes
app.include_router(
    subscription_plans.router,
    prefix="/api/v1",
    tags=["subscription-plans"],
)

# Email logs routes
app.include_router(email_logs.router, prefix="/api/v1", tags=["email-logs"])

# Reminder routes
app.include_router(reminders.reminder_router, prefix="/api/v1", tags=["reminders"])

# Payment routes
app.include_router(payments.payment, prefix="/api/v1", tags=["payments"])

# Fee Structure routes
app.include_router(fee_structure.fee_structure, prefix="/api/v1", tags=["fee-structure"])

app.include_router(schools.router, prefix="/api/v1", tags=["schools"])

# Student Payments routes
app.include_router(student_payments.router, prefix="/api/v1", tags=["student-payments"])

# Certificate routes (transcripts and result slips)
app.include_router(certificates.certificate_router, prefix="/api/v1", tags=["certificates"])

app.include_router(payroll.router, prefix="/api/v1", tags=["payroll"])
app.include_router(student_dashboard.router, prefix="/api/v1", tags=["student-dashboard"])
app.include_router(staff_dashboard.router, prefix="/api/v1", tags=["staff-dashboard"])

# Request management routes
app.include_router(leave_requests.leave_router, prefix="/api/v1", tags=["leave-requests"])
app.include_router(utility_requests.utility_router, prefix="/api/v1", tags=["utility-requests"])

app.include_router(
    notifications.notifications_router,
    prefix="/api/v1",
    tags=["notifications"],
)
app.include_router(
    academic_year_management.academic_year_router,
    prefix="/api/v1",
    tags=["academic-years"],
)
app.include_router(
    academic_calendar.academic_calendar_router,
    prefix="/api/v1",
    tags=["academic-calendar"],
)
app.include_router(
    promotions.promotions_router,
    prefix="/api/v1",
    tags=["promotions"],
)

app.include_router(
    hr.hr_router,
    prefix="/api/v1",
    tags=["hr"],
)

app.include_router(
    correspondence.correspondence_router,
    prefix="/api/v1",
    tags=["correspondence"],
)

app.include_router(
    parent_portal.router,
    prefix="/api/v1",
    tags=["parent-portal"],
)

# Import models to register them with metadata for table creation
from app.models.school import School, SchoolFee
from app.models.fee_structure import FeeStructure, FeeInstallment
from app.models.student_payment import StudentPayment, StudentPaymentInstallment
from app.models.payroll_time_entry import PayrollTimeEntry  # noqa: F401 — register metadata
from app.models.user_push_token import UserPushToken  # noqa: F401 — register tenant metadata
from app.models.student_year_outcome import StudentYearOutcome  # noqa: F401 — register tenant metadata
from app.models.student_promotion_history import StudentPromotionHistory  # noqa: F401 — register tenant metadata
from app.models.student_course_rank import StudentCourseRank  # noqa: F401 — register tenant metadata
from app.models.academic_calendar import AcademicCalendar  # noqa: F401 — register tenant metadata
from app.models.staff_document import StaffDocument  # noqa: F401
from app.models.staff_attendance import StaffAttendance  # noqa: F401
from app.models.communication import Communication  # noqa: F401
from app.models.communication_template import CommunicationTemplate  # noqa: F401
from app.models.circular import Circular  # noqa: F401
from app.models.student_attendance_entry import StudentAttendanceEntry  # noqa: F401
from app.models.student_chat import StudentChatThread, StudentChatMessage  # noqa: F401
from app.models.platform_analytics import (  # noqa: F401
    LoginAuditEvent,
    OtpAuditEvent,
    PlatformEmailEvent,
    PlatformErrorEvent,
    ApiRequestLog,
)

# Create metadata database tables (if they don't exist)
@app.on_event("startup")
def startup():
    DefaultBase.metadata.create_all(bind=engine)
    BaseModel_Base.metadata.create_all(bind=engine)
    from app.database.schema_patches import ensure_schema_patches
    ensure_schema_patches(engine)
    # Seed default data
    with DefaultSessionLocal() as session:
        run_startup_seed(session)
    
    # Start schedule reminder scheduler
    try:
        from app.authentication.authenticator import verify_password, hash_password
        from app.tasks.schedule_reminder_task import start_schedule_reminder_scheduler
        print("SYSTEM ADMIN PASSWORD ", hash_password("admin123"))  # Example usage of hash_password to ensure it's working
        start_schedule_reminder_scheduler()
        from app.tasks.tenant_billing_reminder_task import (
            start_tenant_billing_reminder_scheduler,
        )
        start_tenant_billing_reminder_scheduler()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to start reminder scheduler: {str(e)}")

@app.on_event("shutdown")
def shutdown():
    """Stop background tasks on shutdown"""
    try:
        from app.tasks.schedule_reminder_task import stop_schedule_reminder_scheduler
        from app.tasks.tenant_billing_reminder_task import (
            stop_tenant_billing_reminder_scheduler,
        )
        stop_schedule_reminder_scheduler()
        stop_tenant_billing_reminder_scheduler()
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

# SSE endpoint for real-time cache invalidation notifications
from fastapi.responses import StreamingResponse
import asyncio
import json

# Store for SSE subscribers
sse_subscribers = []

@app.get("/api/v1/events/cache", tags=["events"])
async def cache_events():
    """
    SSE endpoint for real-time cache invalidation events.
    Frontend can subscribe to this endpoint to receive instant notifications.
    """
    async def event_generator():
        # Send initial connection message
        yield f"data: {json.dumps({'event': 'connected', 'message': 'Connected to cache events'})}\n\n"
        
        # Keep connection alive and send periodic heartbeats
        while True:
            await asyncio.sleep(30)
            yield f"data: {json.dumps({'event': 'heartbeat', 'timestamp': str(asyncio.get_event_loop().time())})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

# Function to broadcast cache events to all SSE subscribers
async def broadcast_cache_event(data):
    """Broadcast a cache event to all SSE subscribers"""
    event_data = f"data: {json.dumps(data)}\n\n"
    # SSE is one-directional, so we just log this
    print(f"[SSE] Would broadcast: {data}")

print("[SERVER] Server ready")