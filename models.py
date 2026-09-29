from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


PRIORITIES = ["Low", "Medium", "High"]


@dataclass
class Task:
    title: str
    description: str = ""
    category: str = "General"
    priority: str = "Medium"
    due_date: str = ""
    completed: bool = False
    id: Optional[int] = None
    created_at: str = ""
    deleted: bool = False
    recurrence: str = "none"

    @classmethod
    def from_row(cls, row: tuple) -> "Task":
        return cls(
            id=row[0],
            title=row[1],
            description=row[2],
            category=row[3],
            priority=row[4],
            due_date=row[5],
            completed=bool(row[6]),
            created_at=row[7],
            deleted=bool(row[8]) if len(row) > 8 else False,
            recurrence=row[9] if len(row) > 9 else "none",
        )

    def to_insert_tuple(self) -> tuple:
        return (
            self.title,
            self.description,
            self.category,
            self.priority,
            self.due_date,
            int(self.completed),
            self.created_at,
        )


@dataclass
class SubTask:
    task_id: int
    title: str
    id: Optional[int] = None
    completed: bool = False
    position: int = 0
