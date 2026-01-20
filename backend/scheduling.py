"""
Scheduling algorithms - the brain of the task manager
"""
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from database import db
import json


# Constants
MAX_SESSION_HOURS = 4
WORK_SCHEDULES = {
    'weekdays': 'MO,TU,WE,TH,FR',
    'all_week': 'MO,TU,WE,TH,FR,SA,SU',
}


class SchedulingError(Exception):
    """Raised when scheduling fails"""
    pass


@dataclass
class BumpCandidate:
    """Represents a task slot that could be bumped for higher priority task"""
    slot_id: int
    task_id: int
    task_title: str
    priority: int
    deadline: date
    start_datetime: datetime
    end_datetime: datetime
    duration_hours: float


def get_calendar_settings():
    """Get calendar settings with parsed excluded dates"""
    settings = db.execute_one("SELECT * FROM calendar_settings WHERE id = 1")
    if settings:
        settings['excluded_dates'] = json.loads(settings.get('excluded_dates', '[]'))
    return settings


def get_work_days(calendar_settings):
    """Get list of work day codes (MO, TU, etc.)"""
    if calendar_settings['work_schedule'] == 'custom':
        return calendar_settings['custom_days'].split(',')
    return WORK_SCHEDULES.get(calendar_settings['work_schedule'], 'MO,TU,WE,TH,FR').split(',')


def has_conflict(start_datetime: datetime, end_datetime: datetime, 
                exclude_task_id: int = None, exclude_slot_id: int = None) -> Dict:
    """
    Check if time slot conflicts with existing slots or blocked times
    Returns dict with conflict info
    """
    # Check scheduled slots
    query = """
        SELECT s.id, t.title, s.start_datetime, s.end_datetime
        FROM scheduled_slots s
        JOIN tasks t ON s.task_id = t.id
        WHERE 1=1
    """
    params = []
    
    if exclude_slot_id:
        query += " AND s.id != ?"
        params.append(exclude_slot_id)
    
    if exclude_task_id:
        query += " AND t.id != ?"
        params.append(exclude_task_id)
    
    query += """
        AND s.completed = 0
        AND NOT (s.end_datetime <= ? OR s.start_datetime >= ?)
        AND (s.is_override = 0 OR (s.is_override = 1 AND s.start_datetime IS NOT NULL))
    """
    params.extend([start_datetime.isoformat(), end_datetime.isoformat()])
    
    slot_conflicts = db.execute(query, tuple(params))
    
    # Check blocked times
    block_conflicts = db.execute("""
        SELECT id, title, start_datetime, end_datetime
        FROM blocked_times
        WHERE NOT (end_datetime <= ? OR start_datetime >= ?)
    """, (start_datetime.isoformat(), end_datetime.isoformat()))
    
    if slot_conflicts or block_conflicts:
        return {
            "has_conflict": True,
            "slot_conflicts": slot_conflicts,
            "block_conflicts": block_conflicts
        }
    
    return {"has_conflict": False}


def get_available_time_in_slot(slot_start: datetime, slot_end: datetime, 
                               exclude_task_id: int = None) -> List[Tuple[datetime, datetime]]:
    """
    Given a time range, return all available sub-ranges accounting for conflicts
    Returns list of (start, end) tuples
    """
    # Get all conflicts in this range
    conflicts = []
    
    # Get scheduled slot conflicts
    slot_conflicts = db.execute("""
        SELECT start_datetime, end_datetime
        FROM scheduled_slots s
        JOIN tasks t ON s.task_id = t.id
        WHERE (t.id != ? OR ? IS NULL)
        AND s.completed = 0
        AND NOT (end_datetime <= ? OR start_datetime >= ?)
        AND (s.is_override = 0 OR (s.is_override = 1 AND s.start_datetime IS NOT NULL))
        ORDER BY start_datetime
    """, (exclude_task_id, exclude_task_id, slot_start.isoformat(), slot_end.isoformat()))
    
    # Get blocked time conflicts
    block_conflicts = db.execute("""
        SELECT start_datetime, end_datetime
        FROM blocked_times
        WHERE NOT (end_datetime <= ? OR start_datetime >= ?)
        ORDER BY start_datetime
    """, (slot_start.isoformat(), slot_end.isoformat()))
    
    # Combine and sort all conflicts
    all_conflicts = []
    for conflict in slot_conflicts + block_conflicts:
        all_conflicts.append((
            datetime.fromisoformat(conflict['start_datetime']),
            datetime.fromisoformat(conflict['end_datetime'])
        ))
    all_conflicts.sort(key=lambda x: x[0])
    
    # Find gaps between conflicts
    available = []
    current_start = slot_start
    
    for conflict_start, conflict_end in all_conflicts:
        if current_start < conflict_start:
            # There's a gap before this conflict
            available.append((current_start, conflict_start))
        current_start = max(current_start, conflict_end)
    
    # Check if there's time after the last conflict
    if current_start < slot_end:
        available.append((current_start, slot_end))
    
    return available


