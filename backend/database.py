"""
Database module - handles SQLite connection and operations
"""
import sqlite3
import json
from datetime import datetime, date
from typing import Any, Optional, List, Dict
from pathlib import Path


class Database:
    def __init__(self, db_path: str = "../data/tasks.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def get_connection(self):
        """Get SQLite connection with row factory for dict results"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Projects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                colour TEXT DEFAULT '#3B82F6'
            )
        """)
        
        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                notes TEXT,
                priority INTEGER CHECK(priority BETWEEN 1 AND 5) DEFAULT 3,
                status TEXT CHECK(status IN ('not_started', 'in_progress', 'completed')) DEFAULT 'not_started',
                start_date DATE,
                deadline DATE,
                estimated_hours REAL,
                min_session_hours REAL DEFAULT 2.0,
                is_reschedulable BOOLEAN DEFAULT 1,
                has_time_allocation BOOLEAN DEFAULT 0,
                completed_at TIMESTAMP,
                archived BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)
        
        # Time allocations (for recurring tasks)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_allocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                rrule TEXT NOT NULL,
                duration_hours REAL NOT NULL CHECK(duration_hours <= 4),
                time_of_day TIME,
                start_date DATE NOT NULL,
                end_date DATE,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)
        
        # Scheduled slots (actual calendar entries)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                start_datetime DATETIME NOT NULL,
                end_datetime DATETIME NOT NULL,
                source TEXT CHECK(source IN ('allocation', 'auto', 'manual')) DEFAULT 'auto',
                is_override BOOLEAN DEFAULT 0,
                original_start DATETIME,
                completed BOOLEAN DEFAULT 0,
                completed_at TIMESTAMP,
                actual_hours REAL,
                time_tracking_start TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)
        
        # Blocked times (meetings, lunch breaks, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blocked_times (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT DEFAULT 'Blocked',
                description TEXT,
                rrule TEXT,
                start_datetime DATETIME NOT NULL,
                end_datetime DATETIME NOT NULL,
                is_recurring BOOLEAN DEFAULT 0
            )
        """)
        
        # Calendar settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calendar_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                work_schedule TEXT DEFAULT 'weekdays',
                custom_days TEXT,
                work_start_time TIME DEFAULT '09:00',
                work_end_time TIME DEFAULT '17:00',
                excluded_dates TEXT DEFAULT '[]'
            )
        """)
        
        # Activity log for undo functionality
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action TEXT NOT NULL,
                entity_type TEXT,
                entity_id INTEGER,
                old_data TEXT,
                new_data TEXT,
                reversible BOOLEAN DEFAULT 1
            )
        """)
        
        # Email settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                enabled BOOLEAN DEFAULT 0,
                email_address TEXT,
                smtp_server TEXT DEFAULT 'smtp.gmail.com',
                smtp_port INTEGER DEFAULT 587,
                smtp_username TEXT,
                smtp_password TEXT,
                monday_digest BOOLEAN DEFAULT 1,
                daily_deadline_alert BOOLEAN DEFAULT 1,
                alert_hour INTEGER DEFAULT 8
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_slots_datetime ON scheduled_slots(start_datetime, end_datetime)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_blocked_times_datetime ON blocked_times(start_datetime, end_datetime)")
        
        # Insert default calendar settings if not exists
        cursor.execute("INSERT OR IGNORE INTO calendar_settings (id) VALUES (1)")
        cursor.execute("INSERT OR IGNORE INTO email_settings (id) VALUES (1)")
        
        conn.commit()
        conn.close()
    
    def execute(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results as list of dicts"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def execute_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Execute a SELECT query and return first result as dict"""
        results = self.execute(query, params)
        return results[0] if results else None
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """Insert a row and return the new row ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        cursor.execute(query, tuple(data.values()))
        row_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return row_id
    
    def update(self, table: str, data: Dict[str, Any], where: str, where_params: tuple = ()) -> int:
        """Update rows and return number of rows affected"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        
        cursor.execute(query, tuple(data.values()) + where_params)
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        return rows_affected
    
    def delete(self, table: str, where: str, where_params: tuple = ()) -> int:
        """Delete rows and return number of rows affected"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = f"DELETE FROM {table} WHERE {where}"
        cursor.execute(query, where_params)
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        return rows_affected


# Global database instance
db = Database()
