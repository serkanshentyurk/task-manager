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
    ReallocateRequest, EmailSettingsUpdate,
    ManualSlotCreate, SlotMove
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


@app.get("/tasks/sanity-check")
def sanity_check_tasks():
    """
    Check that each task's total slot duration matches estimated_hours
    Returns list of tasks with mismatches
    """
    print("=== SANITY CHECK STARTED ===")
    try:
        # Get all active tasks
        print("Fetching active tasks...")
        tasks = db.execute("SELECT * FROM tasks WHERE status != 'completed'")
        print(f"Found {len(tasks)} active tasks")
        
        mismatches = []
        
        for task in tasks:
            print(f"Processing task {task['id']}: {task['title']}")
            try:
                # Get all slots (completed and incomplete) for this task
                slots = db.execute("""
                    SELECT start_datetime, end_datetime, completed
                    FROM scheduled_slots
                    WHERE task_id = ?
                """, (task['id'],))
                
                print(f"  Task {task['id']} has {len(slots)} slots")
                
                # Calculate total scheduled hours
                total_scheduled_hours = 0
                completed_hours = 0
                incomplete_hours = 0
                
                for slot in slots:
                    start = datetime.fromisoformat(slot['start_datetime'].replace('+00:00', '').replace('Z', ''))
                    end = datetime.fromisoformat(slot['end_datetime'].replace('+00:00', '').replace('Z', ''))
                    duration = (end - start).total_seconds() / 3600
                    
                    total_scheduled_hours += duration
                    if slot['completed']:
                        completed_hours += duration
                    else:
                        incomplete_hours += duration
                
                # Check for mismatch
                estimated = task['estimated_hours']
                difference = abs(total_scheduled_hours - estimated)
                
                print(f"  Estimated: {estimated}h, Scheduled: {total_scheduled_hours}h, Diff: {difference}h")
                
                # Allow 0.1 hour tolerance for rounding
                if difference > 0.1:
                    print(f"  MISMATCH FOUND for task {task['id']}")
                    mismatches.append({
                        'task_id': task['id'],
                        'title': task['title'],
                        'estimated_hours': estimated,
                        'scheduled_hours': round(total_scheduled_hours, 2),
                        'completed_hours': round(completed_hours, 2),
                        'incomplete_hours': round(incomplete_hours, 2),
                        'difference': round(estimated - total_scheduled_hours, 2),
                        'slot_count': len(slots)
                    })
            except Exception as e:
                print(f"ERROR processing task {task['id']}: {e}")
                import traceback
                traceback.print_exc()
                # Skip this task and continue
                continue
        
        result = {
            "total_tasks": len(tasks),
            "mismatches": mismatches,
            "mismatch_count": len(mismatches)
        }
        print(f"=== SANITY CHECK COMPLETE: {len(mismatches)} mismatches found ===")
        return result
    except Exception as e:
        print(f"ERROR in sanity_check_tasks: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Sanity check failed: {str(e)}")


