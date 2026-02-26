from fastapi import FastAPI
from app.database.base import DefaultBase, engine
from app.database.sessionManager import BaseModel_Base
from app.routes import (
    login, register_user, tenants, students, teachers, courses, schedules, activities,
    announcements, assignments, users, notes, classes, enrollments, student_records,
    complaints, tenant_settings, system_admin, system_config
)
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI app
app = FastAPI(
    title="School Management System",
    description="A multi-tenant school management system using FastAPI.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

# Include routers
# Authentication routes
app.include_router(login.login, prefix="/auth/v1", tags=["Authentication"])
app.include_router(register_user.register, prefix="/api/v1", tags=["Registration"])

# Core entity routes
app.include_router(tenants.tenant, prefix="/api/v1", tags=["tenants"])
app.include_router(students.student, prefix="/api/v1", tags=["students"])
app.include_router(teachers.teacher, prefix="/api/v1", tags=["teachers"])
app.include_router(courses.course, prefix="/api/v1", tags=["courses"])
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

# System admin routes (global database)
app.include_router(system_admin.system_admin, prefix="/api/v1", tags=["system-admin"])
app.include_router(system_config.system_config, prefix="/api/v1", tags=["system-config"])

# Create metadata database tables (if they don't exist)
@app.on_event("startup")
def startup():
    DefaultBase.metadata.create_all(bind=engine)
    BaseModel_Base.metadata.create_all(bind=engine)

# Health check endpoint
@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok", "message": "School Management System is running!"}