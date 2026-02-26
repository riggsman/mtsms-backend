"""
Seed script to populate the backend database with mock data from frontend
Run this script after setting up the database to populate initial data
"""
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.base import get_db_session, DefaultSessionLocal
from app.models.course import Course
from app.models.schedule import Schedule
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.user import User
from app.models.complaint import Complaint
from app.models.assignment import Assignment
from app.models.student_record import StudentRecord
from app.models.department import Department
import importlib
_class_module = importlib.import_module('app.models.class')
SchoolClass = _class_module.Class
from app.models.academic_year import AcademicYear
from app.models.guardian import Guardian
from app.authentication.authenticator import hash_password
import json

def seed_departments(db):
    """Seed departments - required for courses, teachers, students"""
    departments_data = [
        {'name': 'Mathematics', 'code': 'MATH'},
        {'name': 'Science', 'code': 'SCI'},
        {'name': 'English', 'code': 'ENG'},
        {'name': 'Computer Science', 'code': 'CS'},
        {'name': 'Physics', 'code': 'PHY'},
        {'name': 'Chemistry', 'code': 'CHEM'},
        {'name': 'Biology', 'code': 'BIO'}
    ]
    
    department_map = {}
    for dept_data in departments_data:
        existing = db.query(Department).filter(Department.code == dept_data['code']).first()
        if not existing:
            dept = Department(**dept_data)
            db.add(dept)
            db.flush()  # Get the ID
            department_map[dept_data['name']] = dept.id
            print(f"Added department: {dept_data['name']} (ID: {dept.id})")
        else:
            department_map[dept_data['name']] = existing.id
    
    db.commit()
    return department_map

def seed_academic_years(db):
    """Seed academic years - required for students"""
    academic_years_data = [
        {
            'name': '2023-2024',
            'start_date': '2023-09-01',
            'end_date': '2024-06-30',
            'is_current': True
        },
        {
            'name': '2024-2025',
            'start_date': '2024-09-01',
            'end_date': '2025-06-30',
            'is_current': False
        }
    ]
    
    academic_year_map = {}
    for ay_data in academic_years_data:
        existing = db.query(AcademicYear).filter(AcademicYear.name == ay_data['name']).first()
        if not existing:
            ay = AcademicYear(**ay_data)
            db.add(ay)
            db.flush()
            academic_year_map[ay_data['name']] = ay.id
            print(f"Added academic year: {ay_data['name']} (ID: {ay.id})")
        else:
            academic_year_map[ay_data['name']] = existing.id
    
    db.commit()
    return academic_year_map

def seed_classes(db, department_map, academic_year_map):
    """Seed classes - required for students"""
    classes_data = [
        {'name': 'Grade 8', 'level_id': 8, 'department_id': department_map.get('Mathematics', 1), 'academic_year_id': list(academic_year_map.values())[0], 'capacity': 30},
        {'name': 'Grade 9', 'level_id': 9, 'department_id': department_map.get('Mathematics', 1), 'academic_year_id': list(academic_year_map.values())[0], 'capacity': 30},
        {'name': 'Grade 10', 'level_id': 10, 'department_id': department_map.get('Mathematics', 1), 'academic_year_id': list(academic_year_map.values())[0], 'capacity': 30},
        {'name': 'Grade 11', 'level_id': 11, 'department_id': department_map.get('Mathematics', 1), 'academic_year_id': list(academic_year_map.values())[0], 'capacity': 30}
    ]
    
    class_map = {}
    for class_data in classes_data:
        existing = db.query(SchoolClass).filter(
            SchoolClass.name == class_data['name'],
            SchoolClass.academic_year_id == class_data['academic_year_id']
        ).first()
        if not existing:
            cls = SchoolClass(**class_data)
            db.add(cls)
            db.flush()
            class_map[class_data['name']] = cls.id
            print(f"Added class: {class_data['name']} (ID: {cls.id})")
        else:
            class_map[class_data['name']] = existing.id
    
    db.commit()
    return class_map

