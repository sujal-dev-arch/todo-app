# Todo App

An advanced desktop Todo List application built with **Python** and **Tkinter**. Manage tasks with priorities, categories, due dates, soft-delete trash, templates, subtasks support in the database layer, light/dark themes, search, sorting, CSV/JSON export, and keyboard shortcuts — all stored locally in SQLite.

## Features

- **Task management** — Create, edit, duplicate, and delete tasks
- **Priorities** — Low / Medium / High with visual highlighting
- **Categories** — Organize tasks; filter by category
- **Due dates & times** — Calendar date picker + optional time (24h)
- **Filters** — All, Active, Completed, Overdue, Trash
- **Search** — Live search across title and description
- **Sorting** — By created date, due date, priority, or alphabetical; click column headers to sort
- **Soft delete / Trash** — Deleted tasks go to Trash; restore or permanently delete
- **Templates** — Save a task as a template and load it later
- **Statistics** — Total, Active, Completed, Overdue counts in the sidebar
- **Themes** — Light and dark mode toggle
- **Export** — CSV and JSON
- **Bulk actions** — Mark all done, clear completed
- **Keyboard shortcuts**
  - `Ctrl+N` — Add task
  - `Enter` / double-click — Edit selected
  - `Space` — Toggle complete
  - `Delete` — Delete selected
- **Draft autosave** — Unsaved add-task form content is restored if the dialog is closed
- **Reminders** — Checks for tasks due soon on startup
- **Print view** — Simple printable summary of tasks

## Tech stack

| Component   | Technology                          |
|------------|--------------------------------------|
| UI         | Tkinter + ttk                        |
| Database   | SQLite (`todo_app.db`)               |
| Language   | Python 3 (standard library only)     |

No external packages are required. Tkinter ships with Python.

## Project Structure

```text
todo-app/
├── main.py          # Entry point
├── gui.py           # Main window, dialogs, themes, filters, export
├── database.py      # SQLite layer (tasks, subtasks, templates, stats)
├── models.py        # Task and SubTask dataclasses
├── utils.py         # Date parsing, validation, helpers
├── requirements.txt # Placeholder (no third-party dependencies)
└── README.md        # Project documentation
```

## Requirements

- Python 3.8+
- Tkinter (included with most Python installations)

On Linux you may need:

```bash
# Debian/Ubuntu
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter
```
# Installation & run
git clone https://github.com/sujal-dev-arch/todo-app.git
cd todo-app
python main.py


The SQLite database (todo_app.db) is created automatically in the working directory on first run.

# Usage

1. **Add a Task**
   Click **+ Add Task** or press `Ctrl+N`. Fill in the following details:

   * Title *(required)*
   * Description
   * Category
   * Priority
   * Due date/time

2. **Edit a Task**
   Select a task and:

   * Click **Edit**
   * Press `Enter`
   * Double-click the task

3. **Complete a Task**
   Select a task and click **Toggle Complete** or press `Space`.

4. **Filter Tasks**
   Use the sidebar to filter tasks by:

   * All
   * Active
   * Completed
   * Overdue
   * Trash

   You can also filter by **priority** and **category**.

5. **Search Tasks**
   Type in the search box at the top to quickly find tasks.

6. **Templates**
   Select a task and click **Save as Template**.
   Use **Load Template** to create a new task from a saved template.

7. **Trash**
   Deleted tasks appear under **Trash**. From there, you can:

   * Restore tasks
   * Permanently remove tasks

8. **Export**
   Use **Export CSV** or **Export JSON** to save the current filtered task list.

9. **Theme**
   Click **Toggle Theme** in the sidebar to switch between **dark mode** and **light mode**.
