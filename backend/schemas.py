from datetime import date

from pydantic import BaseModel, Field


class LeaveRequestCreate(BaseModel):
    student_id: int = Field(gt=0)
    start_date: date
    end_date: date
    reason: str = Field(min_length=5, max_length=500)


class MaintenanceTicketCreate(BaseModel):
    location: str = Field(min_length=2, max_length=150)
    issue: str = Field(min_length=5, max_length=1000)
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$")


class GrievanceCreate(BaseModel):
    student_id: int = Field(gt=0)
    category: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=5, max_length=1000)
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$")


class EventRegistrationCreate(BaseModel):
    student_id: int = Field(gt=0)
    event_id: int = Field(gt=0)
    
class ChatRequest(BaseModel):
    student_id: int = Field(default=1, gt=0)
    message: str = Field(min_length=2, max_length=1000)   
  
class MaintenanceConfirmation(BaseModel):
    location: str = Field(min_length=2, max_length=150)
    issue: str = Field(min_length=5, max_length=1000)
    priority: str = Field(
        default="medium",
        pattern="^(low|medium|high|critical)$",
    )
    confirmed: bool
    
class AttendanceImpactRequest(BaseModel):
    student_id: int = Field(default=1, gt=0)
    subject: str = Field(min_length=2, max_length=120)
    planned_missed_classes: int = Field(default=1, ge=0, le=10)
class CampusDecisionRequest(BaseModel):
    student_id: int = Field(default=1, gt=0)
    intent: str = Field(min_length=5, max_length=500)
    event_name: str | None = None
    event_time: str | None = None  # e.g. "2026-08-23T14:00:00"
    subject: str | None = None     # e.g. "Database Management Systems"
    planned_missed_classes: int = Field(default=1, ge=0, le=10)