from datetime import datetime
from uuid import uuid4
from policy_engine import get_attendance_impact
from typing import Any
from orchestrator import route_campus_request
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import (
    Attendance,
    Event,
    EventRegistration,
    Exam,
    FeeRecord,
    Grievance,
    LeaveRequest,
    MaintenanceTicket,
    Student,
    Timetable,
)
from schemas import (
    ChatRequest,
    EventRegistrationCreate,
    GrievanceCreate,
    LeaveRequestCreate,
    MaintenanceTicketCreate,
    AttendanceImpactRequest,
    CampusDecisionRequest, 
)
from schemas import MaintenanceConfirmation

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CampusOS AI API",
    description="Production-style backend prototype for autonomous campus operations.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def success_response(message: str, data=None, action_id: str | None = None):
    response = {
        "success": True,
        "message": message,
        "data": data,
    }
    if action_id:
        response["action_id"] = action_id
    return response


def get_student_or_404(student_id: int, db: Session) -> Student:
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} was not found.",
        )
    return student


@app.get("/", tags=["System"])
def root():
    return {
        "message": "CampusOS AI API is running",
        "docs": "/docs",
        "status": "healthy",
    }


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/academic/timetable", tags=["Academic"])
def get_timetable(
    student_id: int = Query(..., gt=0),
    day: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    student = get_student_or_404(student_id, db)

    query = db.query(Timetable).filter(Timetable.student_id == student_id)

    if day:
        query = query.filter(Timetable.day.ilike(day.strip()))

    entries = query.order_by(Timetable.day, Timetable.start_time).all()

    return success_response(
        message="Timetable retrieved successfully.",
        data={
            "student": {
                "id": student.id,
                "name": student.name,
                "department": student.department,
                "semester": student.semester,
            },
            "entries": [
                {
                    "id": entry.id,
                    "day": entry.day,
                    "subject": entry.subject,
                    "faculty": entry.faculty,
                    "room": entry.room,
                    "start_time": entry.start_time,
                    "end_time": entry.end_time,
                }
                for entry in entries
            ],
        },
    )


@app.get("/api/academic/attendance", tags=["Academic"])
def get_attendance(
    student_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    student = get_student_or_404(student_id, db)
    records = (
        db.query(Attendance)
        .filter(Attendance.student_id == student_id)
        .order_by(Attendance.subject)
        .all()
    )

    attendance_data = []
    for record in records:
        percentage = round(record.percentage, 2)
        status_label = "safe" if percentage >= 75 else "at_risk"
        classes_needed = 0

        if record.total_classes > 0 and percentage < 75:
            attended = record.attended_classes
            total = record.total_classes

            while (attended / total) * 100 < 75:
                attended += 1
                total += 1
                classes_needed += 1

        attendance_data.append(
            {
                "subject": record.subject,
                "attended_classes": record.attended_classes,
                "total_classes": record.total_classes,
                "percentage": percentage,
                "status": status_label,
                "classes_needed_to_reach_75_percent": classes_needed,
            }
        )

    return success_response(
        message="Attendance retrieved successfully.",
        data={
            "student": {"id": student.id, "name": student.name},
            "minimum_required_percentage": 75,
            "attendance": attendance_data,
        },
    )


@app.get("/api/exams/schedule", tags=["Examinations"])
def get_exam_schedule(
    student_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    student = get_student_or_404(student_id, db)

    exams = (
        db.query(Exam)
        .filter(
            Exam.department == student.department,
            Exam.semester == student.semester,
        )
        .order_by(Exam.exam_date, Exam.start_time)
        .all()
    )

    return success_response(
        message="Exam schedule retrieved successfully.",
        data={
            "student": {
                "id": student.id,
                "name": student.name,
                "department": student.department,
                "semester": student.semester,
            },
            "exams": [
                {
                    "id": exam.id,
                    "subject": exam.subject,
                    "exam_date": exam.exam_date.isoformat(),
                    "start_time": exam.start_time,
                    "end_time": exam.end_time,
                    "room": exam.room,
                    "exam_type": exam.exam_type,
                }
                for exam in exams
            ],
        },
    )


@app.post("/api/admin/leave", status_code=status.HTTP_201_CREATED, tags=["Administration"])
def apply_leave(
    payload: LeaveRequestCreate,
    db: Session = Depends(get_db),
):
    get_student_or_404(payload.student_id, db)

    if payload.end_date < payload.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date cannot be before start_date.",
        )

    action_id = f"LEAVE-{uuid4().hex[:8].upper()}"

    leave_request = LeaveRequest(
        student_id=payload.student_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason.strip(),
        status="pending",
        action_id=action_id,
    )

    db.add(leave_request)
    db.commit()
    db.refresh(leave_request)

    return success_response(
        message="Leave request submitted successfully. It is awaiting faculty approval.",
        action_id=action_id,
        data={
            "leave_request_id": leave_request.id,
            "student_id": leave_request.student_id,
            "start_date": leave_request.start_date.isoformat(),
            "end_date": leave_request.end_date.isoformat(),
            "reason": leave_request.reason,
            "status": leave_request.status,
        },
    )


@app.post(
    "/api/maintenance/ticket",
    status_code=status.HTTP_201_CREATED,
    tags=["Maintenance"],
)
def create_maintenance_ticket(
    payload: MaintenanceTicketCreate,
    db: Session = Depends(get_db),
):
    action_id = f"MNT-{uuid4().hex[:8].upper()}"

    ticket = MaintenanceTicket(
        location=payload.location.strip(),
        issue=payload.issue.strip(),
        priority=payload.priority.lower(),
        status="open",
        assigned_team="Campus Maintenance Team",
        action_id=action_id,
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return success_response(
        message="Maintenance ticket created and assigned to the Campus Maintenance Team.",
        action_id=action_id,
        data={
            "ticket_id": ticket.id,
            "location": ticket.location,
            "issue": ticket.issue,
            "priority": ticket.priority,
            "status": ticket.status,
            "assigned_team": ticket.assigned_team,
            "expected_sla": "4 hours" if ticket.priority in ["high", "critical"] else "24 hours",
        },
    )


@app.post(
    "/api/grievance/submit",
    status_code=status.HTTP_201_CREATED,
    tags=["Grievances"],
)
def submit_grievance(
    payload: GrievanceCreate,
    db: Session = Depends(get_db),
):
    get_student_or_404(payload.student_id, db)

    action_id = f"GRV-{uuid4().hex[:8].upper()}"

    grievance = Grievance(
        student_id=payload.student_id,
        category=payload.category.strip(),
        description=payload.description.strip(),
        priority=payload.priority.lower(),
        status="submitted",
        action_id=action_id,
    )

    db.add(grievance)
    db.commit()
    db.refresh(grievance)

    return success_response(
        message="Grievance submitted successfully and routed for review.",
        action_id=action_id,
        data={
            "grievance_id": grievance.id,
            "student_id": grievance.student_id,
            "category": grievance.category,
            "description": grievance.description,
            "priority": grievance.priority,
            "status": grievance.status,
        },
    )


@app.get("/api/finance/fees", tags=["Finance"])
def get_fee_status(
    student_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    student = get_student_or_404(student_id, db)

    fee_records = (
        db.query(FeeRecord)
        .filter(FeeRecord.student_id == student_id)
        .order_by(FeeRecord.due_date)
        .all()
    )

    records = []
    for fee in fee_records:
        outstanding = round(max(fee.total_amount - fee.paid_amount, 0), 2)
        records.append(
            {
                "fee_record_id": fee.id,
                "academic_year": fee.academic_year,
                "total_amount": fee.total_amount,
                "paid_amount": fee.paid_amount,
                "outstanding_amount": outstanding,
                "due_date": fee.due_date.isoformat(),
                "payment_status": fee.payment_status,
            }
        )

    return success_response(
        message="Fee status retrieved successfully.",
        data={
            "student": {"id": student.id, "name": student.name},
            "fee_records": records,
        },
    )


@app.get("/api/events/search", tags=["Events"])
def search_events(
    query: str = Query(..., min_length=1, max_length=100),
    db: Session = Depends(get_db),
):
    cleaned_query = query.strip()

    events = (
        db.query(Event)
        .filter(
            or_(
                Event.title.ilike(f"%{cleaned_query}%"),
                Event.description.ilike(f"%{cleaned_query}%"),
                Event.category.ilike(f"%{cleaned_query}%"),
            )
        )
        .order_by(Event.event_date, Event.start_time)
        .all()
    )

    return success_response(
        message=f"{len(events)} event(s) found for '{cleaned_query}'.",
        data={
            "events": [
                {
                    "id": event.id,
                    "title": event.title,
                    "description": event.description,
                    "category": event.category,
                    "event_date": event.event_date.isoformat(),
                    "start_time": event.start_time,
                    "end_time": event.end_time,
                    "venue": event.venue,
                    "capacity": event.capacity,
                    "registered_count": event.registered_count,
                    "available_seats": max(
                        event.capacity - event.registered_count, 0
                    ),
                }
                for event in events
            ]
        },
    )


@app.post(
    "/api/events/register",
    status_code=status.HTTP_201_CREATED,
    tags=["Events"],
)
def register_for_event(
    payload: EventRegistrationCreate,
    db: Session = Depends(get_db),
):
    student = get_student_or_404(payload.student_id, db)

    event = db.query(Event).filter(Event.id == payload.event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {payload.event_id} was not found.",
        )

    if event.registered_count >= event.capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This event is already full.",
        )

    existing_registration = (
        db.query(EventRegistration)
        .filter(
            EventRegistration.student_id == payload.student_id,
            EventRegistration.event_id == payload.event_id,
        )
        .first()
    )

    if existing_registration:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student is already registered for this event.",
        )

    registration = EventRegistration(
        student_id=payload.student_id,
        event_id=payload.event_id,
        status="confirmed",
    )

    event.registered_count += 1

    db.add(registration)
    db.commit()
    db.refresh(registration)

    action_id = f"EVENT-{registration.id:05d}"

    return success_response(
        message=f"{student.name} is successfully registered for {event.title}.",
        action_id=action_id,
        data={
            "registration_id": registration.id,
            "student_id": student.id,
            "event_id": event.id,
            "event_title": event.title,
            "event_date": event.event_date.isoformat(),
            "start_time": event.start_time,
            "venue": event.venue,
            "registration_status": registration.status,
        },
    )


@app.post("/api/chat", tags=["CampusOS AI"])
def campusos_chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
):
    get_student_or_404(payload.student_id, db)

    response = route_campus_request(
        message=payload.message,
        student_id=payload.student_id,
        db=db,
    )

    response["timestamp"] = datetime.utcnow().isoformat()
    return response


@app.post(
    "/api/maintenance/confirm",
    status_code=status.HTTP_201_CREATED,
    tags=["Maintenance"],
)
def confirm_maintenance_ticket(
    payload: MaintenanceConfirmation,
    db: Session = Depends(get_db),
):
    if not payload.confirmed:
        return {
            "success": True,
            "message": (
                "Maintenance ticket creation was cancelled by the user."
            ),
            "data": {
                "ticket_created": False,
                "location": payload.location,
            },
        }

    action_id = f"MNT-{uuid4().hex[:8].upper()}"

    ticket = MaintenanceTicket(
        location=payload.location.strip(),
        issue=payload.issue.strip(),
        priority=payload.priority.lower(),
        status="open",
        assigned_team="Campus Maintenance Team",
        action_id=action_id,
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return {
        "success": True,
        "message": (
            "Maintenance ticket created successfully and assigned to the "
            "Campus Maintenance Team."
        ),
        "action_id": action_id,
        "data": {
            "ticket_created": True,
            "ticket_id": ticket.id,
            "location": ticket.location,
            "issue": ticket.issue,
            "priority": ticket.priority,
            "status": ticket.status,
            "assigned_team": ticket.assigned_team,
            "expected_sla": "4 hours"
            if ticket.priority in ["high", "critical"]
            else "24 hours",
            "created_at": ticket.created_at.isoformat(),
        },
    }
@app.post(
    "/api/decision/attendance-impact",
    tags=["Campus Decision Engine"],
)
def analyze_attendance_impact(
    payload: AttendanceImpactRequest,
    db: Session = Depends(get_db),
):
    get_student_or_404(payload.student_id, db)

    result = get_attendance_impact(
        student_id=payload.student_id,
        subject=payload.subject,
        planned_missed_classes=payload.planned_missed_classes,
        db=db,
    )

    result["agent"] = "Campus Decision Engine"
    result["tools_used"] = [
        "get_attendance",
        "simulate_attendance_impact",
        "retrieve_academic_regulations",
    ]
    result["timestamp"] = datetime.utcnow().isoformat()

    return result

@app.post(
    "/api/decision/campus",
    tags=["Campus Decision Engine"],
)
def analyze_campus_decision(
    payload: CampusDecisionRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Unified decision endpoint:
    - Interprets a student intent (e.g. attend an event)
    - Checks attendance impact
    - Checks timetable conflict (simplified)
    - Uses policy evidence
    - Returns a single, explainable decision
    """

    get_student_or_404(payload.student_id, db)

    # Default subject if not provided
    subject = payload.subject or "Database Management Systems"

    # 1. Attendance impact
    attendance_result = get_attendance_impact(
        student_id=payload.student_id,
        subject=subject,
        planned_missed_classes=payload.planned_missed_classes,
        db=db,
    )

    if not attendance_result.get("success"):
        return {
            "agent": "Campus Decision Engine",
            "tools_used": ["get_attendance", "simulate_attendance_impact"],
            "timestamp": datetime.utcnow().isoformat(),
            "success": False,
            "message": attendance_result.get(
                "message", "Attendance impact analysis failed."
            ),
        }

    data = attendance_result["data"]
    decision_data = data["decision"]
    policy_evidence = data["policy_evidence"]

    # 2. Simple timetable conflict heuristic
    # In a real system, this would query a timetable service.
    # Here we simulate: if event_name and subject are both provided, assume conflict.
    conflict_detected = bool(payload.event_name and payload.subject)

    conflict_note = ""
    if conflict_detected:
        conflict_note = (
            f"The requested activity overlaps with {subject}. "
            "This would require missing one class."
        )
    else:
        conflict_note = (
            "No timetable conflict was detected for the requested activity."
        )

    # 3. Build a unified decision
    risk_level = decision_data["risk_level"]
    eligible_for_leave = decision_data["eligible_for_event_leave"]

    if risk_level == "low" and eligible_for_leave:
        final_recommendation = (
            f"{decision_data['recommendation']} "
            f"{conflict_note} You may proceed with event registration and "
            "submit an academic-event leave request."
        )
        action_suggestion = "approve_and_execute"
    elif risk_level == "high":
        final_recommendation = (
            f"{decision_data['recommendation']} "
            f"{conflict_note} It is not recommended to miss this class. "
            "Consider attending the class instead of the event."
        )
        action_suggestion = "decline"
    else:
        final_recommendation = (
            f"{decision_data['recommendation']} "
            f"{conflict_note} You must first restore attendance eligibility "
            "before considering additional absences."
        )
        action_suggestion = "decline"

    return {
        "agent": "Campus Decision Engine",
        "tools_used": [
            "get_attendance",
            "simulate_attendance_impact",
            "retrieve_academic_regulations",
            "check_timetable_conflict",
        ],
        "timestamp": datetime.utcnow().isoformat(),
        "success": True,
        "message": "Campus decision analysis completed.",
        "data": {
            "student": data["student"],
            "intent": payload.intent,
            "event": {
                "name": payload.event_name,
                "time": payload.event_time,
            },
            "subject": subject,
            "attendance_impact": {
                "current_percentage": data["current_attendance"]["percentage"],
                "projected_percentage": data["simulation"]["projected_percentage"],
                "minimum_required_percentage": data["simulation"]["minimum_required_percentage"],
            },
            "timetable": {
                "conflict_detected": conflict_detected,
                "note": conflict_note,
            },
            "decision": {
                "risk_level": risk_level,
                "eligible_for_event_leave": eligible_for_leave,
                "recommendation": final_recommendation,
                "action_suggestion": action_suggestion,
            },
            "policy_evidence": policy_evidence,
        },
    }