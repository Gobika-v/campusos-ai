import re
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from models import Attendance, Student


POLICY_FILE = Path(__file__).parent / "data" / "academic_regulations.txt"
MINIMUM_ATTENDANCE = 75.0


def load_policy_text() -> str:
    if not POLICY_FILE.exists():
        return ""

    return POLICY_FILE.read_text(encoding="utf-8")


def extract_policy_section(section_number: str) -> dict[str, str]:
    text = load_policy_text()

    if not text:
        return {
            "source": "Academic Regulations 2026",
            "section": section_number,
            "content": "Policy document is not available.",
        }

    pattern = (
        rf"(Section\s+{re.escape(section_number)}:.*?"
        rf")(?=\nSection\s+\d+\.\d+:|\Z)"
    )

    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)

    if not match:
        return {
            "source": "Academic Regulations 2026",
            "section": section_number,
            "content": "Relevant policy section was not found.",
        }

    content = " ".join(match.group(1).split())

    return {
        "source": "Academic Regulations 2026",
        "section": section_number,
        "content": content,
    }


def get_attendance_impact(
    student_id: int,
    subject: str,
    planned_missed_classes: int,
    db: Session,
) -> dict[str, Any]:
    student = db.query(Student).filter(Student.id == student_id).first()

    if not student:
        return {
            "success": False,
            "message": "Student profile was not found.",
        }

    attendance = (
        db.query(Attendance)
        .filter(
            Attendance.student_id == student_id,
            Attendance.subject.ilike(subject.strip()),
        )
        .first()
    )

    if not attendance:
        return {
            "success": False,
            "message": f"No attendance record was found for '{subject}'.",
        }

    missed = max(planned_missed_classes, 0)

    current_percentage = round(
        (attendance.attended_classes / attendance.total_classes) * 100,
        2,
    )

    projected_total = attendance.total_classes + missed
    projected_percentage = round(
        (attendance.attended_classes / projected_total) * 100,
        2,
    )

    current_safe = current_percentage >= MINIMUM_ATTENDANCE
    projected_safe = projected_percentage >= MINIMUM_ATTENDANCE

    classes_needed = 0
    attended = attendance.attended_classes
    total = attendance.total_classes + missed

    while total > 0 and (attended / total) * 100 < MINIMUM_ATTENDANCE:
        attended += 1
        total += 1
        classes_needed += 1

    attendance_policy = extract_policy_section("4.2")
    event_leave_policy = extract_policy_section("6.1")

    if projected_safe:
        recommendation = (
            f"Safe to miss {missed} class(es). Your projected attendance "
            f"will remain above the required 75% threshold."
        )
        risk_level = "low"
        eligible_for_leave = True
    elif current_safe:
        recommendation = (
            f"Not recommended to miss {missed} class(es). Your attendance "
            f"would fall to {projected_percentage}%, below the required 75% threshold."
        )
        risk_level = "high"
        eligible_for_leave = False
    else:
        recommendation = (
            f"You are already below the required 75% attendance threshold. "
            f"Attend at least {classes_needed} consecutive class(es) in {attendance.subject} "
            f"to reach eligibility."
        )
        risk_level = "critical"
        eligible_for_leave = False

    return {
        "success": True,
        "message": "Attendance impact analysis completed.",
        "data": {
            "student": {
                "id": student.id,
                "name": student.name,
            },
            "subject": attendance.subject,
            "current_attendance": {
                "attended_classes": attendance.attended_classes,
                "total_classes": attendance.total_classes,
                "percentage": current_percentage,
            },
            "simulation": {
                "planned_missed_classes": missed,
                "projected_total_classes": projected_total,
                "projected_percentage": projected_percentage,
                "minimum_required_percentage": MINIMUM_ATTENDANCE,
            },
            "decision": {
                "risk_level": risk_level,
                "eligible_for_event_leave": eligible_for_leave,
                "recommendation": recommendation,
                "classes_needed_to_reach_75_percent": classes_needed,
            },
            "policy_evidence": [
                attendance_policy,
                event_leave_policy,
            ],
        },
    }
