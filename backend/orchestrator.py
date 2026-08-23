import json
import os
import re
from datetime import date, datetime
from typing import Any, TypedDict
from uuid import uuid4

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import Attendance, Event, Exam, FeeRecord, LeaveRequest, Student, Timetable

load_dotenv()


class IntentResult(BaseModel):
    intent: str


class ResponseResult(BaseModel):
    message: str


def _create_intent_classifier():
    if not os.getenv("OPENAI_API_KEY"):
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return ChatOpenAI(
        model=model,
        temperature=0,
    ).with_structured_output(IntentResult)


intent_classifier = _create_intent_classifier()


def _create_response_generator():
    if not os.getenv("OPENAI_API_KEY"):
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return ChatOpenAI(
        model=model,
        temperature=0.2,
    ).with_structured_output(ResponseResult)


response_generator = _create_response_generator()


def _get_student_or_none(student_id: int, db: Session) -> Student | None:
    return db.query(Student).filter(Student.id == student_id).first()


def _timetable_response(student_id: int, db: Session) -> dict[str, Any]:
    student = _get_student_or_none(student_id, db)
    if not student:
        return {
            "success": False,
            "agent": "Academic Agent",
            "message": "I could not find that student profile.",
        }

    entries = (
        db.query(Timetable)
        .filter(Timetable.student_id == student_id)
        .order_by(Timetable.day, Timetable.start_time)
        .all()
    )

    formatted = [
        f"{entry.day}: {entry.subject}, {entry.start_time}-{entry.end_time}, "
        f"{entry.room}, {entry.faculty}"
        for entry in entries
    ]

    return {
        "success": True,
        "agent": "Academic Agent",
        "tools_used": ["get_timetable"],
        "message": f"Here is {student.name}'s timetable.",
        "data": {"timetable": formatted},
    }


def _attendance_response(student_id: int, db: Session) -> dict[str, Any]:
    student = _get_student_or_none(student_id, db)
    if not student:
        return {
            "success": False,
            "agent": "Academic Agent",
            "message": "I could not find that student profile.",
        }

    records = (
        db.query(Attendance)
        .filter(Attendance.student_id == student_id)
        .order_by(Attendance.subject)
        .all()
    )

    formatted = []
    for record in records:
        status = "Safe" if record.percentage >= 75 else "At Risk"
        formatted.append(
            {
                "subject": record.subject,
                "attendance": round(record.percentage, 2),
                "status": status,
            }
        )

    at_risk = [item["subject"] for item in formatted if item["status"] == "At Risk"]

    message = f"Your attendance has been checked. "
    if at_risk:
        message += f"You are below 75% in: {', '.join(at_risk)}."
    else:
        message += "You meet the required 75% attendance in all subjects."

    return {
        "success": True,
        "agent": "Academic Agent",
        "tools_used": ["get_attendance", "check_attendance_policy"],
        "message": message,
        "data": {
            "minimum_required_attendance": 75,
            "attendance": formatted,
        },
    }


def _exam_response(student_id: int, db: Session) -> dict[str, Any]:
    student = _get_student_or_none(student_id, db)
    if not student:
        return {
            "success": False,
            "agent": "Examination Agent",
            "message": "I could not find that student profile.",
        }

    exams = (
        db.query(Exam)
        .filter(
            Exam.department == student.department,
            Exam.semester == student.semester,
        )
        .order_by(Exam.exam_date, Exam.start_time)
        .all()
    )

    formatted = [
        {
            "subject": exam.subject,
            "date": exam.exam_date.isoformat(),
            "time": f"{exam.start_time}-{exam.end_time}",
            "room": exam.room,
            "type": exam.exam_type,
        }
        for exam in exams
    ]

    return {
        "success": True,
        "agent": "Examination Agent",
        "tools_used": ["get_exam_schedule"],
        "message": f"I found {len(formatted)} upcoming exam(s) for you.",
        "data": {"exams": formatted},
    }


