"""
Main FastAPI application
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import db
from models import (
    ProjectCreate, TaskCreate, TaskUpdate, 
    CalendarSettingsUpdate, BlockedTimeCreate,
    TimeAllocationCreate, TimeAllocationEdit,
    ReallocateRequest, EmailSettingsUpdate
)
from datetime import datetime, date, timedelta
import json

# Import scheduling modules
from scheduling import (
    auto_schedule_task, auto_schedule_all_tasks, 
    attempt_with_bumping, reallocate_to_available_time,
    check_deadline_feasibility, SchedulingError, has_conflict
)
from rrule_utils import (
    validate_rrule, generate_recurring_slots, 
    edit_recurring_instance, delete_recurring_instance,
    regenerate_all_recurring_slots, RecurrenceError
)
from email_reminders import (
    send_monday_digest, send_daily_deadline_alert,
    test_email_connection, get_email_settings as get_email_settings_from_db
)

app = FastAPI(title="PhD Task Manager", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def serialize_for_json(obj):
    """Convert dates/datetimes to strings for JSON serialization"""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    return obj


# ============================================================================
# PROJECTS
# ============================================================================

@app.get("/projects")
def get_projects():
    """Get all projects"""
    projects = db.execute("SELECT * FROM projects ORDER BY name")
    return {"projects": projects}


@app.post("/projects")
def create_project(project: ProjectCreate):
    """Create a new project"""
    project_id = db.insert('projects', project.dict())
    return {"id": project_id, **project.dict()}


@app.delete("/projects/{project_id}")
def delete_project(project_id: int):
    """Delete a project"""
    # Check if any tasks are using this project
    tasks = db.execute("SELECT COUNT(*) as count FROM tasks WHERE project_id = ?", (project_id,))
    if tasks[0]['count'] > 0:
        raise HTTPException(400, "Cannot delete project with existing tasks")
    
    db.delete('projects', 'id = ?', (project_id,))
    return {"success": True}


# ============================================================================
# TASKS
# ============================================================================

@app.get("/tasks")
def get_tasks(
    status: str = None,
    project_id: int = None,
    include_archived: bool = False
):
    """Get all tasks with optional filters"""
    query = """
        SELECT t.*, p.name as project_name, p.colour as project_colour
        FROM tasks t
        LEFT JOIN projects p ON t.project_id = p.id
        WHERE 1=1
    """
    params = []
    
    if status:
        query += " AND t.status = ?"
        params.append(status)
    
    if project_id:
        query += " AND t.project_id = ?"
        params.append(project_id)
    
    if not include_archived:
        query += " AND t.archived = 0"
    
    query += " ORDER BY t.priority DESC, t.deadline ASC"
    
    tasks = db.execute(query, tuple(params))
    return {"tasks": tasks}


@app.get("/tasks/unscheduled")
def get_unscheduled_tasks():
    """Get tasks that have no scheduled slots or are only partially scheduled"""
    tasks = db.execute("""
        SELECT 
            t.*,
            p.name as project_name,
            p.colour as project_colour,
            COALESCE(SUM(CAST((julianday(s.end_datetime) - julianday(s.start_datetime)) * 24 AS REAL)), 0) as scheduled_hours
        FROM tasks t
        LEFT JOIN projects p ON t.project_id = p.id
        LEFT JOIN scheduled_slots s ON t.id = s.task_id
            AND (s.is_override = 0 OR (s.is_override = 1 AND s.start_datetime IS NOT NULL))
        WHERE t.status != 'completed'
        AND t.archived = 0
        AND t.has_time_allocation = 0
        GROUP BY t.id
        HAVING scheduled_hours < t.estimated_hours
        ORDER BY t.deadline ASC, t.priority DESC
    """)
    
    result = []
    for task in tasks:
        result.append({
            **task,
            "hours_remaining": task['estimated_hours'] - task['scheduled_hours']
        })
    
    return {"unscheduled_tasks": result}


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    """Get a single task by ID"""
    task = db.execute_one("""
        SELECT t.*, p.name as project_name, p.colour as project_colour
        FROM tasks t
        LEFT JOIN projects p ON t.project_id = p.id
        WHERE t.id = ?
    """, (task_id,))
    
    if not task:
        raise HTTPException(404, "Task not found")
    
    return task


@app.post("/tasks")
def create_task(task: TaskCreate):
    """Create a new task"""
    # Validate
    if task.deadline and task.start_date and task.deadline < task.start_date:
        raise HTTPException(400, "Deadline cannot be before start date")
    
    task_dict = task.dict()
    task_dict['has_time_allocation'] = False
    task_dict['status'] = 'not_started'
    
    task_id = db.insert('tasks', task_dict)
    
    # Log activity
    db.insert('activity_log', {
        'action': 'create_task',
        'entity_type': 'task',
        'entity_id': task_id,
        'new_data': json.dumps(task_dict)
    })
    
    return {"id": task_id, **task_dict}


@app.patch("/tasks/{task_id}")
def update_task(task_id: int, updates: TaskUpdate):
    """Update a task"""
    task = db.execute_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
    if not task:
        raise HTTPException(404, "Task not found")
    
    update_dict = updates.dict(exclude_none=True)
    
    if update_dict:
        db.update('tasks', update_dict, 'id = ?', (task_id,))
        
        # Log activity
        db.insert('activity_log', {
            'action': 'update_task',
            'entity_type': 'task',
            'entity_id': task_id,
            'old_data': json.dumps(task),
            'new_data': json.dumps(update_dict)
        })
    
    return get_task(task_id)


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    """Delete a task and all its scheduled slots"""
    task = db.execute_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
    if not task:
        raise HTTPException(404, "Task not found")
    
    # Log before deleting
    db.insert('activity_log', {
        'action': 'delete_task',
        'entity_type': 'task',
        'entity_id': task_id,
        'old_data': json.dumps(task)
    })
    
    # Delete scheduled slots
    db.delete('scheduled_slots', 'task_id = ?', (task_id,))
    
    # Delete time allocations
    db.delete('time_allocations', 'task_id = ?', (task_id,))
    
    # Delete task
    db.delete('tasks', 'id = ?', (task_id,))
    
    return {"success": True}


@app.post("/tasks/{task_id}/complete")
def complete_task(task_id: int):
    """Mark task as completed and remove future scheduled slots"""
    task = db.execute_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
    if not task:
        raise HTTPException(404, "Task not found")
    
    now = datetime.now()
    
    # Update task
    db.update('tasks', {
        'status': 'completed',
        'completed_at': now.isoformat()
    }, 'id = ?', (task_id,))
    
    # Delete future slots
    deleted = db.execute("""
        SELECT COUNT(*) as count FROM scheduled_slots
        WHERE task_id = ? AND start_datetime > ?
    """, (task_id, now.isoformat()))
    
    db.delete('scheduled_slots', 
              'task_id = ? AND start_datetime > ?', 
              (task_id, now.isoformat()))
    
    # End time allocation if exists
    db.update('time_allocations', {
        'end_date': date.today().isoformat()
    }, 'task_id = ?', (task_id,))
    
    return {
        "success": True,
        "deleted_future_slots": deleted[0]['count']
    }


# ============================================================================
# SCHEDULED SLOTS
# ============================================================================

@app.get("/slots")
def get_slots(start_date: date = None, end_date: date = None):
    """Get scheduled slots with optional date range filter"""
    query = """
        SELECT 
            s.*,
            t.title,
            t.priority,
            t.status,
            t.is_reschedulable,
            p.name as project_name,
            p.colour as project_colour
        FROM scheduled_slots s
        JOIN tasks t ON s.task_id = t.id
        LEFT JOIN projects p ON t.project_id = p.id
        WHERE (s.is_override = 0 OR (s.is_override = 1 AND s.start_datetime IS NOT NULL))
    """
    params = []
    
    if start_date:
        query += " AND DATE(s.start_datetime) >= ?"
        params.append(start_date.isoformat())
    
    if end_date:
        query += " AND DATE(s.start_datetime) <= ?"
        params.append(end_date.isoformat())
    
    query += " ORDER BY s.start_datetime"
    
    slots = db.execute(query, tuple(params))
    return {"slots": slots}


@app.delete("/slots/{slot_id}")
def delete_slot(slot_id: int):
    """Delete a scheduled slot"""
    slot = db.execute_one("SELECT * FROM scheduled_slots WHERE id = ?", (slot_id,))
    if not slot:
        raise HTTPException(404, "Slot not found")
    
    if slot['source'] == 'allocation':
        # Mark as deleted override so it doesn't regenerate
        db.update('scheduled_slots', {
            'is_override': 1,
            'start_datetime': None,
            'end_datetime': None
        }, 'id = ?', (slot_id,))
    else:
        db.delete('scheduled_slots', 'id = ?', (slot_id,))
    
    return {"success": True}


@app.post("/slots/{slot_id}/complete")
def complete_slot(slot_id: int):
    """Mark a single slot as completed"""
    slot = db.execute_one("SELECT * FROM scheduled_slots WHERE id = ?", (slot_id,))
    if not slot:
        raise HTTPException(404, "Slot not found")
    
    db.update('scheduled_slots', {
        'completed': 1,
        'completed_at': datetime.now().isoformat()
    }, 'id = ?', (slot_id,))
    
    return {"success": True}


# ============================================================================
# BLOCKED TIMES
# ============================================================================

@app.get("/blocked-times")
def get_blocked_times():
    """Get all blocked times"""
    blocks = db.execute("SELECT * FROM blocked_times ORDER BY start_datetime")
    return {"blocked_times": blocks}


@app.post("/blocked-times")
def create_blocked_time(block: BlockedTimeCreate):
    """Create a blocked time period"""
    block_dict = block.dict()
    block_dict['is_recurring'] = bool(block.rrule)
    
    block_id = db.insert('blocked_times', {
        'title': block_dict['title'],
        'description': block_dict['description'],
        'start_datetime': block_dict['start_datetime'].isoformat(),
        'end_datetime': block_dict['end_datetime'].isoformat(),
        'rrule': block_dict['rrule'],
        'is_recurring': block_dict['is_recurring']
    })
    
    return {"id": block_id, **block_dict}


@app.delete("/blocked-times/{block_id}")
def delete_blocked_time(block_id: int):
    """Delete a blocked time"""
    db.delete('blocked_times', 'id = ?', (block_id,))
    return {"success": True}


# ============================================================================
# CALENDAR SETTINGS
# ============================================================================

@app.get("/settings/calendar")
def get_calendar_settings():
    """Get calendar settings"""
    settings = db.execute_one("SELECT * FROM calendar_settings WHERE id = 1")
    if settings:
        settings['excluded_dates'] = json.loads(settings['excluded_dates'])
    return settings


@app.patch("/settings/calendar")
def update_calendar_settings(updates: CalendarSettingsUpdate):
    """Update calendar settings"""
    update_dict = updates.dict(exclude_none=True)
    
    if 'excluded_dates' in update_dict:
        update_dict['excluded_dates'] = json.dumps(update_dict['excluded_dates'])
    
    if update_dict:
        db.update('calendar_settings', update_dict, 'id = 1')
    
    return get_calendar_settings()


# ============================================================================
# SCHEDULING
# ============================================================================

@app.post("/schedule/auto")
def auto_schedule():
    """Auto-schedule all unscheduled, reschedulable tasks"""
    try:
        result = auto_schedule_all_tasks()
        return result
    except SchedulingError as e:
        raise HTTPException(400, str(e))


@app.post("/schedule/task/{task_id}")
def schedule_single_task(task_id: int, force_bump: bool = False):
    """
    Schedule a single task
    If force_bump=True, will bump lower priority tasks if needed
    """
    task = db.execute_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
    if not task:
        raise HTTPException(404, "Task not found")
    
    try:
        if force_bump or task['priority'] >= 4:
            result = attempt_with_bumping(task_id)
        else:
            result = auto_schedule_task(task_id)
        
        return result
    except SchedulingError as e:
        raise HTTPException(400, str(e))


@app.post("/tasks/with-scheduling")
def create_task_with_scheduling(task: TaskCreate, force_bump: bool = False):
    """
    Create task and automatically schedule it
    High priority tasks will bump lower priority ones if needed
    """
    # Validate
    if task.deadline and task.start_date and task.deadline < task.start_date:
        raise HTTPException(400, "Deadline cannot be before start date")
    
    task_dict = task.dict()
    task_dict['has_time_allocation'] = False
    task_dict['status'] = 'not_started'
    
    task_id = db.insert('tasks', task_dict)
    
    # Log activity
    db.insert('activity_log', {
        'action': 'create_task',
        'entity_type': 'task',
        'entity_id': task_id,
        'new_data': json.dumps(serialize_for_json(task_dict))
    })
    
    # Try to schedule
    should_bump = force_bump or task.priority >= 4
    
    try:
        if should_bump:
            schedule_result = attempt_with_bumping(task_id)
        else:
            schedule_result = auto_schedule_task(task_id)
        
        return {
            "task_id": task_id,
            **task_dict,
            "scheduling": schedule_result
        }
    except SchedulingError as e:
        # Task created but couldn't schedule
        return {
            "task_id": task_id,
            **task_dict,
            "scheduling": {
                "scheduled": False,
                "error": str(e)
            }
        }


@app.post("/schedule/reallocate-now")
def reallocate_now(request: ReallocateRequest):
    """
    Find tasks that could be moved into newly available time
    """
    try:
        result = reallocate_to_available_time(
            request.available_start,
            request.available_end,
            request.mode,
            request.max_suggestions
        )
        return result
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/schedule/reallocate-accept/{slot_id}")
def accept_reallocation(slot_id: int, new_start: datetime):
    """User accepts a reallocation suggestion"""
    slot = db.execute_one("SELECT * FROM scheduled_slots WHERE id = ?", (slot_id,))
    if not slot:
        raise HTTPException(404, "Slot not found")
    
    # Check for conflicts
    duration = (datetime.fromisoformat(slot['end_datetime']) - 
                datetime.fromisoformat(slot['start_datetime']))
    new_end = new_start + duration
    
    conflict = has_conflict(new_start, new_end, exclude_slot_id=slot_id)
    if conflict['has_conflict']:
        raise HTTPException(409, "Time slot conflicts with existing schedule")
    
    # Move the slot
    db.update('scheduled_slots', {
        'start_datetime': new_start.isoformat(),
        'end_datetime': new_end.isoformat(),
        'source': 'manual',
        'is_override': 1,
        'original_start': slot['start_datetime']
    }, 'id = ?', (slot_id,))
    
    db.insert('activity_log', {
        'action': 'reallocate_accept',
        'entity_type': 'slot',
        'entity_id': slot_id,
        'old_data': json.dumps({'start': slot['start_datetime']}),
        'new_data': json.dumps({'start': new_start.isoformat()})
    })
    
    return {"success": True}


@app.put("/slots/{slot_id}/move")
def move_slot(slot_id: int, new_start: datetime):
    """Manually move a scheduled slot to a new time"""
    slot = db.execute_one("SELECT * FROM scheduled_slots WHERE id = ?", (slot_id,))
    if not slot:
        raise HTTPException(404, "Slot not found")
    
    # Check task is reschedulable
    task = db.execute_one("SELECT * FROM tasks WHERE id = ?", (slot['task_id'],))
    if not task['is_reschedulable'] and slot['source'] != 'manual':
        raise HTTPException(400, "This task cannot be rescheduled")
    
    # Calculate duration
    duration = (datetime.fromisoformat(slot['end_datetime']) - 
                datetime.fromisoformat(slot['start_datetime']))
    new_end = new_start + duration
    
    # Check for conflicts
    conflict = has_conflict(new_start, new_end, exclude_slot_id=slot_id)
    if conflict['has_conflict']:
        raise HTTPException(409, "Time slot conflicts with existing schedule")
    
    # Update slot
    db.update('scheduled_slots', {
        'start_datetime': new_start.isoformat(),
        'end_datetime': new_end.isoformat(),
        'is_override': 1,
        'original_start': slot.get('original_start') or slot['start_datetime'],
        'source': 'manual'
    }, 'id = ?', (slot_id,))
    
    return {"success": True}


@app.get("/schedule/feasibility/{task_id}")
def check_task_feasibility_endpoint(task_id: int):
    """Check if a task can fit within its deadline"""
    task = db.execute_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
    if not task:
        raise HTTPException(404, "Task not found")
    
    try:
        result = check_deadline_feasibility(task)
        return result
    except Exception as e:
        raise HTTPException(400, str(e))


# ============================================================================
# TIME ALLOCATIONS (Recurring Patterns)
# ============================================================================

@app.post("/time-allocations")
def create_time_allocation(allocation: TimeAllocationCreate):
    """Create a recurring time allocation for a task"""
    # Validate task exists
    task = db.execute_one("SELECT * FROM tasks WHERE id = ?", (allocation.task_id,))
    if not task:
        raise HTTPException(404, "Task not found")
    
    # Validate rrule
    validation = validate_rrule(allocation.rrule)
    if not validation['valid']:
        raise HTTPException(400, f"Invalid rrule: {validation['error']}")
    
    # Create allocation
    allocation_id = db.insert('time_allocations', {
        'task_id': allocation.task_id,
        'rrule': allocation.rrule,
        'duration_hours': allocation.duration_hours,
        'time_of_day': allocation.time_of_day,
        'start_date': allocation.start_date.isoformat(),
        'end_date': allocation.end_date.isoformat() if allocation.end_date else None
    })
    
    # Mark task as having time allocation
    db.update('tasks', {'has_time_allocation': 1}, 'id = ?', (allocation.task_id,))
    
    # Generate slots
    try:
        generated = generate_recurring_slots(allocation_id)
        return {
            "id": allocation_id,
            "slots_generated": len(generated)
        }
    except RecurrenceError as e:
        raise HTTPException(400, str(e))


@app.get("/time-allocations/{task_id}")
def get_time_allocations(task_id: int):
    """Get time allocations for a task"""
    allocations = db.execute("""
        SELECT * FROM time_allocations WHERE task_id = ?
    """, (task_id,))
    return {"allocations": allocations}


@app.put("/slots/{slot_id}/edit-recurrence")
def edit_recurring_slot(slot_id: int, edit: TimeAllocationEdit):
    """Edit a recurring time allocation instance"""
    try:
        result = edit_recurring_instance(
            slot_id=slot_id,
            mode=edit.mode,
            new_rrule=edit.rrule,
            new_duration=edit.duration_hours,
            new_time=edit.time_of_day
        )
        return result
    except RecurrenceError as e:
        raise HTTPException(400, str(e))


@app.post("/time-allocations/validate-rrule")
def validate_rrule_endpoint(rrule: str):
    """Validate an rrule string and show example dates"""
    result = validate_rrule(rrule)
    if not result['valid']:
        raise HTTPException(400, result['error'])
    return result


# ============================================================================
# EMAIL SETTINGS & REMINDERS
# ============================================================================

@app.get("/settings/email")
def get_email_settings():
    """Get email settings (password is masked)"""
    settings = get_email_settings_from_db()
    if settings and settings.get('smtp_password'):
        settings['smtp_password'] = '********'  # Mask password
    return settings


@app.patch("/settings/email")
def update_email_settings(updates: EmailSettingsUpdate):
    """Update email settings"""
    update_dict = updates.dict(exclude_none=True)
    
    if update_dict:
        db.update('email_settings', update_dict, 'id = 1')
    
    return get_email_settings()


@app.post("/settings/email/test")
def test_email():
    """Test email connection"""
    settings = get_email_settings_from_db()
    if not settings:
        raise HTTPException(400, "Email settings not configured")
    
    result = test_email_connection(settings)
    if not result['success']:
        raise HTTPException(400, f"Email test failed: {result['error']}")
    
    return result


@app.post("/reminders/send-monday-digest")
def send_digest_now():
    """Manually trigger Monday digest email"""
    result = send_monday_digest()
    return result


@app.post("/reminders/send-daily-alert")
def send_alert_now():
    """Manually trigger daily deadline alert"""
    result = send_daily_deadline_alert()
    return result
    
    return get_calendar_settings()


# ============================================================================
# STATISTICS
# ============================================================================

@app.get("/stats/overview")
def get_stats():
    """Get dashboard statistics"""
    
    # Task counts by status
    task_stats = db.execute("""
        SELECT status, COUNT(*) as count
        FROM tasks
        WHERE archived = 0
        GROUP BY status
    """)
    by_status = {stat['status']: stat['count'] for stat in task_stats}
    
    # Task counts by priority
    priority_stats = db.execute("""
        SELECT priority, COUNT(*) as count
        FROM tasks
        WHERE archived = 0 AND status != 'completed'
        GROUP BY priority
    """)
    by_priority = {stat['priority']: stat['count'] for stat in priority_stats}
    
    # Total estimated hours remaining
    total_hours = db.execute("""
        SELECT SUM(estimated_hours) as total
        FROM tasks
        WHERE status != 'completed' AND archived = 0
    """)
    
    # Upcoming deadlines
    deadlines = db.execute("""
        SELECT t.id, t.title, t.deadline, t.priority, p.name as project_name
        FROM tasks t
        LEFT JOIN projects p ON t.project_id = p.id
        WHERE t.status != 'completed'
        AND t.deadline IS NOT NULL
        AND t.deadline <= DATE('now', '+7 days')
        AND t.archived = 0
        ORDER BY t.deadline ASC
        LIMIT 5
    """)
    
    return {
        "tasks": {
            "total": sum(by_status.values()),
            "by_status": by_status,
            "by_priority": by_priority
        },
        "hours": {
            "total_estimated": total_hours[0]['total'] or 0
        },
        "upcoming_deadlines": deadlines
    }


# ============================================================================
# UTILITY
# ============================================================================

@app.get("/")
def root():
    """API root endpoint"""
    return {
        "message": "PhD Task Manager API",
        "version": "1.0.0",
        "endpoints": {
            "projects": "/projects",
            "tasks": "/tasks",
            "unscheduled_tasks": "/tasks/unscheduled",
            "slots": "/slots",
            "blocked_times": "/blocked-times",
            "auto_schedule": "/schedule/auto",
            "reallocate": "/schedule/reallocate-now",
            "time_allocations": "/time-allocations",
            "calendar_settings": "/settings/calendar",
            "email_settings": "/settings/email",
            "stats": "/stats/overview",
            "docs": "/docs"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