def generate_available_slots(start_date: date, end_date: date, 
                            calendar_settings: Dict) -> List[Tuple[datetime, datetime]]:
    """
    Generate all possible work slots based on calendar settings
    Returns list of (start_datetime, end_datetime) tuples
    """
    slots = []
    current_date = start_date
    
    work_days = get_work_days(calendar_settings)
    excluded_dates = calendar_settings.get('excluded_dates', [])
    
    work_start = datetime.strptime(calendar_settings['work_start_time'], "%H:%M").time()
    work_end = datetime.strptime(calendar_settings['work_end_time'], "%H:%M").time()
    
    while current_date <= end_date:
        # Check if it's a work day and not excluded
        day_code = current_date.strftime('%a').upper()[:2]  # MO, TU, etc.
        
        if day_code in work_days and current_date.isoformat() not in excluded_dates:
            slot_start = datetime.combine(current_date, work_start)
            slot_end = datetime.combine(current_date, work_end)
            slots.append((slot_start, slot_end))
        
        current_date += timedelta(days=1)
    
    return slots


def create_task_sessions(task: Dict, available_slots: List[Tuple[datetime, datetime]], 
                        min_session_hours: float = None) -> Tuple[List[Dict], float]:
    """
    Split task into sessions and fit them into available slots
    Returns (list of session dicts, remaining_hours)
    """
    if min_session_hours is None:
        min_session_hours = task.get('min_session_hours', 2.0)
    
    sessions = []
    remaining = task['estimated_hours']
    
    for slot_start, slot_end in available_slots:
        if remaining <= 0:
            break
        
        # Get available time within this slot (accounting for conflicts)
        available_ranges = get_available_time_in_slot(slot_start, slot_end, task['id'])
        
        for range_start, range_end in available_ranges:
            if remaining <= 0:
                break
            
            range_duration = (range_end - range_start).total_seconds() / 3600
            
            # Only use this range if it's at least min_session_hours
            if range_duration >= min_session_hours:
                session_duration = min(MAX_SESSION_HOURS, range_duration, remaining)
                session_end = range_start + timedelta(hours=session_duration)
                
                sessions.append({
                    'task_id': task['id'],
                    'start_datetime': range_start.isoformat(),
                    'end_datetime': session_end.isoformat(),
                    'source': 'auto',
                    'is_override': 0
                })
                
                remaining -= session_duration
    
    return sessions, remaining


def auto_schedule_task(task_id: int) -> Dict:
    """
    Auto-schedule a single task into available slots
    Returns dict with scheduling result
    """
    task = db.execute_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
    if not task:
        raise SchedulingError(f"Task {task_id} not found")
    
    if task['has_time_allocation']:
        raise SchedulingError("Task has recurring time allocation, cannot auto-schedule")
    
    calendar_settings = get_calendar_settings()
    
    # Generate available slots
    start_date = datetime.fromisoformat(task['start_date']).date() if task['start_date'] else date.today()
    end_date = datetime.fromisoformat(task['deadline']).date() if task['deadline'] else (date.today() + timedelta(days=365))
    
    available_slots = generate_available_slots(start_date, end_date, calendar_settings)
    
    # Create sessions
    sessions, remaining = create_task_sessions(task, available_slots)
    
    if sessions:
        # Insert sessions
        for session in sessions:
            db.insert('scheduled_slots', session)
    
    return {
        "task_id": task_id,
        "scheduled": remaining == 0,
        "hours_scheduled": task['estimated_hours'] - remaining,
        "hours_remaining": remaining,
        "session_count": len(sessions)
    }


