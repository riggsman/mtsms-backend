import io
from datetime import datetime
from decimal import Decimal
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import black, HexColor
from sqlalchemy.orm import Session
from app.models.student import Student
from app.models.student_record import StudentRecord
from app.models.tenant import Tenant
from app.models.department import Department
from app.models.course import Course
from app.services.gpa_service import get_grade_point_from_letter
from app.services.document_verification import (
    build_result_slip_verification_payload,
    build_transcript_verification_payload,
    draw_verification_qr_on_canvas,
    issue_verified_document,
)


def get_student_data(db: Session, student_no: str, institution_id: int):
    # School model disabled - schools table was dropped
    # from app.models.school import School
    
    student = db.query(Student).filter(
        Student.student_id == student_no,
        Student.institution_id == institution_id,
        Student.deleted_at.is_(None)
    ).first()
    if student:
        department = db.query(Department).filter(
            Department.id == student.department_id,
            Department.deleted_at.is_(None)
        ).first() if student.department_id else None
        
        # School lookup disabled - schools table was dropped
        # school = None
        # if student.school_id:
        #     school = db.query(School).filter(
        #         School.id == student.school_id,
        #         School.deleted_at.is_(None)
        #     ).first()
        
        def _pdf_text(value, fallback="N/A"):
            if value is None:
                return fallback
            text = str(value).strip()
            return text if text else fallback

        return {
            "student_no": _pdf_text(student.student_id),
            "surname": _pdf_text(student.lastname),
            "other_names": _pdf_text(f"{student.firstname} {student.middlename or ''}".strip()),
            "date_of_birth": _pdf_text(student.dob),
            "sex": _pdf_text(student.gender),
            "date_of_enrolment": (
                student.created_at.strftime("%d %B %Y") if student.created_at else "N/A"
            ),
            "faculty": department.name if department else "N/A",  # School table dropped, using department
            "department": department.name if department else "N/A",
            "major": department.name if department else "N/A",
            "degree_proposed": student.degree_proposed or student.type or "Undergraduate",
        }
    return None


def get_student_courses(db: Session, student_no: str, institution_id: int, semester: str = None):
    query = db.query(StudentRecord).filter(
        StudentRecord.student_id == student_no,
        StudentRecord.institution_id == institution_id,
        StudentRecord.deleted_at.is_(None)
    )
    if semester:
        query = query.filter(StudentRecord.semester == semester)
    records = query.order_by(StudentRecord.semester).all()
    
    # Fetch all course codes at once for efficient lookup
    course_codes = list(set(r.course_code for r in records if r.course_code))
    courses_by_code = {}
    if course_codes:
        course_records = db.query(Course).filter(
            Course.code.in_(course_codes),
            Course.institution_id == institution_id,
            Course.deleted_at.is_(None)
        ).all()
        for c in course_records:
            courses_by_code[c.code] = c
    
    courses = []
    for record in records:
        course = courses_by_code.get(record.course_code) if record.course_code else None
        course_name = course.name if course else (record.course_code or "N/A")
        credit_value = float(record.course_weight or 0) if record.course_weight else (
            float(course.credits) if course and course.credits else 3
        )
        ca_mark = float(record.assignment or 0) + float(record.ca or 0)
        exam_mark = float(record.exam or 0)
        total_mark = float(record.total_score or 0) if record.total_score else (ca_mark + exam_mark)
        courses.append({
            "semester": record.semester,
            "cse_code": record.course_code or "N/A",
            "course_title": course_name,
            "type": "COMPULSORY",
            "credit_value": credit_value,
            "ca_mark": ca_mark,
            "exam_mark": exam_mark,
            "total_mark": total_mark,
            "grade": record.letter_grade or "N/A",
            "credits_earned": credit_value if record.letter_grade and record.letter_grade not in ["F", "X", "W", "N", "P"] else 0,
            "for_gpa": credit_value if record.letter_grade not in ["F", "X", "W", "N", "P"] else 0,
            "points": float(record.gpa or 0) * credit_value if record.gpa else 0
        })
    return courses


def get_institution_data(db: Session, institution_id: int):
    tenant = db.query(Tenant).filter(Tenant.id == institution_id).first()
    if tenant:
        return {
            "name": tenant.name.upper(),
            "address": "P.O. Box 63",
            "city": "BUEA, CAMEROON"
        }
    return {
        "name": "EduSphere",
        "address": "P.O. Box ",
        "city": "Douala, CAMEROON"
    }


def get_grade_points(db: Session, institution_id: int, grade: str) -> float:
    return get_grade_point_from_letter(db, institution_id, grade)


