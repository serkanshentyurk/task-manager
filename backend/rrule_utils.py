"""
Recurring pattern utilities using rrule (iCalendar format)
"""
from datetime import datetime, date, time, timedelta
from dateutil.rrule import rrulestr
from typing import List, Dict, Optional
from database import db
import json


class RecurrenceError(Exception):
    """Raised when recurrence operations fail"""
    pass


def validate_rrule(rrule_string: str) -> Dict:
    """
    Validate and parse rrule string
    Returns dict with validation result and example date
    """
    try:
        rule = rrulestr(rrule_string, dtstart=datetime.now())
        
        # Test it generates at least one occurrence
        occurrences = list(rule[:5])  # Get first 5
        if not occurrences:
            return {
                "valid": False,
                "error": "Rule doesn't generate any occurrences"
            }
        
        return {
            "valid": True,
            "example_dates": [occ.date().isoformat() for occ in occurrences[:3]],
            "count": len(occurrences)
        }
    except Exception as e:
        return {
            "valid": False,
            "error": f"Invalid recurrence rule: {str(e)}",
            "help": "Format should be like: FREQ=WEEKLY;BYDAY=MO,WE,FR"
        }


def generate_recurring_slots(time_allocation_id: int, from_date: Optional[date] = None) -> List[Dict]:
    """
    Generate scheduled slots from a time allocation pattern
    Respects existing overrides (manually edited instances)
    """
    allocation = db.execute_one(
        "SELECT * FROM time_allocations WHERE id = ?",
        (time_allocation_id,)
    )
    
    if not allocation:
        raise RecurrenceError(f"Time allocation {time_allocation_id} not found")
    
    if from_date is None:
        from_date = datetime.fromisoformat(allocation['start_date']).date()
    
    # Parse rrule
    try:
        rule = rrulestr(
            allocation['rrule'],
            dtstart=datetime.combine(from_date, time(0, 0))
        )
    except Exception as e:
        raise RecurrenceError(f"Invalid rrule: {str(e)}")
    
    # Get existing overrides for this task
    existing_overrides = db.execute("""
        SELECT original_start FROM scheduled_slots
        WHERE task_id = ? AND is_override = 1 AND original_start IS NOT NULL
    """, (allocation['task_id'],))
    
    override_dates = {
        datetime.fromisoformat(row['original_start'])
        for row in existing_overrides
    }
    
    # Determine end date
    if allocation['end_date']:
        end_date = datetime.fromisoformat(allocation['end_date']).date()
    else:
        # Generate for next year if no end date
        end_date = (datetime.now() + timedelta(days=365)).date()
    
    # Parse time of day
    time_of_day = datetime.strptime(allocation['time_of_day'], "%H:%M").time()
    
    # Generate occurrences
    generated = []
    for occurrence in rule:
        if occurrence.date() > end_date:
            break
        
        # Create datetime with specified time
        slot_start = datetime.combine(occurrence.date(), time_of_day)
        
        # Skip if this instance has been manually overridden
        if slot_start in override_dates:
            continue
        
        slot_end = slot_start + timedelta(hours=allocation['duration_hours'])
        
        # Check if already exists
        exists = db.execute_one("""
            SELECT id FROM scheduled_slots
            WHERE task_id = ?
            AND start_datetime = ?
            AND is_override = 0
        """, (allocation['task_id'], slot_start.isoformat()))
        
        if not exists:
            slot_data = {
                'task_id': allocation['task_id'],
                'start_datetime': slot_start.isoformat(),
                'end_datetime': slot_end.isoformat(),
                'source': 'allocation',
                'is_override': 0
            }
            
            slot_id = db.insert('scheduled_slots', slot_data)
            generated.append({**slot_data, 'id': slot_id})
    
    return generated