def auto_schedule_all_tasks() -> Dict:
    """
    Auto-schedule all unscheduled, reschedulable tasks
    Returns summary of what was scheduled
    """
    # Get tasks that need scheduling
    tasks = db.execute("""
        SELECT t.* FROM tasks t
        WHERE t.has_time_allocation = 0
        AND t.is_reschedulable = 1
        AND t.status != 'completed'
        AND t.archived = 0
        AND NOT EXISTS (
            SELECT 1 FROM scheduled_slots s 
            WHERE s.task_id = t.id
        )
        ORDER BY t.deadline ASC, t.priority DESC
    """)
    
    scheduled = []
    partial = []
    failed = []
    
    for task in tasks:
        try:
            result = auto_schedule_task(task['id'])
            
            if result['scheduled']:
                scheduled.append({
                    'task_id': task['id'],
                    'title': task['title'],
                    'sessions': result['session_count']
                })
            else:
                partial.append({
                    'task_id': task['id'],
                    'title': task['title'],
                    'scheduled_hours': result['hours_scheduled'],
                    'remaining_hours': result['hours_remaining']
                })
        except SchedulingError as e:
            failed.append({
                'task_id': task['id'],
                'title': task['title'],
                'error': str(e)
            })
    
    return {
        "scheduled": scheduled,
        "partial": partial,
        "failed": failed,
        "summary": f"Scheduled {len(scheduled)}, Partial {len(partial)}, Failed {len(failed)}"
    }


def find_bumpable_slots(required_hours: float, new_priority: int, 
                       start_date: date, deadline: date) -> List[BumpCandidate]:
    """
    Find scheduled slots that could be bumped for a higher priority task
    Returns list sorted by bumpability (lowest priority first)
    """
    candidates = db.execute("""
        SELECT 
            s.id as slot_id,
            s.task_id,
            s.start_datetime,
            s.end_datetime,
            t.title as task_title,
            t.priority,
            t.deadline,
            CAST((julianday(s.end_datetime) - julianday(s.start_datetime)) * 24 AS REAL) as duration_hours
        FROM scheduled_slots s
        JOIN tasks t ON s.task_id = t.id
        WHERE t.priority < ?
        AND t.is_reschedulable = 1
        AND t.status != 'completed'
        AND DATE(s.start_datetime) >= ?
        AND DATE(s.start_datetime) <= ?
        AND (s.is_override = 0 OR (s.is_override = 1 AND s.start_datetime IS NOT NULL))
        ORDER BY 
            t.priority ASC,
            t.deadline DESC,
            s.start_datetime ASC
    """, (new_priority, start_date.isoformat(), deadline.isoformat()))
    
    result = []
    for c in candidates:
        result.append(BumpCandidate(
            slot_id=c['slot_id'],
            task_id=c['task_id'],
            task_title=c['task_title'],
            priority=c['priority'],
            deadline=datetime.fromisoformat(c['deadline']).date() if c['deadline'] else None,
            start_datetime=datetime.fromisoformat(c['start_datetime']),
            end_datetime=datetime.fromisoformat(c['end_datetime']),
            duration_hours=c['duration_hours']
        ))
    
    return result


def reschedule_with_flexible_sessions(task_id: int, remaining_hours: float, 
                                     min_session_hours: float) -> List[Dict]:
    """
    Reschedule a task with flexible session sizes
    Returns list of new sessions
    """
    task = db.execute_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
    if not task:
        raise SchedulingError(f"Task {task_id} not found")
    
    calendar_settings = get_calendar_settings()
    
    start_date = datetime.fromisoformat(task['start_date']).date() if task['start_date'] else date.today()
    end_date = datetime.fromisoformat(task['deadline']).date() if task['deadline'] else (date.today() + timedelta(days=365))
    
    available_slots = generate_available_slots(start_date, end_date, calendar_settings)
    
    # Create flexible sessions
    task_copy = dict(task)
    task_copy['estimated_hours'] = remaining_hours
    sessions, remaining = create_task_sessions(task_copy, available_slots, min_session_hours)
    
    if remaining > 0:
        raise SchedulingError(f"Could not reschedule task {task_id}. {remaining:.1f}h remaining.")
    
    # Insert sessions
    for session in sessions:
        db.insert('scheduled_slots', session)
    
    return sessions