def _events_response(message: str, db: Session) -> dict[str, Any]:
    search_terms = ["ai", "hackathon", "workshop", "seminar", "event"]
    selected_term = next((term for term in search_terms if term in message.lower()), "event")

    events = (
        db.query(Event)
        .filter(
            Event.title.ilike(f"%{selected_term}%")
            | Event.description.ilike(f"%{selected_term}%")
            | Event.category.ilike(f"%{selected_term}%")
        )
        .order_by(Event.event_date, Event.start_time)
        .all()
    )

    if not events and selected_term != "event":
        events = db.query(Event).order_by(Event.event_date, Event.start_time).all()

    formatted = [
        {
            "event_id": event.id,
            "title": event.title,
            "date": event.event_date.isoformat(),
            "time": f"{event.start_time}-{event.end_time}",
            "venue": event.venue,
            "available_seats": max(event.capacity - event.registered_count, 0),
        }
        for event in events
    ]

    return {
        "success": True,
        "agent": "Events Agent",
        "tools_used": ["search_events"],
        "message": f"I found {len(formatted)} relevant event(s).",
        "data": {"events": formatted},
    }


def _fees_response(student_id: int, db: Session) -> dict[str, Any]:
    student = _get_student_or_none(student_id, db)
    if not student:
        return {
            "success": False,
            "agent": "Finance Agent",
            "message": "I could not find that student profile.",
        }

    fee_records = (
        db.query(FeeRecord)
        .filter(FeeRecord.student_id == student_id)
        .order_by(FeeRecord.due_date)
        .all()
    )

    formatted = []
    for fee in fee_records:
        outstanding = max(fee.total_amount - fee.paid_amount, 0)
        formatted.append(
            {
                "academic_year": fee.academic_year,
                "total_amount": fee.total_amount,
                "paid_amount": fee.paid_amount,
                "outstanding_amount": outstanding,
                "due_date": fee.due_date.isoformat(),
                "status": fee.payment_status,
            }
        )

    return {
        "success": True,
        "agent": "Finance Agent",
        "tools_used": ["get_fee_status"],
        "message": "I retrieved your fee status.",
        "data": {"fees": formatted},
    }


def _maintenance_intent(message: str) -> bool:
    keywords = [
        "projector",
        "ac ",
        "air conditioner",
        "water dispenser",
        "broken",
        "not working",
        "maintenance",
        "repair",
    ]
    lowered = message.lower()
    return any(keyword in lowered for keyword in keywords)


def _maintenance_draft(message: str) -> dict[str, Any]:
    location_match = re.search(
        r"(room|lab|block|hostel|library)\s*[-#]?\s*([a-z0-9\-]+)",
        message.lower(),
    )
    location = (
        f"{location_match.group(1).title()} {location_match.group(2).upper()}"
        if location_match
        else "Campus location not specified"
    )

    priority = "high" if any(word in message.lower() for word in ["urgent", "exam", "projector"]) else "medium"

    return {
        "success": True,
        "agent": "Maintenance Agent",
        "tools_used": ["classify_maintenance_issue"],
        "message": (
            "I identified a maintenance issue. Please confirm before I create "
            "a ticket for the Campus Maintenance Team."
        ),
        "requires_confirmation": True,
        "suggested_action": "create_maintenance_ticket",
        "data": {
            "location": location,
            "issue": message.strip(),
            "priority": priority,
            "assigned_team": "Campus Maintenance Team",
        },
    }


def determine_intent(user_message: str) -> str:
    lowered = user_message.lower().strip()

    if any(keyword in lowered for keyword in ["grievance", "complaint", "issue with", "report a problem"]):
        return "grievance"
    if any(word in lowered for word in ["leave", "absent", "absence"]):
        return "leave_request"
    if any(keyword in lowered for keyword in ["timetable", "next class", "class today", "schedule"]):
        return "timetable"
    if any(keyword in lowered for keyword in ["attendance", "can i miss", "skip class", "75%"]):
        return "attendance"
    if any(keyword in lowered for keyword in ["exam", "hall ticket", "internal", "semester test"]):
        return "examination"
    if any(keyword in lowered for keyword in ["fee", "fees", "payment", "due amount", "outstanding"]):
        return "fees"
    if any(keyword in lowered for keyword in ["event", "workshop", "hackathon", "seminar", "register"]):
        return "event"
    if _maintenance_intent(lowered):
        return "maintenance"
    return "general"


