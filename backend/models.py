from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    department = Column(String(100), nullable=False)
    semester = Column(Integer, nullable=False)
    roll_number = Column(String(50), unique=True, nullable=False)

    timetable_entries = relationship("Timetable", back_populates="student", cascade="all, delete-orphan")
    attendance_records = relationship("Attendance", back_populates="student", cascade="all, delete-orphan")
    leave_requests = relationship("LeaveRequest", back_populates="student", cascade="all, delete-orphan")
    grievances = relationship("Grievance", back_populates="student", cascade="all, delete-orphan")
    fees = relationship("FeeRecord", back_populates="student", cascade="all, delete-orphan")
    registrations = relationship("EventRegistration", back_populates="student", cascade="all, delete-orphan")


class Timetable(Base):
    __tablename__ = "timetable"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    day = Column(String(20), nullable=False)
    subject = Column(String(120), nullable=False)
    faculty = Column(String(120), nullable=False)
    room = Column(String(50), nullable=False)
    start_time = Column(String(10), nullable=False)
    end_time = Column(String(10), nullable=False)

    student = relationship("Student", back_populates="timetable_entries")


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    subject = Column(String(120), nullable=False)
    attended_classes = Column(Integer, nullable=False, default=0)
    total_classes = Column(Integer, nullable=False, default=0)
    percentage = Column(Float, nullable=False, default=0.0)

    student = relationship("Student", back_populates="attendance_records")


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    department = Column(String(100), nullable=False, index=True)
    semester = Column(Integer, nullable=False, index=True)
    subject = Column(String(120), nullable=False)
    exam_date = Column(Date, nullable=False)
    start_time = Column(String(10), nullable=False)
    end_time = Column(String(10), nullable=False)
    room = Column(String(50), nullable=False)
    exam_type = Column(String(50), nullable=False)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(80), nullable=False)
    event_date = Column(Date, nullable=False)
    start_time = Column(String(10), nullable=False)
    end_time = Column(String(10), nullable=False)
    venue = Column(String(120), nullable=False)
    capacity = Column(Integer, nullable=False, default=100)
    registered_count = Column(Integer, nullable=False, default=0)


class EventRegistration(Base):
    __tablename__ = "event_registrations"
    __table_args__ = (
        UniqueConstraint("student_id", "event_id", name="unique_student_event_registration"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    registered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(30), default="confirmed", nullable=False)

    student = relationship("Student", back_populates="registrations")
    event = relationship("Event")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="pending")
    action_id = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    student = relationship("Student", back_populates="leave_requests")


class MaintenanceTicket(Base):
    __tablename__ = "maintenance_tickets"

    id = Column(Integer, primary_key=True, index=True)
    location = Column(String(150), nullable=False)
    issue = Column(Text, nullable=False)
    priority = Column(String(30), nullable=False, default="medium")
    status = Column(String(30), nullable=False, default="open")
    assigned_team = Column(String(100), nullable=False, default="Campus Maintenance Team")
    action_id = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Grievance(Base):
    __tablename__ = "grievances"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    category = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(30), nullable=False, default="medium")
    status = Column(String(30), nullable=False, default="submitted")
    action_id = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    student = relationship("Student", back_populates="grievances")


class FeeRecord(Base):
    __tablename__ = "fee_records"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    academic_year = Column(String(20), nullable=False)
    total_amount = Column(Float, nullable=False)
    paid_amount = Column(Float, nullable=False, default=0.0)
    due_date = Column(Date, nullable=False)
    payment_status = Column(String(30), nullable=False, default="pending")

    student = relationship("Student", back_populates="fees")