def seed_guardians(db):
    """Seed guardians - required for students"""
    guardians_data = [
        {
            'guardian_name': 'Jane Doe',
            'phone': '+1234567891',
            'address': '123 Main St, City',
            'relationship': 'mother',
            'gender': 'Female',
            'email': 'jane.doe@email.com'
        },
        {
            'guardian_name': 'Robert Smith',
            'phone': '+1234567893',
            'address': '456 Oak Ave, City',
            'relationship': 'father',
            'gender': 'Male',
            'email': 'robert.smith@email.com'
        },
        {
            'guardian_name': 'Mary Johnson',
            'phone': '+1234567895',
            'address': '789 Pine Rd, City',
            'relationship': 'mother',
            'gender': 'Female',
            'email': 'mary.johnson@email.com'
        }
    ]
    
    guardian_map = {}
    for i, guardian_data in enumerate(guardians_data):
        existing = db.query(Guardian).filter(Guardian.phone == guardian_data['phone']).first()
        if not existing:
            guardian = Guardian(**guardian_data)
            db.add(guardian)
            db.flush()
            guardian_map[i] = guardian.id
            print(f"Added guardian: {guardian_data['guardian_name']} (ID: {guardian.id})")
        else:
            guardian_map[i] = existing.id
    
    db.commit()
    return guardian_map

def seed_courses(db, department_map):
    """Seed courses from frontend mock data"""
    courses_data = [
        {
            'name': 'Mathematics 101',
            'code': 'MATH101',
            'department_id': department_map.get('Mathematics', 1),
            'credits': 3,
            'description': 'Introduction to Algebra and Calculus'
        },
        {
            'name': 'Science Lab',
            'code': 'SCI201',
            'department_id': department_map.get('Science', 2),
            'credits': 4,
            'description': 'Chemistry and Physics Laboratory'
        },
        {
            'name': 'English Literature',
            'code': 'ENG301',
            'department_id': department_map.get('English', 3),
            'credits': 3,
            'description': 'Shakespeare and Modern Literature'
        },
        {
            'name': 'Computer Science',
            'code': 'CS401',
            'department_id': department_map.get('Computer Science', 4),
            'credits': 4,
            'description': 'Programming Fundamentals'
        }
    ]
    
    for course_data in courses_data:
        existing = db.query(Course).filter(Course.code == course_data['code']).first()
        if not existing:
            course = Course(**course_data)
            db.add(course)
            print(f"Added course: {course_data['code']}")
    
    db.commit()

def seed_schedules(db):
    """Seed schedules from frontend mock data"""
    schedules_data = [
        {
            'course_name': 'Mathematics 101',
            'instructor': 'Prof. Smith',
            'day': 'Monday',
            'start_time': '09:00',
            'end_time': '10:30',
            'room': 'Room 101',
            'capacity': 30,
            'description': 'Introduction to Algebra'
        },
        {
            'course_name': 'Science Lab',
            'instructor': 'Dr. Johnson',
            'day': 'Tuesday',
            'start_time': '14:00',
            'end_time': '16:00',
            'room': 'Lab 205',
            'capacity': 25,
            'description': 'Chemistry Laboratory'
        },
        {
            'course_name': 'English Literature',
            'instructor': 'Ms. Williams',
            'day': 'Wednesday',
            'start_time': '10:00',
            'end_time': '11:30',
            'room': 'Room 302',
            'capacity': 35,
            'description': 'Shakespeare Studies'
        },
        {
            'course_name': 'Computer Science',
            'instructor': 'Prof. Davis',
            'day': 'Thursday',
            'start_time': '13:00',
            'end_time': '15:00',
            'room': 'Lab 401',
            'capacity': 20,
            'description': 'Programming Lab'
        },
        {
            'course_name': 'Mathematics 101',
            'instructor': 'Prof. Smith',
            'day': 'Friday',
            'start_time': '09:00',
            'end_time': '10:30',
            'room': 'Room 101',
            'capacity': 30,
            'description': 'Calculus Practice'
        }
    ]
    
    for schedule_data in schedules_data:
        existing = db.query(Schedule).filter(
            Schedule.course_name == schedule_data['course_name'],
            Schedule.day == schedule_data['day'],
            Schedule.start_time == schedule_data['start_time']
        ).first()
        if not existing:
            schedule = Schedule(**schedule_data)
            db.add(schedule)
            print(f"Added schedule: {schedule_data['course_name']} - {schedule_data['day']}")
    
    db.commit()

