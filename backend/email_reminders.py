"""
Email reminder system for deadlines and weekly digests
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date, timedelta
from typing import Dict, Optional
from database import db


class EmailError(Exception):
    """Raised when email operations fail"""
    pass


def get_email_settings() -> Optional[Dict]:
    """Get email settings from database"""
    settings = db.execute_one("SELECT * FROM email_settings WHERE id = 1")
    return settings


def send_email(to: str, subject: str, html: str, settings: Dict) -> bool:
    """
    Send an email via SMTP
    Returns True if successful, False otherwise
    """
    if not settings or not settings.get('enabled'):
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = settings['smtp_username']
        msg['To'] = to
        
        msg.attach(MIMEText(html, 'html'))
        
        server = smtplib.SMTP(settings['smtp_server'], settings['smtp_port'])
        server.starttls()
        server.login(settings['smtp_username'], settings['smtp_password'])
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def generate_monday_digest() -> str:
    """Generate HTML content for Monday morning digest"""
    week_end = date.today() + timedelta(days=7)
    
    deadlines = db.execute("""
        SELECT 
            t.id,
            t.title, 
            t.deadline, 
            t.priority, 
            t.status, 
            p.name as project_name,
            COUNT(s.id) as scheduled_sessions,
            SUM(CAST((julianday(s.end_datetime) - julianday(s.start_datetime)) * 24 AS REAL)) as scheduled_hours
        FROM tasks t
        LEFT JOIN projects p ON t.project_id = p.id
        LEFT JOIN scheduled_slots s ON t.id = s.task_id
            AND (s.is_override = 0 OR (s.is_override = 1 AND s.start_datetime IS NOT NULL))
        WHERE t.status != 'completed'
        AND t.deadline IS NOT NULL
        AND t.deadline <= ?
        AND t.deadline >= ?
        AND t.archived = 0
        GROUP BY t.id
        ORDER BY t.deadline ASC, t.priority DESC
    """, (week_end.isoformat(), date.today().isoformat()))
    
    if not deadlines:
        return None  # No email needed
    
    # Build HTML
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            h2 {{ color: #2563EB; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th {{ background-color: #EFF6FF; padding: 12px; text-align: left; border: 1px solid #BFDBFE; }}
            td {{ padding: 10px; border: 1px solid #E5E7EB; }}
            .priority-5 {{ color: #DC2626; font-weight: bold; }}
            .priority-4 {{ color: #EA580C; }}
            .priority-3 {{ color: #CA8A04; }}
            .today {{ background-color: #FEF2F2; }}
            .tomorrow {{ background-color: #FEF9C3; }}
        </style>
    </head>
    <body>
        <h2>📅 Week Ahead - {date.today().strftime('%d %B %Y')}</h2>
        <p>You have <strong>{len(deadlines)}</strong> tasks with deadlines this week:</p>
        <table>
            <tr>
                <th>Task</th>
                <th>Project</th>
                <th>Deadline</th>
                <th>Priority</th>
                <th>Scheduled</th>
                <th>Status</th>
            </tr>
    """
    
    for task in deadlines:
        deadline_date = datetime.fromisoformat(task['deadline']).date()
        days_left = (deadline_date - date.today()).days
        
        deadline_str = deadline_date.strftime('%a %d %b')
        row_class = ""
        
        if days_left == 0:
            deadline_str += " <strong>(TODAY)</strong>"
            row_class = "today"
        elif days_left == 1:
            deadline_str += " (tomorrow)"
            row_class = "tomorrow"
        
        priority_class = f"priority-{task['priority']}"
        priority_emoji = "🔴" * task['priority']
        
        scheduled_str = f"{task['scheduled_hours']:.1f}h" if task['scheduled_hours'] else "⚠️ Not scheduled"
        
        html += f"""
            <tr class="{row_class}">
                <td>{task['title']}</td>
                <td>{task['project_name'] or '-'}</td>
                <td>{deadline_str}</td>
                <td class="{priority_class}">{priority_emoji}</td>
                <td>{scheduled_str}</td>
                <td>{task['status'].replace('_', ' ').title()}</td>
            </tr>
        """
    
    html += """
        </table>
        <p style="margin-top: 20px; color: #6B7280;">Have a productive week! 🚀</p>
    </body>
    </html>
    """
    
    return html