def handle_leave_query(
    user_message: str,
    db: Session,
    student_id: int,
) -> dict[str, Any]:
    date_match = re.search(
        r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b|\b(\d{4})-(\d{1,2})-(\d{1,2})\b",
        user_message,
    )
    if date_match:
        try:
            if date_match.group(1):
                requested_date = date(
                    int(date_match.group(3)),
                    int(date_match.group(2)),
                    int(date_match.group(1)),
                )
            else:
                requested_date = date(
                    int(date_match.group(4)),
                    int(date_match.group(5)),
                    int(date_match.group(6)),
                )
        except ValueError:
            requested_date = None

        if requested_date:
            reason = re.sub(date_match.group(0), "", user_message).strip(" ,-:")
            reason = re.sub(r"^(leave request|leave|for)\s*", "", reason, flags=re.I).strip()
            if len(reason) >= 5:
                action_id = f"LEAVE-{uuid4().hex[:8].upper()}"
                leave_request = LeaveRequest(
                    student_id=student_id,
                    start_date=requested_date,
                    end_date=requested_date,
                    reason=reason,
                    status="pending",
                    action_id=action_id,
                )
                db.add(leave_request)
                db.commit()
                db.refresh(leave_request)
                return {
                    "success": True,
                    "agent": "Administration Agent",
                    "tools_used": ["apply_leave"],
                    "message": (
                        f"Your leave request for {requested_date.strftime('%d/%m/%Y')} "
                        f"has been submitted for approval due to {reason}."
                    ),
                    "action_id": action_id,
                    "data": {
                        "leave_request_id": leave_request.id,
                        "start_date": requested_date.isoformat(),
                        "end_date": requested_date.isoformat(),
                        "reason": reason,
                        "status": leave_request.status,
                    },
                }

    return {
        "success": True,
        "agent": "Administration Agent",
        "tools_used": ["handle_leave_query"],
        "message": (
            "I can help you create a leave request. Please tell me: "
            "1) the date(s) you need leave, and "
            "2) the reason (e.g., illness, family event, academic event)."
        ),
        "suggested_next_steps": [
            "I need leave for tomorrow due to illness.",
            "I want to apply for academic-event leave for the AI workshop.",
        ],
    }


class CampusGraphState(TypedDict, total=False):
    message: str
    student_id: int
    db: Session
    intent: str
    response: dict[str, Any]


def _llm_intent(message: str) -> str:
    if intent_classifier is None:
        return determine_intent(message)

    prompt = (
        "Classify this campus request into exactly one intent: "
        "leave_request, timetable, attendance, examination, fees, event, "
        f"maintenance, grievance, or general. Request: {message}"
    )
    result = intent_classifier.invoke(prompt)
    valid_intents = {
        "leave_request",
        "timetable",
        "attendance",
        "examination",
        "fees",
        "event",
        "maintenance",
        "grievance",
        "general",
    }
    if result.intent in valid_intents:
        return result.intent
    return determine_intent(message)


def _classify_request(state: CampusGraphState) -> CampusGraphState:
    try:
        intent = _llm_intent(state["message"])
    except Exception:
        intent = determine_intent(state["message"])
    return {"intent": intent}


def _general_response(_: CampusGraphState) -> dict[str, Any]:
    return {
        "success": True,
        "agent": "CampusOS Orchestrator",
        "tools_used": [],
        "message": (
            "I can help with timetable, attendance, examinations, events, "
            "fees, leave requests, grievances, and maintenance tickets. "
            "Try asking: 'What is my next class?'"
        ),
        "data": {},
    }


