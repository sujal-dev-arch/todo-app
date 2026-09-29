import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional

from models import Task, SubTask


DB_NAME = "todo_app.db"


class Database:
    def __init__(self, db_name: str = DB_NAME):
        self._conn = sqlite3.connect(db_name)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                category TEXT DEFAULT 'General',
                priority TEXT DEFAULT 'Medium',
                due_date TEXT DEFAULT '',
                completed INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                deleted INTEGER DEFAULT 0,
                recurrence TEXT DEFAULT 'none'
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subtasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                completed INTEGER DEFAULT 0,
                position INTEGER DEFAULT 0,
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                category TEXT DEFAULT 'General',
                priority TEXT DEFAULT 'Medium',
                recurrence TEXT DEFAULT 'none',
                created_at TEXT NOT NULL
            )
            """
        )
        cursor = self._conn.execute("PRAGMA table_info(tasks)")
        columns = [row[1] for row in cursor.fetchall()]
        if "deleted" not in columns:
            self._conn.execute("ALTER TABLE tasks ADD COLUMN deleted INTEGER DEFAULT 0")
        if "recurrence" not in columns:
            self._conn.execute("ALTER TABLE tasks ADD COLUMN recurrence TEXT DEFAULT 'none'")
        self._conn.commit()

    def get_all_tasks(self, include_deleted: bool = False) -> List[Task]:
        query = "SELECT * FROM tasks"
        if not include_deleted:
            query += " WHERE deleted = 0"
        query += " ORDER BY created_at DESC"
        cursor = self._conn.execute(query)
        return [Task.from_row(tuple(row)) for row in cursor.fetchall()]

    def get_task(self, task_id: int) -> Optional[Task]:
        cursor = self._conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        return Task.from_row(tuple(row)) if row else None

    def add_task(self, task: Task) -> int:
        task.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self._conn.execute(
            """
            INSERT INTO tasks (title, description, category, priority, due_date, completed, created_at, deleted, recurrence)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (*task.to_insert_tuple(), task.recurrence),
        )
        self._conn.commit()
        return cursor.lastrowid

    def update_task(self, task: Task) -> None:
        self._conn.execute(
            """
            UPDATE tasks
            SET title = ?, description = ?, category = ?, priority = ?, due_date = ?, completed = ?, recurrence = ?
            WHERE id = ?
            """,
            (
                task.title,
                task.description,
                task.category,
                task.priority,
                task.due_date,
                int(task.completed),
                task.recurrence,
                task.id,
            ),
        )
        self._conn.commit()

    def soft_delete_task(self, task_id: int) -> None:
        self._conn.execute("UPDATE tasks SET deleted = 1 WHERE id = ?", (task_id,))
        self._conn.commit()

    def restore_task(self, task_id: int) -> None:
        self._conn.execute("UPDATE tasks SET deleted = 0 WHERE id = ?", (task_id,))
        self._conn.commit()

    def permanent_delete_task(self, task_id: int) -> None:
        self._conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self._conn.commit()

    def get_trashed_tasks(self) -> List[Task]:
        cursor = self._conn.execute(
            "SELECT * FROM tasks WHERE deleted = 1 ORDER BY created_at DESC"
        )
        return [Task.from_row(tuple(row)) for row in cursor.fetchall()]

    def get_statistics(self) -> dict:
        total = self._conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE deleted = 0"
        ).fetchone()[0]
        active = self._conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE deleted = 0 AND completed = 0"
        ).fetchone()[0]
        completed = self._conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE deleted = 0 AND completed = 1"
        ).fetchone()[0]
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        overdue = self._conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE deleted = 0 AND completed = 0 AND due_date != '' AND due_date < ?",
            (now,),
        ).fetchone()[0]
        trashed = self._conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE deleted = 1"
        ).fetchone()[0]
        return {
            "total": total,
            "active": active,
            "completed": completed,
            "overdue": overdue,
            "trashed": trashed,
        }

    def get_categories(self) -> List[str]:
        cursor = self._conn.execute(
            "SELECT DISTINCT category FROM tasks WHERE deleted = 0 AND category != '' ORDER BY category"
        )
        return [row[0] for row in cursor.fetchall()]

    def mark_all_completed(self) -> int:
        cursor = self._conn.execute(
            "UPDATE tasks SET completed = 1 WHERE deleted = 0 AND completed = 0"
        )
        self._conn.commit()
        return cursor.rowcount

    def delete_all_completed(self) -> int:
        cursor = self._conn.execute(
            "UPDATE tasks SET deleted = 1 WHERE deleted = 0 AND completed = 1"
        )
        self._conn.commit()
        return cursor.rowcount

    def get_tasks_due_soon(self, minutes: int = 60) -> List[Task]:
        now = datetime.now()
        future = datetime.fromtimestamp(now.timestamp() + minutes * 60)
        now_str = now.strftime("%Y-%m-%d %H:%M")
        future_str = future.strftime("%Y-%m-%d %H:%M")
        cursor = self._conn.execute(
            """
            SELECT * FROM tasks
            WHERE deleted = 0 AND completed = 0
            AND due_date != '' AND due_date >= ? AND due_date <= ?
            ORDER BY due_date ASC
            """,
            (now_str, future_str),
        )
        return [Task.from_row(tuple(row)) for row in cursor.fetchall()]

    def create_recurring_instance(self, task_id: int) -> Optional[int]:
        task = self.get_task(task_id)
        if not task or task.recurrence == "none" or not task.due_date:
            return None
        try:
            due = datetime.strptime(task.due_date, "%Y-%m-%d %H:%M")
        except ValueError:
            return None
        if task.recurrence == "daily":
            due += timedelta(days=1)
        elif task.recurrence == "weekly":
            due += timedelta(weeks=1)
        elif task.recurrence == "monthly":
            month = due.month + 1
            year = due.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            day = min(due.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
            due = due.replace(year=year, month=month, day=day)
        else:
            return None
        new_task = Task(
            title=task.title,
            description=task.description,
            category=task.category,
            priority=task.priority,
            due_date=due.strftime("%Y-%m-%d %H:%M"),
            recurrence=task.recurrence,
        )
        return self.add_task(new_task)

    def get_subtasks(self, task_id: int) -> List[SubTask]:
        cursor = self._conn.execute(
            "SELECT * FROM subtasks WHERE task_id = ? ORDER BY position, id",
            (task_id,),
        )
        return [SubTask(
            id=row[0],
            task_id=row[1],
            title=row[2],
            completed=bool(row[3]),
            position=row[4],
        ) for row in cursor.fetchall()]

    def add_subtask(self, task_id: int, title: str) -> int:
        cursor = self._conn.execute(
            "SELECT COALESCE(MAX(position), 0) + 1 FROM subtasks WHERE task_id = ?",
            (task_id,),
        )
        position = cursor.fetchone()[0]
        cursor = self._conn.execute(
            "INSERT INTO subtasks (task_id, title, completed, position) VALUES (?, ?, 0, ?)",
            (task_id, title, position),
        )
        self._conn.commit()
        return cursor.lastrowid

    def update_subtask(self, subtask: SubTask) -> None:
        self._conn.execute(
            "UPDATE subtasks SET title = ?, completed = ?, position = ? WHERE id = ?",
            (subtask.title, int(subtask.completed), subtask.position, subtask.id),
        )
        self._conn.commit()

    def delete_subtask(self, subtask_id: int) -> None:
        self._conn.execute("DELETE FROM subtasks WHERE id = ?", (subtask_id,))
        self._conn.commit()

    def get_templates(self) -> List[dict]:
        cursor = self._conn.execute("SELECT * FROM templates ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]

    def add_template(self, name: str, title: str, description: str, category: str, priority: str, recurrence: str) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO templates (name, title, description, category, priority, recurrence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, title, description, category, priority, recurrence, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        self._conn.commit()
        return cursor.lastrowid

    def delete_template(self, template_id: int) -> None:
        self._conn.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