def attempt_with_bumping(task_id: int) -> Dict:
    """
    Try to schedule a high-priority task by bumping lower-priority ones
    Returns dict with scheduling result and list of bumped tasks
    """
    task = db.execute_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
    if not task:
        raise SchedulingError(f"Task {task_id} not found")
    
    calendar_settings = get_calendar_settings()
    
    start_date = datetime.fromisoformat(task['start_date']).date() if task['start_date'] else date.today()
    end_date = datetime.fromisoformat(task['deadline']).date() if task['deadline'] else (date.today() + timedelta(days=365))
    
    # First try normal scheduling
    available_slots = generate_available_slots(start_date, end_date, calendar_settings)
    sessions, remaining = create_task_sessions(task, available_slots)
    
    if remaining == 0:
        # Fits without bumping
        for session in sessions:
            db.insert('scheduled_slots', session)
        return {
            "scheduled": True,
            "bumped_tasks": [],
            "method": "normal"
        }
    
    # Need to bump
    candidates = find_bumpable_slots(remaining, task['priority'], start_date, end_date)
    
    if not candidates:
        raise SchedulingError("No lower-priority tasks to bump")
    
    # Select slots to bump
    to_bump = []
    accumulated_hours = 0
    bumped_task_ids = set()
    
    for candidate in candidates:
        to_bump.append(candidate)
        accumulated_hours += candidate.duration_hours
        bumped_task_ids.add(candidate.task_id)
        
        if accumulated_hours >= remaining:
            break
    
    if accumulated_hours < remaining:
        raise SchedulingError(
            f"Even after bumping {len(to_bump)} slots, still short by {remaining - accumulated_hours:.1f}h"
        )
    
    # Remove bumped slots
    for candidate in to_bump:
        db.delete('scheduled_slots', 'id = ?', (candidate.slot_id,))
    
    # Now reschedule the high-priority task
    available_slots = generate_available_slots(start_date, end_date, calendar_settings)
    new_sessions, still_remaining = create_task_sessions(task, available_slots)
    
    if still_remaining > 0:
        raise SchedulingError("Failed to schedule after bumping (bug)")
    
    # Insert new sessions
    for session in new_sessions:
        db.insert('scheduled_slots', session)
    
    # Try to reschedule bumped tasks
    rescheduled = {}
    failures = []
    
    for bumped_task_id in bumped_task_ids:
        bumped_task = db.execute_one("SELECT * FROM tasks WHERE id = ?", (bumped_task_id,))
        
        # Calculate remaining hours
        existing = db.execute("""
            SELECT SUM(CAST((julianday(end_datetime) - julianday(start_datetime)) * 24 AS REAL)) as total
            FROM scheduled_slots
            WHERE task_id = ?
        """, (bumped_task_id,))
        
        already_scheduled = existing[0]['total'] or 0
        task_remaining = bumped_task['estimated_hours'] - already_scheduled
        
        if task_remaining <= 0:
            continue
        
        try:
            result = reschedule_with_flexible_sessions(
                bumped_task_id, 
                task_remaining,
                min_session_hours=bumped_task.get('min_session_hours', 2.0)
            )
            rescheduled[bumped_task_id] = len(result)
        except SchedulingError:
            failures.append(bumped_task_id)
    
    # Log bumping activity
    db.insert('activity_log', {
        'action': 'bump_tasks',
        'entity_type': 'task',
        'entity_id': task_id,
        'new_data': json.dumps({
            'bumped': list(bumped_task_ids),
            'rescheduled': list(rescheduled.keys()),
            'failed': failures
        })
    })
    
    return {
        "scheduled": True,
        "method": "with_bumping",
        "bumped_tasks": list(bumped_task_ids),
        "rescheduled": rescheduled,
        "failed_reschedules": failures
    }


def calculate_benefit_score(candidate: Dict) -> float:
    """Calculate how beneficial it is to move this task to available time"""
    score = 0.0
    
    # Priority contribution (0-50 points)
    score += candidate['priority'] * 10
    
    # Deadline urgency (0-30 points)
    if candidate.get('days_until_deadline') is not None:
        days = candidate['days_until_deadline']
        if days <= 1:
            score += 30
        elif days <= 3:
            score += 20
        elif days <= 7:
            score += 10
    
    # Prefer moving evening work to earlier
    if 'original_start' in candidate:
        original_hour = datetime.fromisoformat(candidate['original_start']).hour
        if original_hour >= 17:
            score += 10
    
    return score