def seed_teachers(db, department_map):
    """Seed teachers/lecturers from frontend mock data"""
    teachers_data = [
        {
            'firstname': 'John',
            'lastname': 'Smith',
            'email': 'prof.smith@school.com',
            'phone': '+1234567890',
            'department_id': department_map.get('Mathematics', 1),
            'employee_id': 'LEC001',
            'dob': '1980-01-15',
            'gender': 'Male',
            'address': '123 Teacher St',
            'specialization': 'Algebra and Calculus',
            'qualification': 'Ph.D. in Mathematics'
        },
        {
            'firstname': 'Jane',
            'lastname': 'Johnson',
            'email': 'dr.johnson@school.com',
            'phone': '+1234567891',
            'department_id': department_map.get('Science', 2),
            'employee_id': 'LEC002',
            'dob': '1975-03-20',
            'gender': 'Female',
            'address': '456 Teacher Ave',
            'specialization': 'Chemistry',
            'qualification': 'Ph.D. in Chemistry'
        },
        {
            'firstname': 'Sarah',
            'lastname': 'Williams',
            'email': 'ms.williams@school.com',
            'phone': '+1234567892',
            'department_id': department_map.get('English', 3),
            'employee_id': 'LEC003',
            'dob': '1985-07-10',
            'gender': 'Female',
            'address': '789 Teacher Rd',
            'specialization': 'Literature',
            'qualification': 'M.A. in English Literature'
        },
        {
            'firstname': 'Michael',
            'lastname': 'Davis',
            'email': 'prof.davis@school.com',
            'phone': '+1234567893',
            'department_id': department_map.get('Computer Science', 4),
            'employee_id': 'LEC004',
            'dob': '1978-11-25',
            'gender': 'Male',
            'address': '321 Teacher Dr',
            'specialization': 'Programming',
            'qualification': 'Ph.D. in Computer Science'
        }
    ]
    
    for teacher_data in teachers_data:
        existing = db.query(Teacher).filter(Teacher.email == teacher_data['email']).first()
        if not existing:
            teacher = Teacher(**teacher_data)
            db.add(teacher)
            print(f"Added teacher: {teacher_data['firstname']} {teacher_data['lastname']}")
    
    db.commit()

def seed_students(db, department_map, class_map, academic_year_map, guardian_map):
    """Seed students from frontend mock data"""
    students_data = [
        {
            'student_id': 'STU001',
            'firstname': 'Alice',
            'lastname': 'Brown',
            'email': 'alice.brown@student.school.com',
            'phone': '+1234567900',
            'dob': '2000-01-15',
            'gender': 'Female',
            'address': '123 Main St',
            'class_id': class_map.get('Grade 10', 1),
            'department_id': department_map.get('Computer Science', 4),
            'academic_year_id': list(academic_year_map.values())[0],
            'guardian_id': list(guardian_map.values())[0] if guardian_map else 1
        },
        {
            'student_id': 'STU002',
            'firstname': 'Bob',
            'lastname': 'Wilson',
            'email': 'bob.wilson@student.school.com',
            'phone': '+1234567901',
            'dob': '2000-03-20',
            'gender': 'Male',
            'address': '456 Oak Ave',
            'class_id': class_map.get('Grade 10', 1),
            'department_id': department_map.get('Mathematics', 1),
            'academic_year_id': list(academic_year_map.values())[0],
            'guardian_id': list(guardian_map.values())[1] if len(guardian_map) > 1 else 1
        },
        {
            'student_id': 'STU003',
            'firstname': 'Carol',
            'lastname': 'Martinez',
            'email': 'carol.martinez@student.school.com',
            'phone': '+1234567902',
            'dob': '1999-07-10',
            'gender': 'Female',
            'address': '789 Pine Rd',
            'class_id': class_map.get('Grade 11', 1),
            'department_id': department_map.get('Science', 2),
            'academic_year_id': list(academic_year_map.values())[0],
            'guardian_id': list(guardian_map.values())[2] if len(guardian_map) > 2 else 1
        }
    ]
    
    for student_data in students_data:
        existing = db.query(Student).filter(Student.student_id == student_data['student_id']).first()
        if not existing:
            student = Student(**student_data)
            db.add(student)
            print(f"Added student: {student_data['student_id']} - {student_data['firstname']} {student_data['lastname']}")
    
    db.commit()

