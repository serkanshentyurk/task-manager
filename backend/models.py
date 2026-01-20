"""
Pydantic models for API request/response validation
"""
from pydantic import BaseModel, Field
from datetime import datetime, date, time
from typing import Optional, Literal, List


class ProjectCreate(BaseModel):
    name: str
    colour: str = "#3B82F6"


class TaskCreate(BaseModel):
    title: str
    project_id: Optional[int] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    priority: int = Field(default=3, ge=1, le=5)
    start_date: Optional[date] = None
    deadline: Optional[date] = None
    estimated_hours: float = Field(gt=0)
    min_session_hours: float = Field(default=2.0, ge=0.5, le=4.0)
    is_reschedulable: bool = True


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    project_id: Optional[int] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    status: Optional[Literal['not_started', 'in_progress', 'completed']] = None
    start_date: Optional[date] = None
    deadline: Optional[date] = None
    estimated_hours: Optional[float] = Field(default=None, gt=0)
    min_session_hours: Optional[float] = Field(default=None, ge=0.5, le=4.0)
    is_reschedulable: Optional[bool] = None


class TimeAllocationCreate(BaseModel):
    task_id: int
    rrule: str  # e.g., "FREQ=WEEKLY;BYDAY=MO,WE,FR"
    duration_hours: float = Field(gt=0, le=4)
    time_of_day: str  # "14:00"
    start_date: date
    end_date: Optional[date] = None


class TimeAllocationEdit(BaseModel):
    rrule: Optional[str] = None
    duration_hours: Optional[float] = Field(default=None, gt=0, le=4)
    time_of_day: Optional[str] = None
    mode: Literal['this_only', 'this_and_future'] = 'this_only'


class BlockedTimeCreate(BaseModel):
    title: str = "Blocked"
    description: Optional[str] = None
    start_datetime: datetime
    end_datetime: datetime
    rrule: Optional[str] = None


class ReallocateRequest(BaseModel):
    available_start: datetime
    available_end: datetime
    mode: Literal['interactive', 'auto'] = 'interactive'
    max_suggestions: int = 5


class CalendarSettingsUpdate(BaseModel):
    work_schedule: Optional[Literal['weekdays', 'all_week', 'custom']] = None
    custom_days: Optional[str] = None  # 'MO,TU,WE,TH,FR'
    work_start_time: Optional[str] = None  # '09:00'
    work_end_time: Optional[str] = None  # '17:00'
    excluded_dates: Optional[List[str]] = None  # ['2025-12-25', '2025-12-26']


class EmailSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    email_address: Optional[str] = None
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    monday_digest: Optional[bool] = None
    daily_deadline_alert: Optional[bool] = None
    alert_hour: Optional[int] = Field(default=None, ge=0, le=23)


class ManualSlotCreate(BaseModel):
    task_id: int
    start_datetime: datetime
    end_datetime: datetime
    is_fixed: bool = False


class SlotMove(BaseModel):
    new_start: datetime
    swap_with_slot_id: Optional[int] = None  # For handling conflicts