def edit_recurring_instance(slot_id: int, mode: str, 
                           new_rrule: str = None,
                           new_duration: float = None,
                           new_time: str = None) -> Dict:
    """
    Edit a recurring time allocation instance
    
    mode: 'this_only' or 'this_and_future'
    """
    slot = db.execute_one("SELECT * FROM scheduled_slots WHERE id = ?", (slot_id,))
    if not slot:
        raise RecurrenceError(f"Slot {slot_id} not found")
    
    if slot['source'] != 'allocation':
        raise RecurrenceError("Can only edit recurring allocation instances")
    
    # Get the time allocation
    allocation = db.execute_one("""
        SELECT * FROM time_allocations WHERE task_id = ?
    """, (slot['task_id'],))
    
    if not allocation:
        raise RecurrenceError("Time allocation not found")
    
    if mode == 'this_only':
        # Just override this single instance
        updates = {'is_override': 1, 'source': 'manual'}
        
        if not slot['original_start']:
            updates['original_start'] = slot['start_datetime']
        
        if new_duration:
            slot_start = datetime.fromisoformat(slot['start_datetime'])
            updates['end_datetime'] = (slot_start + timedelta(hours=new_duration)).isoformat()
        
        if new_time:
            slot_date = datetime.fromisoformat(slot['start_datetime']).date()
            new_start = datetime.combine(
                slot_date,
                datetime.strptime(new_time, "%H:%M").time()
            )
            duration = new_duration or allocation['duration_hours']
            updates['start_datetime'] = new_start.isoformat()
            updates['end_datetime'] = (new_start + timedelta(hours=duration)).isoformat()
        
        db.update('scheduled_slots', updates, 'id = ?', (slot_id,))
        
        return {
            "mode": "single_override",
            "slot_id": slot_id,
            "updates": updates
        }
    
    elif mode == 'this_and_future':
        # Split into old task (ends yesterday) + new task (starts today)
        original_task = db.execute_one("SELECT * FROM tasks WHERE id = ?", (slot['task_id'],))
        split_date = datetime.fromisoformat(slot['start_datetime']).date()
        
        # End the current time allocation
        db.update('time_allocations', {
            'end_date': (split_date - timedelta(days=1)).isoformat()
        }, 'id = ?', (allocation['id'],))
        
        # Delete future slots from old allocation
        db.delete('scheduled_slots', 
                 'task_id = ? AND start_datetime >= ? AND is_override = 0',
                 (slot['task_id'], slot['start_datetime']))
        
        # Create new task with new pattern
        new_task_data = {
            'project_id': original_task['project_id'],
            'title': original_task['title'],
            'description': original_task['description'],
            'notes': f"Split from task #{slot['task_id']} on {split_date}",
            'priority': original_task['priority'],
            'status': original_task['status'],
            'start_date': split_date.isoformat(),
            'deadline': original_task['deadline'],
            'estimated_hours': original_task['estimated_hours'],
            'min_session_hours': original_task['min_session_hours'],
            'is_reschedulable': original_task['is_reschedulable'],
            'has_time_allocation': 1,
            'archived': 0
        }
        
        new_task_id = db.insert('tasks', new_task_data)
        
        # Create new time allocation
        new_allocation_data = {
            'task_id': new_task_id,
            'rrule': new_rrule or allocation['rrule'],
            'duration_hours': new_duration or allocation['duration_hours'],
            'time_of_day': new_time or allocation['time_of_day'],
            'start_date': split_date.isoformat(),
            'end_date': allocation['end_date']
        }
        
        new_allocation_id = db.insert('time_allocations', new_allocation_data)
        
        # Generate new slots
        generated = generate_recurring_slots(new_allocation_id, from_date=split_date)
        
        # Log activity
        db.insert('activity_log', {
            'action': 'split_recurring_task',
            'entity_type': 'task',
            'entity_id': slot['task_id'],
            'new_data': json.dumps({
                'new_task_id': new_task_id,
                'split_date': split_date.isoformat(),
                'generated_slots': len(generated)
            })
        })
        
        return {
            "mode": "split_task",
            "original_task_id": slot['task_id'],
            "new_task_id": new_task_id,
            "new_allocation_id": new_allocation_id,
            "split_date": split_date.isoformat(),
            "generated_slots": len(generated)
        }
    
    else:
        raise RecurrenceError(f"Invalid mode: {mode}")


def delete_recurring_instance(slot_id: int) -> Dict:
    """
    Delete a single instance of a recurring pattern
    Marks as override so it doesn't regenerate
    """
    slot = db.execute_one("SELECT * FROM scheduled_slots WHERE id = ?", (slot_id,))
    if not slot:
        raise RecurrenceError(f"Slot {slot_id} not found")
    
    if slot['source'] == 'allocation':
        # Mark as deleted override
        db.update('scheduled_slots', {
            'is_override': 1,
            'start_datetime': None,
            'end_datetime': None,
            'original_start': slot['start_datetime']
        }, 'id = ?', (slot_id,))
        
        return {
            "deleted": False,
            "marked_as_override": True,
            "message": "Instance hidden, pattern continues"
        }
    else:
        # Actually delete non-recurring slots
        db.delete('scheduled_slots', 'id = ?', (slot_id,))
        return {
            "deleted": True,
            "message": "Slot deleted"
        }


def regenerate_all_recurring_slots(task_id: int) -> Dict:
    """
    Regenerate all recurring slots for a task
    Useful after changes to time allocation
    """
    allocations = db.execute("""
        SELECT id FROM time_allocations WHERE task_id = ?
    """, (task_id,))
    
    if not allocations:
        raise RecurrenceError(f"No time allocations found for task {task_id}")
    
    total_generated = 0
    for allocation in allocations:
        generated = generate_recurring_slots(allocation['id'])
        total_generated += len(generated)
    
    return {
        "task_id": task_id,
        "slots_generated": total_generated
    }
