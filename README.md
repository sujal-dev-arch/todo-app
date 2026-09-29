# Todo App

A modern, feature-rich desktop todo list application built with Python and Tkinter.

## Features

- Add, edit, delete, and complete tasks
- Task title, description, category, priority, and due date/time
- Search tasks by title or description
- Filter by: All, Active, Completed, Overdue, Priority, Category
- Sort by: Creation date, Due date, Priority, Alphabetical
- Visual indicators for overdue and high-priority tasks
- Task statistics (total, active, completed, overdue)
- SQLite persistent storage
- Confirmation before deleting tasks
- Input validation with helpful error messages

## Requirements

- Python 3.7+
- Tkinter (included with Python standard library)

No external packages required.

## Setup

1. Ensure Python 3.7+ is installed:
   ```bash
   python --version
   ```

2. Navigate to the project directory:
   ```bash
   cd todo_app
   ```

3. Run the application:
   ```bash
   python main.py
   ```

The SQLite database (`todo_app.db`) is created automatically on first run.

## Project Structure

| File | Purpose |
|------|---------|
| `main.py` | Entry point — creates the root window and starts the app |
| `models.py` | `Task` dataclass — defines the data structure and serialization |
| `database.py` | `Database` class — all SQLite CRUD operations |
| `utils.py` | Helper functions — date parsing, validation, formatting |
| `gui.py` | GUI classes — `TodoApp` (main window), `TaskDialog` (add/edit form) |
| `requirements.txt` | Dependencies (none beyond standard library) |
| `README.md` | This file |

## Architecture

```
main.py  →  gui.py  →  database.py  →  SQLite
              ↓                        ↑
           models.py  ←───────────────┘
              ↓
           utils.py
```

- **models.py** defines the `Task` dataclass with methods to convert to/from database rows.
- **database.py** encapsulates all SQL — the GUI never writes raw SQL.
- **utils.py** provides pure functions for validation, date parsing, and formatting.
- **gui.py** contains all Tkinter code — `TodoApp` manages the main window, `TaskDialog` handles add/edit forms.
- **main.py** is the minimal entry point that wires everything together.

## Usage

- **Add a task**: Click "+ Add Task", fill in the form, click "Save"
- **Edit a task**: Select a task, click "Edit" (or double-click the row)
- **Complete/uncomplete**: Select a task, click "Toggle Complete"
- **Delete a task**: Select a task, click "Delete", confirm
- **Search**: Type in the search box — results filter as you type
- **Filter**: Use sidebar buttons for status/priority, dropdown for category
- **Sort**: Use the sort dropdown in the toolbar