def _run_agent(state: CampusGraphState, handler) -> CampusGraphState:
    return {"response": handler(state)}


def _academic_agent(state: CampusGraphState) -> CampusGraphState:
    student_id, db = state["student_id"], state["db"]
    handler = _attendance_response if state["intent"] == "attendance" else _timetable_response
    return _run_agent(state, lambda _: handler(student_id, db))


def _exam_agent(state: CampusGraphState) -> CampusGraphState:
    return _run_agent(state, lambda _: _exam_response(state["student_id"], state["db"]))


def _administration_agent(state: CampusGraphState) -> CampusGraphState:
    return _run_agent(
        state,
        lambda _: handle_leave_query(state["message"], state["db"], state["student_id"]),
    )


def _maintenance_agent(state: CampusGraphState) -> CampusGraphState:
    return _run_agent(state, lambda _: _maintenance_draft(state["message"]))


def _grievance_agent(state: CampusGraphState) -> CampusGraphState:
    return _run_agent(
        state,
        lambda _: {
            "success": True,
            "agent": "Grievance Agent",
            "tools_used": ["prepare_grievance_submission"],
            "message": "I can prepare a grievance submission. Please provide the category and describe the issue in detail.",
            "suggested_next_steps": [
                "Category: Facilities. The water dispenser on Block A is not working.",
            ],
        },
    )


def _finance_agent(state: CampusGraphState) -> CampusGraphState:
    return _run_agent(state, lambda _: _fees_response(state["student_id"], state["db"]))


def _events_agent(state: CampusGraphState) -> CampusGraphState:
    return _run_agent(state, lambda _: _events_response(state["message"], state["db"]))


def _route_agent(state: CampusGraphState) -> str:
    routes = {
        "timetable": "academic",
        "attendance": "academic",
        "examination": "examination",
        "leave_request": "administration",
        "maintenance": "maintenance",
        "grievance": "grievance",
        "fees": "finance",
        "event": "events",
        "general": "general",
    }
    return routes.get(state["intent"], "general")


def _general_agent(state: CampusGraphState) -> CampusGraphState:
    return _run_agent(state, lambda _: _general_response(state))


def _generate_response(state: CampusGraphState) -> CampusGraphState:
    response = state["response"]
    if response_generator is None or not response.get("success", True):
        return {}

    prompt = (
        "Write a concise, friendly response to the campus user. Use only the "
        "verified handler response below; do not invent facts. Preserve any "
        "confirmation request or next-step instruction.\n"
        f"User request: {state['message']}\n"
        f"Handler response: {json.dumps(response, default=str)}"
    )
    try:
        result = response_generator.invoke(prompt)
        if result.message.strip():
            response["message"] = result.message.strip()
    except Exception:
        # The deterministic handler response is already verified and remains usable.
        pass
    return {"response": response}


def _build_campus_graph():
    graph = StateGraph(CampusGraphState)
    graph.add_node("classify", _classify_request)
    graph.add_node("academic", _academic_agent)
    graph.add_node("examination", _exam_agent)
    graph.add_node("administration", _administration_agent)
    graph.add_node("maintenance", _maintenance_agent)
    graph.add_node("grievance", _grievance_agent)
    graph.add_node("finance", _finance_agent)
    graph.add_node("events", _events_agent)
    graph.add_node("general", _general_agent)
    graph.add_node("generate_response", _generate_response)
    graph.add_edge(START, "classify")
    graph.add_conditional_edges("classify", _route_agent)
    for agent in [
        "academic",
        "examination",
        "administration",
        "maintenance",
        "grievance",
        "finance",
        "events",
        "general",
    ]:
        graph.add_edge(agent, "generate_response")
    graph.add_edge("generate_response", END)
    return graph.compile()


campus_graph = _build_campus_graph()


def route_campus_request(
    message: str,
    student_id: int,
    db: Session,
) -> dict[str, Any]:
    result = campus_graph.invoke(
        {"message": message, "student_id": student_id, "db": db}
    )
    return result["response"]
