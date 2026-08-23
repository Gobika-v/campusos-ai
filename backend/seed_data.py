from datetime import date, timedelta

from database import Base, SessionLocal, engine
from models import Attendance, Event, Exam, FeeRecord, Student, Timetable

Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    existing_student = db.query(Student).filter(Student.id == 1).first()

    if existing_student:
        print("Demo data already exists. Delete campusos.db if you want a fresh reset.")
    else:
        student = Student(
            id=1,
            name="Arjun Mehta",
            email="arjun.mehta@campusos.edu",
            department="Computer Science and Engineering",
            semester=4,
            roll_number="CSE2024-041",
        )
        db.add(student)
        db.flush()

        timetable_entries = [
            Timetable(
                student_id=1,
                day="Monday",
                subject="Database Management Systems",
                faculty="Dr. Priya Sharma",
                room="C-204",
                start_time="09:00",
                end_time="10:00",
            ),
            Timetable(
                student_id=1,
                day="Monday",
                subject="Machine Learning",
                faculty="Dr. Rahul Verma",
                room="AI Lab-2",
                start_time="11:00",
                end_time="12:00",
            ),
            Timetable(
                student_id=1,
                day="Monday",
                subject="Operating Systems",
                faculty="Dr. Ankit Rao",
                room="C-302",
                start_time="14:00",
                end_time="15:00",
            ),
            Timetable(
                student_id=1,
                day="Tuesday",
                subject="Database Management Systems",
                faculty="Dr. Priya Sharma",
                room="C-204",
                start_time="14:00",
                end_time="15:00",
            ),
            Timetable(
                student_id=1,
                day="Tuesday",
                subject="Machine Learning",
                faculty="Dr. Rahul Verma",
                room="AI Lab-2",
                start_time="10:00",
                end_time="11:00",
            ),
        ]

        attendance_records = [
            Attendance(
                student_id=1,
                subject="Database Management Systems",
                attended_classes=34,
                total_classes=38,
                percentage=89.47,
            ),
            Attendance(
                student_id=1,
                subject="Machine Learning",
                attended_classes=29,
                total_classes=38,
                percentage=76.32,
            ),
            Attendance(
                student_id=1,
                subject="Operating Systems",
                attended_classes=27,
                total_classes=38,
                percentage=71.05,
            ),
        ]

        today = date.today()

        exams = [
            Exam(
                department="Computer Science and Engineering",
                semester=4,
                subject="Database Management Systems",
                exam_date=today + timedelta(days=7),
                start_time="09:30",
                end_time="12:30",
                room="Exam Hall A",
                exam_type="Internal Assessment",
            ),
            Exam(
                department="Computer Science and Engineering",
                semester=4,
                subject="Machine Learning",
                exam_date=today + timedelta(days=10),
                start_time="09:30",
                end_time="12:30",
                room="Exam Hall B",
                exam_type="Internal Assessment",
            ),
            Exam(
                department="Computer Science and Engineering",
                semester=4,
                subject="Operating Systems",
                exam_date=today + timedelta(days=14),
                start_time="09:30",
                end_time="12:30",
                room="Exam Hall A",
                exam_type="Internal Assessment",
            ),
        ]

        events = [
            Event(
                title="AI Innovation Workshop",
                description="Hands-on workshop on agentic AI, RAG and production-ready AI applications.",
                category="Technology",
                event_date=today + timedelta(days=1),
                start_time="14:00",
                end_time="16:00",
                venue="Seminar Hall 1",
                capacity=120,
                registered_count=32,
            ),
            Event(
                title="Campus Hackathon 2026",
                description="24-hour interdepartmental hackathon for student innovators.",
                category="Hackathon",
                event_date=today + timedelta(days=5),
                start_time="09:00",
                end_time="18:00",
                venue="Innovation Centre",
                capacity=200,
                registered_count=145,
            ),
            Event(
                title="Cloud Computing Seminar",
                description="Industry session on cloud careers and deployment strategies.",
                category="Seminar",
                event_date=today + timedelta(days=9),
                start_time="11:00",
                end_time="13:00",
                venue="Auditorium",
                capacity=150,
                registered_count=70,
            ),
        ]

        fee_record = FeeRecord(
            student_id=1,
            academic_year="2026-2027",
            total_amount=85000.0,
            paid_amount=60000.0,
            due_date=today + timedelta(days=15),
            payment_status="partially_paid",
        )

        db.add_all(timetable_entries)
        db.add_all(attendance_records)
        db.add_all(exams)
        db.add_all(events)
        db.add(fee_record)
        db.commit()

        print("CampusOS AI demo database seeded successfully.")
        print("Demo student: Arjun Mehta | student_id=1")

finally:
    db.close()