def generate_transcript_pdf(
    db: Session,
    student_no: str,
    institution_id: int,
    output_filename: str = None
):
    student_row = db.query(Student).filter(
        Student.student_id == student_no,
        Student.institution_id == institution_id,
        Student.deleted_at.is_(None),
    ).first()
    if not student_row:
        raise ValueError(f"No student found with ID: {student_no}")

    student_data = get_student_data(db, student_no, institution_id)
    if not student_data:
        raise ValueError(f"No student found with ID: {student_no}")
    
    student_courses = get_student_courses(db, student_no, institution_id)
    institution = get_institution_data(db, institution_id)
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    c.setTitle("Academic Transcript")
    c.setAuthor(institution.get("name") or "MTSMS")
    c.setSubject(f"Official academic transcript for student {student_no}")
    c.setCreator("MTSMS Certificate Service")
    
    current_date = datetime.now().strftime("%d %B %Y")
    
    c.setFont("Helvetica", 10)
    c.setFillColor(black)
    
    c.drawString(0.5 * inch, height - 0.7 * inch, institution["name"])
    c.drawString(0.5 * inch, height - 0.85 * inch, institution["address"])
    c.drawString(0.5 * inch, height - 1.0 * inch, institution["city"])
    
    c.setFont("Helvetica-Bold", 12)
    title = "ACADEMIC RECORD"
    c.drawString(width / 2 - c.stringWidth(title, "Helvetica-Bold", 12) / 2, height - 0.85 * inch, title)
    
    c.setFont("Helvetica", 9)
    c.drawString(6.3 * inch, height - 0.6 * inch, "STUDENT NO. " + student_data["student_no"])
    c.drawString(6.3 * inch, height - 0.75 * inch, "DATE PRINTED " + current_date)
    # c.drawString(5.0 * inch, height - 0.6 * inch, "STUDENT NO.")
    # c.drawString(5.0 * inch, height - 0.75 * inch, student_data["student_no"])
    
    # c.drawString(6.5 * inch, height - 0.6 * inch, "DATE PRINTED")
    # c.drawString(6.5 * inch, height - 0.75 * inch, current_date)
    
    c.setLineWidth(1)
    c.line(0.5 * inch, height - 1.1 * inch, width - 0.5 * inch, height - 1.1 * inch)
    
    c.setFont("Helvetica", 9)
    c.drawString(0.5 * inch, height - 1.25 * inch, "STUDENT NAME")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1.50 * inch, height - 1.25 * inch, student_data["surname"])
    
    c.setFont("Helvetica", 9)
    c.drawString(2.5 * inch, height - 1.25 * inch, "OTHER NAMES")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(4.0 * inch, height - 1.25 * inch, student_data["other_names"])
    
    c.setFont("Helvetica", 8)
    c.drawString(0.5 * inch, height - 1.4 * inch, "DATE OF BIRTH")
    c.drawString(2.5 * inch, height - 1.4 * inch, "PLACE OF BIRTH")
    c.drawString(5.30 * inch, height - 1.4 * inch, "SEX")
    # c.drawString(4.8 * inch, height - 1.4 * inch, "SCHOOL LAST ATTENDED")
    
    c.setFont("Helvetica", 9)
    c.drawString(1.50 * inch, height - 1.4 * inch, student_data["date_of_birth"])
    c.drawString(4.0 * inch, height - 1.4 * inch, student_data["date_of_birth"])
    c.drawString(5.70 * inch, height - 1.4 * inch, student_data["sex"])
    
    c.setFont("Helvetica-Bold", 7)
    c.drawString(5.60 * inch, height - 1.6 * inch, "THIS TRANSCRIPT IS NOT VALID WITHOUT")
    c.drawString(5.60 * inch, height - 1.7 * inch, "THE SIGNATURE OF THE REGISTRAR AND")
    c.drawString(5.60 * inch, height - 1.8 * inch, "THE EMBOSSED SEAL OF THE UNIVERSITY")
    
    c.setFont("Helvetica", 8)
    c.drawString(0.5 * inch, height - 1.8 * inch, "DATE OF ENROLMENT")
    c.drawString(1.80 * inch, height - 1.8 * inch, student_data["date_of_enrolment"])
    
    c.setFont("Helvetica", 9)
    c.drawString(0.5 * inch, height - 2.3 * inch, f"FAC/SCH: {student_data['faculty']}")
    c.drawString(0.5 * inch, height - 2.45 * inch,  f"DEPT: {student_data['department']}")
    c.drawString(0.5 * inch, height - 2.6 * inch, f"MAJOR: {student_data['major']}")
    c.drawString(0.5 * inch, height - 2.75 * inch, "MINOR:")
    c.drawString(0.5 * inch, height - 2.9 * inch,  f"DEGREE PROPOSED: {student_data['degree_proposed']}")
    c.drawString(0.5 * inch, height - 3.05 * inch, "DEGREE CONFERRED:")
    c.drawString(0.5 * inch, height - 3.2 * inch, "DATE:")
    
    c.setFont("Helvetica-Bold", 8)
    c.drawString(6.30 * inch, height - 2.0 * inch, "GRADE SYSTEM")
    c.setFont("Helvetica", 7)
    grades = [
        "A - 4.0GP  80-100% C - COMPULSORY",
        "B+ - 3.5GP  75-79% R - REQUIRED",
        "B - 3.0GP  70-74% E - ELECTIVE",
        "C+ - 2.5GP  65-69% G - UNIVERSITY REQUIREMENT",
        "C - 2.0GP  60-64%",
        "D+ - 1.5GP  55-59% W - 0.0GP WITHDREW",
        "D - 1.0GP  50-54% I - 0.0GP INCOMPLETE",
        "F - 0.0GP  0-49%  X - 0.0GP ABSENT FROM EXAM",
        "                 N - 0.0GP NO CREDIT",
        "                 P - 0.0GP NO CREDIT"
    ]
    y_grade = height - 2.15 * inch
    for grade in grades:
        c.drawString(5.60 * inch, y_grade, grade)
        y_grade -= 0.1 * inch
    
    y_table = height - 3.5 * inch
    c.setFont("Helvetica-Bold", 7)
    c.drawString(0.5 * inch, y_table, "COURSE CODE")
    c.drawString(1.4 * inch, y_table, "COURSE TITLE")
    c.drawString(3.2 * inch, y_table, "TYPE")
    c.drawString(3.5 * inch, y_table, "CREDIT VALUE")
    c.drawString(4.3 * inch, y_table, "GRADE")
    c.drawString(4.7 * inch, y_table, "CREDITS EARNED")
    c.drawString(5.6 * inch, y_table, "CREDITS FOR GPA")
    c.drawString(6.58 * inch, y_table, "GPA POINTS")
    
    c.line(0.5 * inch, y_table - 0.05 * inch, width - 0.5 * inch, y_table - 0.05 * inch)
    
    y_row = y_table - 0.2 * inch
    current_semester = None
    total_credits_attempted = 0
    total_credits_earned = 0
    total_gpa_credits_attempted = 0
    total_gpa_credits_earned = 0
    total_points = 0
    semester_gpa = 0.0
    
    if not student_courses:
        # Show message when no courses are available
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(width / 2 - c.stringWidth("No academic records available.", "Helvetica-Oblique", 10) / 2, y_row, "No academic records available.")
    else:
        for course in student_courses:
            if course["semester"] != current_semester:
                if current_semester is not None:
                    y_row -= 0.1 * inch
                c.setFont("Helvetica-Bold", 7)
                c.drawString(0.5 * inch, y_row, course["semester"])
                y_row -= 0.15 * inch
                current_semester = course["semester"]
            
            c.setFont("Helvetica", 7)
            c.drawString(0.5 * inch, y_row, course["cse_code"])
            c.drawString(1.4 * inch, y_row, course["course_title"])
            c.drawString(3.3  * inch, y_row, course["type"])
            c.drawString(3.7 * inch, y_row, str(course["credit_value"]))
            c.drawString(4.5 * inch, y_row, course["grade"])
            c.drawString(5.0 * inch, y_row, str(course["credits_earned"]))
            c.drawString(6.0 * inch, y_row, str(course["for_gpa"]))
            c.drawString(6.8 * inch, y_row, f"{course['points']:.1f}")
            y_row -= 0.12 * inch
            
            total_credits_attempted += course["credit_value"]
            total_credits_earned += course["credits_earned"]
            total_gpa_credits_attempted += course["for_gpa"]
            total_gpa_credits_earned += course["for_gpa"]
            total_points += course["points"]
        
        y_row -= 0.1 * inch
        c.setFont("Helvetica-Bold", 7)
        c.drawString(0.5 * inch, y_row, f"TOTAL CREDITS ATTEMPTED: {total_credits_attempted}")
        c.drawString(2.5 * inch, y_row, f"TOTAL CREDITS EARNED: {total_credits_earned}")
        y_row -= 0.12 * inch
        c.drawString(0.5 * inch, y_row, f"GPA CREDITS ATTEMPTED: {total_gpa_credits_attempted}")
        c.drawString(2.5 * inch, y_row, f"GPA CREDITS EARNED: {total_gpa_credits_earned}")
        y_row -= 0.12 * inch
        
        semester_gpa = total_points / total_gpa_credits_attempted if total_gpa_credits_attempted > 0 else 0.0
        c.drawString(1.2 * inch, y_row, f"CUMULATIVE GPA: {semester_gpa:.2f}")

    verification_payload = build_transcript_verification_payload(
        student_data,
        institution,
        student_courses,
        date_printed=current_date,
        totals={
            "cumulative_gpa": semester_gpa if student_courses else None,
            "total_credits_attempted": total_credits_attempted if student_courses else 0,
            "total_credits_earned": total_credits_earned if student_courses else 0,
        },
    )
    verification_token, qr_png = issue_verified_document(
        db,
        document_type="transcript",
        institution_id=institution_id,
        student_no=student_no,
        payload=verification_payload,
        student_id=student_row.id,
    )
    draw_verification_qr_on_canvas(
        c,
        verification_token,
        x=width - 1.15 * inch,
        y=0.45 * inch,
        strict=True,
        png_bytes=qr_png,
    )

    c.setFont("Helvetica-Bold", 10)
    c.drawString(width / 2 - 20, 0.7 * inch, "Registrar")
    c.setFont("Helvetica", 10)
    c.drawString(width - 1.5 * inch, 0.7 * inch, current_date)
    
    c.save()
    
    buffer.seek(0)
    
    if output_filename:
        with open(output_filename, 'wb') as f:
            f.write(buffer.getvalue())
        return output_filename
    
    return buffer