def seed_assignments(db):
    """Seed assignments from frontend mock data"""
    assignments_data = [
        {
            'course_code': 'MATH101',
            'title': 'Algebra Assignment 1',
            'description': 'Complete exercises 1-10 from chapter 2',
            'due_date': (datetime.now() + timedelta(days=7)).date(),
            'late_penalty': 10,
            'created_by': 'Prof. Smith'
        },
        {
            'course_code': 'CS401',
            'title': 'Programming Project',
            'description': 'Build a calculator application',
            'due_date': (datetime.now() + timedelta(days=14)).date(),
            'late_penalty': 5,
            'created_by': 'Prof. Davis'
        },
        {
            'course_code': 'ENG301',
            'title': 'Essay on Shakespeare',
            'description': 'Write a 2000-word essay on Hamlet',
            'due_date': (datetime.now() + timedelta(days=10)).date(),
            'late_penalty': 15,
            'created_by': 'Ms. Williams'
        }
    ]
    
    for assignment_data in assignments_data:
        existing = db.query(Assignment).filter(
            Assignment.course_code == assignment_data['course_code'],
            Assignment.title == assignment_data['title']
        ).first()
        if not existing:
            assignment = Assignment(**assignment_data)
            db.add(assignment)
            print(f"Added assignment: {assignment_data['title']}")
    
    db.commit()

def seed_users(db):
    """Seed users (for testing)"""
    # Note: institution_id should match an existing institution/tenant
    # For now, using 1 as default - adjust based on your setup
    
    # Hash passwords with Argon2
    try:
        admin_password = hash_password('admin123')
        print(f"✓ Hashed admin password with Argon2")
    except Exception as e:
        print(f"✗ Error hashing admin password: {e}")
        raise
    
    try:
        superadmin_password = hash_password('superadmin123')
        print(f"✓ Hashed superadmin password with Argon2")
    except Exception as e:
        print(f"✗ Error hashing superadmin password: {e}")
        raise
    
    try:
        secretary_password = hash_password('secretary123')
        print(f"✓ Hashed secretary password with Argon2")
    except Exception as e:
        print(f"✗ Error hashing secretary password: {e}")
        raise
    
    users_data = [
        {
            'institution_id': 1,
            'firstname': 'Admin',
            'lastname': 'User',
            'email': 'admin@school.com',
            'phone': '+1234567800',
            'username': 'admin',
            'password': admin_password,
            'role': 'admin',
            'is_active': 'active',
            'gender': 'Male',
            'address': 'Admin Office'
        },
        {
            'institution_id': None,  # System admin doesn't belong to a tenant
            'firstname': 'Super',
            'lastname': 'Admin',
            'email': 'superadmin@school.com',
            'phone': '+1234567801',
            'username': 'superadmin',
            'password': superadmin_password,
            'role': 'system_super_admin',  # System admin role for global admin dashboard
            'is_active': 'active',
            'gender': 'Male',
            'address': 'System Admin Office'
        },
        {
            'institution_id': 1,
            'firstname': 'Secretary',
            'lastname': 'User',
            'email': 'secretary@school.com',
            'phone': '+1234567802',
            'username': 'secretary',
            'password': secretary_password,
            'role': 'secretary',
            'is_active': 'active',
            'gender': 'Female',
            'address': 'Secretary Office'
        }
    ]
    
    for user_data in users_data:
        existing = db.query(User).filter(User.username == user_data['username']).first()
        if not existing:
            user = User(**user_data)
            db.add(user)
            print(f"Added user: {user_data['username']}")
        else:
            # Update existing user with Argon2 hashed password if it's not already hashed
            if not existing.password.startswith('$argon2') and not existing.password.startswith('$2b$'):
                existing.password = user_data['password']
                print(f"Updated password hash for user: {user_data['username']} (migrated to Argon2)")
            else:
                print(f"User {user_data['username']} already exists with hashed password")
    
    db.commit()

def main():
    """Main function to seed all data"""
    print("Starting database seeding...")
    
    db = next(get_db_session())
    try:
        # Seed in order: dependencies first
        print("\n1. Seeding departments...")
        department_map = seed_departments(db)
        
        print("\n2. Seeding academic years...")
        academic_year_map = seed_academic_years(db)
        
        print("\n3. Seeding classes...")
        class_map = seed_classes(db, department_map, academic_year_map)
        
        print("\n4. Seeding guardians...")
        guardian_map = seed_guardians(db)
        
        print("\n5. Seeding courses...")
        seed_courses(db, department_map)
        
        print("\n6. Seeding schedules...")
        seed_schedules(db)
        
        print("\n7. Seeding teachers...")
        seed_teachers(db, department_map)
        
        print("\n8. Seeding students...")
        seed_students(db, department_map, class_map, academic_year_map, guardian_map)
        
        print("\n9. Seeding assignments...")
        seed_assignments(db)
        
        print("\n10. Seeding users...")
        seed_users(db)
        
        print("\nDatabase seeding completed successfully!")
    except Exception as e:
        print(f"Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