@app.get("/slots/fill-suggestions")
def get_fill_suggestions(start_time: str, end_time: str):
    """
    Get suggestions for tasks that could be moved to fill an empty time slot
    Looks at future slots and suggests which could be pulled forward
    """
    print(f"Getting fill suggestions for {start_time} to {end_time}")
    
    try:
        # Parse times
        slot_start = datetime.fromisoformat(start_time.replace('+00:00', '').replace('Z', ''))
        slot_end = datetime.fromisoformat(end_time.replace('+00:00', '').replace('Z', ''))
        slot_duration = (slot_end - slot_start).total_seconds() / 3600
        
        print(f"Available slot duration: {slot_duration}h")
        
        # Get all future incomplete slots (after the empty slot)
        future_slots = db.execute("""
            SELECT s.*, t.title, t.priority, t.deadline, t.is_reschedulable
            FROM scheduled_slots s
            JOIN tasks t ON s.task_id = t.id
            WHERE s.start_datetime > ?
            AND s.completed = 0
            AND s.is_fixed = 0
            AND t.is_reschedulable = 1
            ORDER BY s.start_datetime
        """, (slot_start.isoformat(),))
        
        print(f"Found {len(future_slots)} future movable slots")
        
        suggestions = []
        
        for slot in future_slots:
            # Calculate slot duration
            slot_start_time = datetime.fromisoformat(slot['start_datetime'].replace('+00:00', '').replace('Z', ''))
            slot_end_time = datetime.fromisoformat(slot['end_datetime'].replace('+00:00', '').replace('Z', ''))
            task_duration = (slot_end_time - slot_start_time).total_seconds() / 3600
            
            # Check if it fits in available time
            if task_duration <= slot_duration:
                # Calculate days until scheduled
                days_until = (slot_start_time.date() - slot_start.date()).days
                hours_until = (slot_start_time - slot_start).total_seconds() / 3600
                
                # Calculate priority score (higher = better to move)
                # Factors: task priority, deadline proximity, how far in future
                deadline_score = 0
                if slot['deadline']:
                    deadline_dt = datetime.fromisoformat(slot['deadline'])
                    days_to_deadline = (deadline_dt.date() - slot_start.date()).days
                    deadline_score = max(0, 100 - days_to_deadline)  # Closer deadline = higher score
                
                priority_score = (4 - slot['priority']) * 50  # P1=150, P2=100, P3=50
                future_score = min(hours_until / 24 * 10, 100)  # Further in future = higher score
                
                total_score = priority_score + deadline_score + future_score
                
                suggestions.append({
                    'slot_id': slot['id'],
                    'task_id': slot['task_id'],
                    'task_title': slot['title'],
                    'priority': slot['priority'],
                    'deadline': slot['deadline'],
                    'current_start': slot['start_datetime'],
                    'current_end': slot['end_datetime'],
                    'duration': round(task_duration, 2),
                    'days_until': days_until,
                    'hours_until': round(hours_until, 1),
                    'score': round(total_score, 1)
                })
        
        # Sort by score (highest first)
        suggestions.sort(key=lambda x: x['score'], reverse=True)
        
        # Return top 10 suggestions
        result = {
            'available_duration': round(slot_duration, 2),
            'suggestions': suggestions[:10],
            'total_found': len(suggestions)
        }
        
        print(f"Returning {len(result['suggestions'])} suggestions")
        return result
        
    except Exception as e:
        print(f"ERROR in get_fill_suggestions: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to get suggestions: {str(e)}")


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
    
    # Log activity (serialize dates for JSON)
    db.insert('activity_log', {
        'action': 'create_task',
        'entity_type': 'task',
        'entity_id': task_id,
        'new_data': json.dumps(serialize_for_json(task_dict))
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
        # Check if dates changed
        dates_changed = ('start_date' in update_dict or 'deadline' in update_dict)
        
        db.update('tasks', update_dict, 'id = ?', (task_id,))
        
        # If dates changed and task is auto-scheduled, reschedule it
        if dates_changed and not task['has_time_allocation'] and task['is_reschedulable']:
            # Delete existing non-fixed, incomplete slots (includes auto, manual, and moved slots)
            deleted = db.delete('scheduled_slots', 
                              'task_id = ? AND is_fixed = 0 AND completed = 0 AND source != ?', 
                              (task_id, 'allocation'))
            
            print(f"Deleted {deleted} non-fixed slots for task {task_id} before rescheduling")
            
            # Try to reschedule
            try:
                from scheduling import auto_schedule_task
                auto_schedule_task(task_id)
            except Exception as e:
                # Rescheduling failed, but task update succeeded
                print(f"Warning: Could not reschedule task {task_id}: {e}")
        
        # Log activity (serialize dates for JSON)
        db.insert('activity_log', {
            'action': 'update_task',
            'entity_type': 'task',
            'entity_id': task_id,
            'old_data': json.dumps(serialize_for_json(task)),
            'new_data': json.dumps(serialize_for_json(update_dict))
        })
    
    return get_task(task_id)


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    """Delete a task and all its scheduled slots"""
    task = db.execute_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
    if not task:
        raise HTTPException(404, "Task not found")
    
    # Log before deleting (serialize dates for JSON)
    db.insert('activity_log', {
        'action': 'delete_task',
        'entity_type': 'task',
        'entity_id': task_id,
        'old_data': json.dumps(serialize_for_json(task))
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
    
    # Delete future slots (including today's future slots)
    # Use datetime comparison properly
    deleted_count = db.delete('scheduled_slots', 
                              'task_id = ? AND datetime(start_datetime) > datetime(?)', 
                              (task_id, now.isoformat()))
    
    # End time allocation if exists
    db.update('time_allocations', {
        'end_date': date.today().isoformat()
    }, 'task_id = ?', (task_id,))
    
    return {
        "success": True,
        "deleted_future_slots": deleted_count
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
        AND s.completed = 0
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
    print(f"get_slots: Returning {len(slots)} slots (completed=0 only)")
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


@app.post("/slots/manual")
def create_manual_slot(slot_data: ManualSlotCreate):
    """Create a manual scheduled slot"""
    # Verify task exists
    task = db.execute_one("SELECT * FROM tasks WHERE id = ?", (slot_data.task_id,))
    if not task:
        raise HTTPException(404, "Task not found")
    
    # Calculate duration
    duration = (slot_data.end_datetime - slot_data.start_datetime).total_seconds() / 3600
    
    # Check for conflicts
    conflicts = db.execute("""
        SELECT id, task_id FROM scheduled_slots
        WHERE completed = 0
        AND (
            (start_datetime < ? AND end_datetime > ?)
            OR (start_datetime < ? AND end_datetime > ?)
            OR (start_datetime >= ? AND end_datetime <= ?)
        )
    """, (
        slot_data.end_datetime.isoformat(), slot_data.start_datetime.isoformat(),
        slot_data.end_datetime.isoformat(), slot_data.end_datetime.isoformat(),
        slot_data.start_datetime.isoformat(), slot_data.end_datetime.isoformat()
    ))
    
    if conflicts:
        return {
            "success": False,
            "conflict": True,
            "conflicting_slots": conflicts
        }
    
    # Create the slot
    slot_id = db.insert('scheduled_slots', {
        'task_id': slot_data.task_id,
        'start_datetime': slot_data.start_datetime.isoformat(),
        'end_datetime': slot_data.end_datetime.isoformat(),
        'source': 'manual',
        'is_fixed': 1 if slot_data.is_fixed else 0,
        'completed': 0
    })
    
    return {
        "success": True,
        "slot_id": slot_id,
        "duration_hours": duration
    }


@app.post("/slots/{slot_id}/complete")
def complete_slot(slot_id: int):
    """Mark a single slot as completed, and complete task if all slots are done"""
    slot = db.execute_one("SELECT * FROM scheduled_slots WHERE id = ?", (slot_id,))
    if not slot:
        raise HTTPException(404, "Slot not found")
    
    print(f"Completing slot {slot_id}, task_id={slot['task_id']}")
    
    # Mark this slot complete
    db.update('scheduled_slots', {
        'completed': 1,
        'completed_at': datetime.now().isoformat()
    }, 'id = ?', (slot_id,))
    
    # Check if all slots for this task are now completed
    remaining_slots = db.execute("""
        SELECT COUNT(*) as count FROM scheduled_slots
        WHERE task_id = ?
        AND completed = 0
        AND (is_override = 0 OR (is_override = 1 AND start_datetime IS NOT NULL))
    """, (slot['task_id'],))
    
    remaining_count = remaining_slots[0]['count']
    print(f"Task {slot['task_id']} has {remaining_count} incomplete slots remaining")
    
    # If no incomplete slots remain, mark task as completed
    if remaining_count == 0:
        print(f"All slots complete! Marking task {slot['task_id']} as completed")
        db.update('tasks', {
            'status': 'completed',
            'completed_at': datetime.now().isoformat()
        }, 'id = ?', (slot['task_id'],))
        
        return {"success": True, "completed": True, "task_completed": True}
    
    return {"success": True, "completed": True, "task_completed": False}


@app.patch("/slots/{slot_id}/update-fixed")
def update_slot_fixed(slot_id: int, data: dict):
    """Update the is_fixed property of a slot"""
    slot = db.execute_one("SELECT * FROM scheduled_slots WHERE id = ?", (slot_id,))
    if not slot:
        raise HTTPException(404, "Slot not found")
    
    is_fixed = data.get('is_fixed', 0)
    
    db.update('scheduled_slots', {
        'is_fixed': 1 if is_fixed else 0
    }, 'id = ?', (slot_id,))
    
    return {"success": True, "is_fixed": bool(is_fixed)}


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
def move_slot(slot_id: int, move_data: SlotMove):
    """Manually move a scheduled slot to a new time"""
    try:
        print(f"move_slot called: slot_id={slot_id}, move_data={move_data}")
        
        slot = db.execute_one("SELECT * FROM scheduled_slots WHERE id = ?", (slot_id,))
        if not slot:
            raise HTTPException(404, "Slot not found")
        
        print(f"Slot found: {slot}")
        
        # Check if slot is fixed
        if slot.get('is_fixed'):
            raise HTTPException(400, "This slot is fixed and cannot be moved")
        
        # Check task is reschedulable
        task = db.execute_one("SELECT * FROM tasks WHERE id = ?", (slot['task_id'],))
        if not task['is_reschedulable'] and slot['source'] != 'manual':
            raise HTTPException(400, "This task cannot be rescheduled")
        
        print(f"Task is reschedulable: {task['is_reschedulable']}")
        
        # Calculate duration
        old_start = datetime.fromisoformat(slot['start_datetime'].replace('+00:00', '').replace('Z', ''))
        old_end = datetime.fromisoformat(slot['end_datetime'].replace('+00:00', '').replace('Z', ''))
        duration = old_end - old_start
        
        print(f"Duration calculated: {duration}")
        
        # Parse new_start (handle timezone)
        new_start = move_data.new_start
        if isinstance(new_start, str):
            new_start = datetime.fromisoformat(new_start.replace('+00:00', '').replace('Z', ''))
        
        new_end = new_start + duration
        
        print(f"Moving slot from {old_start} to {new_start}, duration={duration}")
        
        # Check for conflicts
        print(f"Checking for conflicts...")
        conflict = has_conflict(new_start, new_end, exclude_slot_id=slot_id)
        print(f"Conflict check result: {conflict}")
        
        if conflict['has_conflict']:
            # Get the first conflicting slot
            slot_conflicts = conflict.get('slot_conflicts', [])
            if slot_conflicts:
                conflicting_slot_id = slot_conflicts[0]['id']
                print(f"Conflict detected with slot {conflicting_slot_id}")
                
                # Get conflicting slot info
                conflicting_slot = db.execute_one("""
                    SELECT s.*, t.title as task_title
                    FROM scheduled_slots s
                    JOIN tasks t ON s.task_id = t.id
                    WHERE s.id = ?
                """, (conflicting_slot_id,))
                
                # Return conflict info to let frontend ask user what to do
                return {
                    "success": False,
                    "conflict": True,
                    "conflicting_slot": {
                        "id": conflicting_slot['id'],
                        "task_title": conflicting_slot['task_title'],
                        "start": conflicting_slot['start_datetime'],
                        "end": conflicting_slot['end_datetime'],
                        "is_fixed": bool(conflicting_slot.get('is_fixed', 0))
                    }
                }
            else:
                # Conflict with blocked time
                print(f"Conflict with blocked time")
                return {
                    "success": False,
                    "conflict": True,
                    "conflict_type": "blocked_time"
                }
        
        # No conflict - move the slot
        print(f"No conflict, updating slot")
        db.update('scheduled_slots', {
            'start_datetime': new_start.isoformat(),
            'end_datetime': new_end.isoformat(),
            'is_override': 1,
            'original_start': slot.get('original_start') or slot['start_datetime'],
            'source': 'manual'
        }, 'id = ?', (slot_id,))
        
        print(f"Slot {slot_id} moved successfully")
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in move_slot: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Internal server error: {str(e)}")


@app.put("/slots/{slot_id}/move-with-swap")
def move_slot_with_swap(slot_id: int, swap_with_id: int, move_data: SlotMove):
    """Move a slot and swap with another slot"""
    print(f"move_slot_with_swap called: slot_id={slot_id}, swap_with_id={swap_with_id}")
    
    slot1 = db.execute_one("SELECT * FROM scheduled_slots WHERE id = ?", (slot_id,))
    slot2 = db.execute_one("SELECT * FROM scheduled_slots WHERE id = ?", (swap_with_id,))
    
    if not slot1 or not slot2:
        raise HTTPException(404, "Slot not found")
    
    # Check neither is fixed
    if slot1.get('is_fixed') or slot2.get('is_fixed'):
        raise HTTPException(400, "Cannot swap fixed slots")
    
    # Calculate durations (preserve them!)
    slot1_start = datetime.fromisoformat(slot1['start_datetime'].replace('+00:00', '').replace('Z', ''))
    slot1_end = datetime.fromisoformat(slot1['end_datetime'].replace('+00:00', '').replace('Z', ''))
    slot1_duration = slot1_end - slot1_start
    
    slot2_start = datetime.fromisoformat(slot2['start_datetime'].replace('+00:00', '').replace('Z', ''))
    slot2_end = datetime.fromisoformat(slot2['end_datetime'].replace('+00:00', '').replace('Z', ''))
    slot2_duration = slot2_end - slot2_start
    
    print(f"Slot 1 duration: {slot1_duration}, Slot 2 duration: {slot2_duration}")
    
    # Swap positions but preserve durations
    # Slot 1 moves to Slot 2's position (with its own duration)
    new_slot1_start = slot2_start
    new_slot1_end = slot2_start + slot1_duration
    
    # Slot 2 moves to Slot 1's position (with its own duration)
    new_slot2_start = slot1_start
    new_slot2_end = slot1_start + slot2_duration
    
    print(f"Swapping: Slot {slot_id} -> {new_slot1_start} to {new_slot1_end}")
    print(f"Swapping: Slot {swap_with_id} -> {new_slot2_start} to {new_slot2_end}")
    
    # Update both slots
    db.update('scheduled_slots', {
        'start_datetime': new_slot1_start.isoformat(),
        'end_datetime': new_slot1_end.isoformat(),
        'is_override': 1,
        'source': 'manual'
    }, 'id = ?', (slot_id,))
    
    db.update('scheduled_slots', {
        'start_datetime': new_slot2_start.isoformat(),
        'end_datetime': new_slot2_end.isoformat(),
        'is_override': 1,
        'source': 'manual'
    }, 'id = ?', (swap_with_id,))
    
    print(f"Swap completed successfully")
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