def reallocate_to_available_time(available_start: datetime, available_end: datetime, 
                                 mode: str = 'interactive', max_suggestions: int = 5) -> Dict:
    """
    Find tasks that could be moved into newly available time
    """
    available_duration = (available_end - available_start).total_seconds() / 3600
    
    # Find future slots that could be moved here
    candidates = db.execute("""
        SELECT 
            s.id as slot_id,
            s.task_id,
            s.start_datetime as original_start,
            s.end_datetime as original_end,
            CAST((julianday(s.end_datetime) - julianday(s.start_datetime)) * 24 AS REAL) as duration_hours,
            t.title,
            t.priority,
            t.deadline,
            p.name as project_name,
            p.colour as project_colour,
            julianday(t.deadline) - julianday('now') as days_until_deadline
        FROM scheduled_slots s
        JOIN tasks t ON s.task_id = t.id
        LEFT JOIN projects p ON t.project_id = p.id
        WHERE s.start_datetime > ?
        AND t.is_reschedulable = 1
        AND t.status != 'completed'
        AND CAST((julianday(s.end_datetime) - julianday(s.start_datetime)) * 24 AS REAL) <= ?
        AND (s.is_override = 0 OR (s.is_override = 1 AND s.start_datetime IS NOT NULL))
        ORDER BY 
            t.priority DESC,
            days_until_deadline ASC,
            s.start_datetime ASC
        LIMIT ?
    """, (available_start.isoformat(), available_duration, max_suggestions * 2))
    
    # Check which fit without conflicts
    viable = []
    for candidate in candidates:
        new_end = available_start + timedelta(hours=candidate['duration_hours'])
        
        if new_end <= available_end:
            conflict = has_conflict(available_start, new_end, exclude_slot_id=candidate['slot_id'])
            if not conflict['has_conflict']:
                candidate['new_start'] = available_start.isoformat()
                candidate['new_end'] = new_end.isoformat()
                candidate['benefit_score'] = calculate_benefit_score(candidate)
                viable.append(candidate)
    
    # Sort by benefit
    viable.sort(key=lambda x: x['benefit_score'], reverse=True)
    viable = viable[:max_suggestions]
    
    if mode == 'auto' and viable:
        # Auto-move the best candidate
        best = viable[0]
        
        db.update('scheduled_slots', {
            'start_datetime': best['new_start'],
            'end_datetime': best['new_end'],
            'source': 'manual',
            'is_override': 1,
            'original_start': best['original_start']
        }, 'id = ?', (best['slot_id'],))
        
        db.insert('activity_log', {
            'action': 'reallocate_auto',
            'entity_type': 'slot',
            'entity_id': best['slot_id'],
            'old_data': json.dumps({'start': best['original_start']}),
            'new_data': json.dumps({'start': best['new_start']})
        })
        
        return {
            "mode": "auto",
            "moved": best,
            "message": f"Moved '{best['title']}' to available slot"
        }
    
    return {
        "mode": "interactive",
        "available_time": {
            "start": available_start.isoformat(),
            "end": available_end.isoformat(),
            "duration_hours": available_duration
        },
        "suggestions": viable
    }


def check_deadline_feasibility(task: Dict) -> Dict:
    """Check if task can fit before deadline"""
    calendar_settings = get_calendar_settings()
    
    start_date = datetime.fromisoformat(task['start_date']).date() if task['start_date'] else date.today()
    end_date = datetime.fromisoformat(task['deadline']).date() if task['deadline'] else (date.today() + timedelta(days=365))
    
    available_slots = generate_available_slots(start_date, end_date, calendar_settings)
    
    # Calculate total available hours
    total_available = 0
    for slot_start, slot_end in available_slots:
        ranges = get_available_time_in_slot(slot_start, slot_end, task.get('id'))
        for range_start, range_end in ranges:
            total_available += (range_end - range_start).total_seconds() / 3600
    
    feasible = total_available >= task['estimated_hours']
    
    return {
        "feasible": feasible,
        "required_hours": task['estimated_hours'],
        "available_hours": round(total_available, 2),
        "shortfall": max(0, task['estimated_hours'] - total_available)
    }