def generate_daily_deadline_alert() -> str:
    """Generate HTML content for daily deadline alert"""
    today_deadlines = db.execute("""
        SELECT 
            t.id,
            t.title, 
            t.priority, 
            t.status, 
            t.estimated_hours,
            p.name as project_name,
            COUNT(s.id) as scheduled_sessions,
            SUM(CAST((julianday(s.end_datetime) - julianday(s.start_datetime)) * 24 AS REAL)) as scheduled_hours
        FROM tasks t
        LEFT JOIN projects p ON t.project_id = p.id
        LEFT JOIN scheduled_slots s ON t.id = s.task_id
            AND DATE(s.start_datetime) = DATE('now')
            AND (s.is_override = 0 OR (s.is_override = 1 AND s.start_datetime IS NOT NULL))
        WHERE t.deadline = DATE('now')
        AND t.status != 'completed'
        AND t.archived = 0
        GROUP BY t.id
        ORDER BY t.priority DESC
    """)
    
    if not today_deadlines:
        return None
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            h2 {{ color: #DC2626; }}
            ul {{ list-style-type: none; padding-left: 0; }}
            li {{ padding: 10px; margin: 5px 0; background-color: #FEF2F2; border-left: 4px solid #DC2626; }}
            .priority-5 {{ border-left-color: #DC2626; }}
            .priority-4 {{ border-left-color: #EA580C; }}
            .priority-3 {{ border-left-color: #CA8A04; }}
            .scheduled {{ color: #059669; }}
            .not-scheduled {{ color: #DC2626; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h2>⚠️ Deadlines Today - {date.today().strftime('%A, %d %B %Y')}</h2>
        <p>You have <strong>{len(today_deadlines)}</strong> tasks due today:</p>
        <ul>
    """
    
    for task in today_deadlines:
        priority_emoji = "🔴" * task['priority']
        priority_class = f"priority-{task['priority']}"
        
        # Check if task has time scheduled today
        scheduled_today = task['scheduled_hours'] or 0
        
        if scheduled_today > 0:
            schedule_info = f"<span class='scheduled'>✓ {scheduled_today:.1f}h scheduled today</span>"
        else:
            schedule_info = "<span class='not-scheduled'>⚠️ Not scheduled today</span>"
        
        html += f"""
            <li class="{priority_class}">
                <strong>{priority_emoji} {task['title']}</strong>
                <br>
                <small>Project: {task['project_name'] or 'None'} | Status: {task['status'].replace('_', ' ').title()}</small>
                <br>
                {schedule_info}
            </li>
        """
    
    html += """
        </ul>
        <p style="margin-top: 20px;">Good luck! You've got this! 💪</p>
    </body>
    </html>
    """
    
    return html


def send_monday_digest() -> Dict:
    """
    Send Monday morning digest email
    Returns dict with send status
    """
    settings = get_email_settings()
    
    if not settings or not settings['enabled'] or not settings['monday_digest']:
        return {"sent": False, "reason": "Disabled in settings"}
    
    html = generate_monday_digest()
    
    if not html:
        return {"sent": False, "reason": "No deadlines this week"}
    
    success = send_email(
        to=settings['email_address'],
        subject=f"📅 Week Ahead - Your Deadlines",
        html=html,
        settings=settings
    )
    
    return {
        "sent": success,
        "reason": "Email sent successfully" if success else "SMTP error"
    }


def send_daily_deadline_alert() -> Dict:
    """
    Send daily deadline alert email
    Returns dict with send status
    """
    settings = get_email_settings()
    
    if not settings or not settings['enabled'] or not settings['daily_deadline_alert']:
        return {"sent": False, "reason": "Disabled in settings"}
    
    html = generate_daily_deadline_alert()
    
    if not html:
        return {"sent": False, "reason": "No deadlines today"}
    
    success = send_email(
        to=settings['email_address'],
        subject=f"⚠️ Deadlines Today - {date.today().strftime('%d %B')}",
        html=html,
        settings=settings
    )
    
    return {
        "sent": success,
        "reason": "Email sent successfully" if success else "SMTP error"
    }


def test_email_connection(settings: Dict) -> Dict:
    """
    Test email connection with provided settings
    """
    try:
        server = smtplib.SMTP(settings['smtp_server'], settings['smtp_port'])
        server.starttls()
        server.login(settings['smtp_username'], settings['smtp_password'])
        server.quit()
        
        return {"success": True, "message": "Email connection successful"}
    except Exception as e:
        return {"success": False, "error": str(e)}