def generate_result_slip_pdf(
    db: Session,
    student_no: str,
    institution_id: int,
    semester: str = None,
    output_filename: str = None
):
    student_row = db.query(Student).filter(
        Student.student_id == student_no,
        Student.institution_id == institution_id,
        Student.deleted_at.is_(None),
    ).first()
    if not student_row:
        raise ValueError(f"No student found with ID: {student_no}")

    student_data = get_student_data(db, student_no, institution_id)
    if not student_data:
        raise ValueError(f"No student found with ID: {student_no}")
    
    student_courses = get_student_courses(db, student_no, institution_id, semester)
    institution = get_institution_data(db, institution_id)
    
    # Generate PDF even if no courses found
    target_semester = student_courses[0]["semester"] if student_courses else semester or "N/A"
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    c.setTitle("Statement of Results")
    c.setAuthor(institution.get("name") or "MTSMS")
    c.setSubject(f"Official result slip for student {student_no}")
    c.setCreator("MTSMS Certificate Service")
    
    current_date = datetime.now().strftime("%d %B %Y")
    
    # Header
    c.setFont("Helvetica-Bold", 14)
    c.drawString(width / 2 - c.stringWidth(institution["name"], "Helvetica-Bold", 14) / 2, height - 0.7 * inch, institution["name"])
    
    c.setFont("Helvetica-Bold", 12)
    title = "STATEMENT OF RESULTS"
    c.drawString(width / 2 - c.stringWidth(title, "Helvetica-Bold", 12) / 2, height - 1.0 * inch, title)
    
    # Student info
    c.setFont("Helvetica", 10)
    c.drawString(0.5 * inch, height - 1.4 * inch, f"STUDENT NAME: {student_data['surname']}, {student_data['other_names']}")
    c.drawString(0.5 * inch, height - 1.6 * inch, f"STUDENT NO: {student_data['student_no']}")
    c.drawString(0.5 * inch, height - 1.8 * inch, f"PROGRAMME: {student_data['degree_proposed']}")
    c.drawString(0.5 * inch, height - 2.0 * inch, f"DEPARTMENT: {student_data['department']}")
    c.drawString(0.5 * inch, height - 2.2 * inch, f"SEMESTER: {target_semester}")
    c.drawString(0.5 * inch, height - 2.4 * inch, f"DATE: {current_date}")
    
    c.setLineWidth(1)
    c.line(0.5 * inch, height - 2.6 * inch, width - 0.5 * inch, height - 2.6 * inch)
    
    # Table header
    y_table = height - 2.9 * inch
    c.setFont("Helvetica-Bold", 8)
    c.drawString(0.5 * inch, y_table, "CODE")
    c.drawString(1.3 * inch, y_table, "COURSE TITLE")
    c.drawString(3.8 * inch, y_table, "CA")
    c.drawString(4.3 * inch, y_table, "EXAM")
    c.drawString(4.9 * inch, y_table, "TOTAL")
    c.drawString(5.5 * inch, y_table, "GRADE")
    c.drawString(6.2 * inch, y_table, "POINTS")
    c.drawString(7.0 * inch, y_table, "REMARK")
    
    c.line(0.5 * inch, y_table - 0.05 * inch, width - 0.5 * inch, y_table - 0.05 * inch)
    
    y_row = y_table - 0.2 * inch
    total_points = 0
    total_credits = 0
    total_ca = 0
    total_exam = 0
    total_mark = 0
    semester_gpa = 0.0
    
    if not student_courses:
        # Show message when no courses are available
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(width / 2 - c.stringWidth("No results available for this semester.", "Helvetica-Oblique", 10) / 2, y_row, "No results available for this semester.")
    else:
        for course in student_courses:
            c.setFont("Helvetica", 8)
            # Truncate course title if too long
            course_title = course["course_title"]
            if len(course_title) > 35:
                course_title = course_title[:32] + "..."
            c.drawString(0.5 * inch, y_row, course["cse_code"])
            c.drawString(1.3 * inch, y_row, course_title)
            c.drawString(3.8 * inch, y_row, f"{course['ca_mark']:.1f}")
            c.drawString(4.3 * inch, y_row, f"{course['exam_mark']:.1f}")
            c.drawString(4.9 * inch, y_row, f"{course['total_mark']:.1f}")
            c.drawString(5.5 * inch, y_row, course["grade"])
            c.drawString(6.2 * inch, y_row, f"{course['points']:.1f}")
            
            remark = "PASS" if course["grade"] not in ["F", "X", "W", "N", "P"] else "FAIL"
            c.drawString(7.0 * inch, y_row, remark)
            
            total_points += course["points"]
            total_credits += course["credit_value"]
            total_ca += course["ca_mark"]
            total_exam += course["exam_mark"]
            total_mark += course["total_mark"]
            y_row -= 0.22 * inch
        
        y_row -= 0.15 * inch
        c.setLineWidth(0.5)
        c.line(0.5 * inch, y_row + 0.05 * inch, width - 0.5 * inch, y_row + 0.05 * inch)
        
        # Summary
        semester_gpa = total_points / total_credits if total_credits > 0 else 0.0
        c.setFont("Helvetica-Bold", 9)
        c.drawString(0.5 * inch, y_row, f"SEMESTER GPA: {semester_gpa:.2f}")
        c.drawString(2.5 * inch, y_row, f"TOTAL CREDITS: {total_credits}")
        c.drawString(4.5 * inch, y_row, f"TOTAL CA: {total_ca:.1f}")
        c.drawString(5.8 * inch, y_row, f"TOTAL EXAM: {total_exam:.1f}")
        
        y_row -= 0.25 * inch
        c.drawString(4.5 * inch, y_row, f"GRAND TOTAL: {total_mark:.1f}")
        
        y_row -= 0.4 * inch
        c.setFont("Helvetica", 9)
        c.drawString(0.5 * inch, y_row, f"Date: {current_date}")
        c.drawString(5.5 * inch, y_row, "Signature: ____________")

    verification_payload = build_result_slip_verification_payload(
        student_data,
        institution,
        student_courses,
        semester=target_semester,
        date_printed=current_date,
        semester_gpa=semester_gpa if student_courses else 0.0,
        total_credits=total_credits if student_courses else 0,
        total_ca=total_ca if student_courses else 0,
        total_exam=total_exam if student_courses else 0,
        grand_total=total_mark if student_courses else 0,
    )
    verification_token, qr_png = issue_verified_document(
        db,
        document_type="result_slip",
        institution_id=institution_id,
        student_no=student_no,
        payload=verification_payload,
        student_id=student_row.id,
        semester=target_semester if target_semester != "N/A" else semester,
    )
    draw_verification_qr_on_canvas(
        c,
        verification_token,
        x=width - 1.15 * inch,
        y=0.45 * inch,
        strict=True,
        png_bytes=qr_png,
    )

    # Footer
    c.setFont("Helvetica-Bold", 8)
    c.drawString(0.5 * inch, 0.5 * inch, "This is an official document. Keep it safe.")
    
    c.save()
    
    buffer.seek(0)
    
    if output_filename:
        with open(output_filename, 'wb') as f:
            f.write(buffer.getvalue())
        return output_filename
    
    return buffer
