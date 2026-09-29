from datetime import datetime
from typing import Optional


def parse_due_datetime(date_str: str, time_str: str) -> str:
    if not date_str:
        return ""
    if not time_str:
        time_str = "23:59"
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        raise ValueError("Invalid date or time format. Use YYYY-MM-DD and HH:MM.")


def is_overdue(due_date: str) -> bool:
    if not due_date:
        return False
    try:
        due = datetime.strptime(due_date, "%Y-%m-%d %H:%M")
        return due < datetime.now()
    except ValueError:
        return False


def get_priority_color(priority: str) -> str:
    return {"High": "#ffcccc", "Medium": "#fff3cd", "Low": "#d4edda"}.get(
        priority, "#ffffff"
    )


def format_display_date(due_date: str) -> str:
    if not due_date:
        return "No due date"
    try:
        dt = datetime.strptime(due_date, "%Y-%m-%d %H:%M")
        return dt.strftime("%b %d, %Y %H:%M")
    except ValueError:
        return due_date


def validate_task_input(title: str, due_date: str) -> Optional[str]:
    if not title.strip():
        return "Title is required."
    if due_date:
        try:
            datetime.strptime(due_date, "%Y-%m-%d %H:%M")
        except ValueError:
            return "Due date must be in YYYY-MM-DD HH:MM format."
    return None
