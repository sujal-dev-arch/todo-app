import calendar
import csv
import json
import os
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import ttk, messagebox, filedialog
from typing import Optional

from database import Database
from models import Task, PRIORITIES
from utils import (
    parse_due_datetime,
    is_overdue,
    get_priority_color,
    format_display_date,
    validate_task_input,
)


DRAFT_FILE = "task_draft.json"


THEMES = {
    "light": {
        "sidebar_bg": "#2c3e50",
        "sidebar_btn": "#34495e",
        "sidebar_btn_active": "#4a6278",
        "sidebar_btn_selected": "#1abc9c",
        "sidebar_text": "white",
        "sidebar_header": "#1abc9c",
        "main_bg": "#ffffff",
        "main_text": "#000000",
    },
    "dark": {
        "sidebar_bg": "#1a1a2e",
        "sidebar_btn": "#16213e",
        "sidebar_btn_active": "#0f3460",
        "sidebar_btn_selected": "#e94560",
        "sidebar_text": "#eaeaea",
        "sidebar_header": "#e94560",
        "main_bg": "#16213e",
        "main_text": "#eaeaea",
    },
}


class DatePickerDialog(tk.Toplevel):
    def __init__(self, parent, title: str = "Select Date"):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result: Optional[str] = None
        self.current_year = datetime.now().year
        self.current_month = datetime.now().month

        self._create_widgets()
        self._update_calendar()

        self.bind("<Escape>", lambda e: self.destroy())

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self) -> None:
        frame = ttk.Frame(self, padding=10)
        frame.grid(row=0, column=0)

        nav_frame = ttk.Frame(frame)
        nav_frame.grid(row=0, column=0, columnspan=7, pady=(0, 5))

        ttk.Button(nav_frame, text="<", width=3, command=self._prev_month).pack(side="left")
        self.month_label = ttk.Label(nav_frame, text="", width=15, anchor="center")
        self.month_label.pack(side="left", padx=5)
        ttk.Button(nav_frame, text=">", width=3, command=self._next_month).pack(side="left")

        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, day in enumerate(days):
            ttk.Label(frame, text=day, width=4, anchor="center").grid(row=1, column=i, pady=2)

        self.day_buttons = []
        for row in range(6):
            for col in range(7):
                btn = tk.Button(frame, text="", width=4, command=lambda r=row, c=col: self._on_day_click(r, c))
                btn.grid(row=row + 2, column=col, padx=1, pady=1)
                self.day_buttons.append((row, col, btn))

        ttk.Button(frame, text="Today", command=self._on_today).grid(row=8, column=0, columnspan=3, pady=5)
        ttk.Button(frame, text="Clear", command=self._on_clear).grid(row=8, column=4, columnspan=3, pady=5)

    def _update_calendar(self) -> None:
        self.month_label.configure(text=datetime(self.current_year, self.current_month, 1).strftime("%B %Y"))
        cal = calendar.Calendar()
        month_days = cal.monthdayscalendar(self.current_year, self.current_month)

        for row, col, btn in self.day_buttons:
            btn.configure(text="", state="disabled", bg="SystemButtonFace")

        for week_idx, week in enumerate(month_days):
            for day_idx, day in enumerate(week):
                if day != 0:
                    for r, c, btn in self.day_buttons:
                        if r == week_idx and c == day_idx:
                            btn.configure(text=str(day), state="normal")
                            break

    def _prev_month(self) -> None:
        self.current_month -= 1
        if self.current_month < 1:
            self.current_month = 12
            self.current_year -= 1
        self._update_calendar()

    def _next_month(self) -> None:
        self.current_month += 1
        if self.current_month > 12:
            self.current_month = 1
            self.current_year += 1
        self._update_calendar()

    def _on_day_click(self, row: int, col: int) -> None:
        cal = calendar.Calendar()
        month_days = cal.monthdayscalendar(self.current_year, self.current_month)
        day = month_days[row][col]
        if day != 0:
            self.result = f"{self.current_year:04d}-{self.current_month:02d}-{day:02d}"
            self.destroy()

    def _on_today(self) -> None:
        today = datetime.now()
        self.result = today.strftime("%Y-%m-%d")
        self.destroy()

    def _on_clear(self) -> None:
        self.result = ""
        self.destroy()


class TaskDialog(tk.Toplevel):
    def __init__(self, parent, title: str, task: Optional[Task] = None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result: Optional[Task] = None
        self._task = task
        self._draft_key = f"draft_{'edit' if task else 'add'}"

        self._create_widgets()
        self._populate_if_editing()
        self._restore_draft()
        self._setup_draft_autosave()

        self.bind("<Return>", lambda e: self._on_submit())
        self.bind("<Escape>", lambda e: self.destroy())

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        self.title_entry.focus_set()

    def _create_widgets(self) -> None:
        frame = ttk.Frame(self, padding=15)
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text="Title *").grid(row=0, column=0, sticky="w", pady=2)
        self.title_entry = ttk.Entry(frame, width=40)
        self.title_entry.grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Description").grid(row=1, column=0, sticky="nw", pady=2)
        self.desc_text = tk.Text(frame, width=30, height=4, wrap="word")
        self.desc_text.grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Category").grid(row=2, column=0, sticky="w", pady=2)
        self.category_entry = ttk.Entry(frame, width=40)
        self.category_entry.grid(row=2, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Priority").grid(row=3, column=0, sticky="w", pady=2)
        self.priority_var = tk.StringVar(value="Medium")
        priority_combo = ttk.Combobox(
            frame, textvariable=self.priority_var, values=PRIORITIES, state="readonly", width=37
        )
        priority_combo.grid(row=3, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Due Date").grid(row=4, column=0, sticky="w", pady=2)
        date_frame = ttk.Frame(frame)
        date_frame.grid(row=4, column=1, sticky="ew", pady=2)

        self.date_entry = ttk.Entry(date_frame, width=12)
        self.date_entry.pack(side="left")
        ttk.Button(date_frame, text="...", width=3, command=self._on_date_picker).pack(side="left", padx=2)
        ttk.Label(date_frame, text=" (YYYY-MM-DD)").pack(side="left")

        ttk.Label(frame, text="Due Time").grid(row=5, column=0, sticky="w", pady=2)
        time_frame = ttk.Frame(frame)
        time_frame.grid(row=5, column=1, sticky="ew", pady=2)

        self.time_entry = ttk.Entry(time_frame, width=12)
        self.time_entry.pack(side="left")
        ttk.Label(time_frame, text=" (HH:MM, 24h)").pack(side="left")

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=15)

        ttk.Button(btn_frame, text="Save", command=self._on_submit).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        frame.columnconfigure(1, weight=1)

    def _on_date_picker(self) -> None:
        dialog = DatePickerDialog(self)
        self.wait_window(dialog)
        if dialog.result is not None:
            self.date_entry.delete(0, "end")
            self.date_entry.insert(0, dialog.result)

    def _populate_if_editing(self) -> None:
        if self._task:
            self.title_entry.insert(0, self._task.title)
            self.desc_text.insert("1.0", self._task.description)
            self.category_entry.insert(0, self._task.category)
            self.priority_var.set(self._task.priority)
            if self._task.due_date:
                parts = self._task.due_date.split(" ")
                self.date_entry.insert(0, parts[0])
                if len(parts) > 1:
                    self.time_entry.insert(0, parts[1])

    def _setup_draft_autosave(self) -> None:
        self.title_entry.bind("<KeyRelease>", lambda e: self._save_draft())
        self.desc_text.bind("<KeyRelease>", lambda e: self._save_draft())
        self.category_entry.bind("<KeyRelease>", lambda e: self._save_draft())
        self.date_entry.bind("<KeyRelease>", lambda e: self._save_draft())
        self.time_entry.bind("<KeyRelease>", lambda e: self._save_draft())

    def _save_draft(self) -> None:
        draft = {
            "title": self.title_entry.get(),
            "description": self.desc_text.get("1.0", "end-1c"),
            "category": self.category_entry.get(),
            "priority": self.priority_var.get(),
            "date": self.date_entry.get(),
            "time": self.time_entry.get(),
        }
        try:
            all_drafts = {}
            if os.path.exists(DRAFT_FILE):
                with open(DRAFT_FILE, "r") as f:
                    all_drafts = json.load(f)
            all_drafts[self._draft_key] = draft
            with open(DRAFT_FILE, "w") as f:
                json.dump(all_drafts, f)
        except Exception:
            pass

    def _restore_draft(self) -> None:
        if self._task:
            return
        try:
            if os.path.exists(DRAFT_FILE):
                with open(DRAFT_FILE, "r") as f:
                    all_drafts = json.load(f)
                draft = all_drafts.get(self._draft_key)
                if draft:
                    self.title_entry.insert(0, draft.get("title", ""))
                    self.desc_text.insert("1.0", draft.get("description", ""))
                    self.category_entry.insert(0, draft.get("category", ""))
                    self.priority_var.set(draft.get("priority", "Medium"))
                    self.date_entry.insert(0, draft.get("date", ""))
                    self.time_entry.insert(0, draft.get("time", ""))
        except Exception:
            pass

    def _clear_draft(self) -> None:
        try:
            if os.path.exists(DRAFT_FILE):
                with open(DRAFT_FILE, "r") as f:
                    all_drafts = json.load(f)
                all_drafts.pop(self._draft_key, None)
                with open(DRAFT_FILE, "w") as f:
                    json.dump(all_drafts, f)
        except Exception:
            pass

    def _on_submit(self) -> None:
        title = self.title_entry.get().strip()
        description = self.desc_text.get("1.0", "end-1c").strip()
        category = self.category_entry.get().strip() or "General"
        priority = self.priority_var.get()
        date_str = self.date_entry.get().strip()
        time_str = self.time_entry.get().strip()

        try:
            due_date = parse_due_datetime(date_str, time_str)
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e), parent=self)
            return

        error = validate_task_input(title, due_date)
        if error:
            messagebox.showerror("Invalid Input", error, parent=self)
            return

        task_id = self._task.id if self._task else None
        completed = self._task.completed if self._task else False
        created_at = self._task.created_at if self._task else ""

        self.result = Task(
            id=task_id,
            title=title,
            description=description,
            category=category,
            priority=priority,
            due_date=due_date,
            completed=completed,
            created_at=created_at,
        )
        self._clear_draft()
        self.destroy()


class TodoApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Todo App")
        self.root.geometry("900x600")
        self.root.minsize(700, 450)

        self.db = Database()
        self.current_filter = "All"
        self.current_priority_filter = "All"
        self.current_category_filter = "All"
        self.search_query = ""
        self.sort_by = "Created"
        self.sort_reverse = False
        self.column_sort = None
        self.current_theme = "light"

        self._setup_style()
        self._create_widgets()
        self._load_categories()
        self._bind_shortcuts()
        self.refresh()
        self._check_reminders()

    def _setup_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        self._apply_theme()

    def _apply_theme(self) -> None:
        theme = THEMES[self.current_theme]
        style = ttk.Style()

        style.configure("Sidebar.TFrame", background=theme["sidebar_bg"])
        style.configure(
            "Sidebar.TButton",
            background=theme["sidebar_btn"],
            foreground=theme["sidebar_text"],
            borderwidth=0,
            focusthickness=0,
            padding=8,
        )
        style.map(
            "Sidebar.TButton",
            background=[("active", theme["sidebar_btn_active"]), ("selected", theme["sidebar_btn_selected"])],
        )
        style.configure("Stats.TLabel", background=theme["sidebar_bg"], foreground=theme["sidebar_text"])
        style.configure("StatsHeader.TLabel", background=theme["sidebar_bg"], foreground=theme["sidebar_header"])

        self.root.configure(bg=theme["main_bg"])

    def _toggle_theme(self) -> None:
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self._apply_theme()

    def _create_widgets(self) -> None:
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        self._create_sidebar()
        self._create_main_area()

    def _create_sidebar(self) -> None:
        sidebar = ttk.Frame(self.root, style="Sidebar.TFrame", width=180)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        ttk.Label(sidebar, text="Todo App", style="StatsHeader.TLabel", font=("Helvetica", 14, "bold")).pack(
            fill="x", pady=15, padx=10
        )

        ttk.Label(sidebar, text="Filters", style="Stats.TLabel", font=("Helvetica", 10, "bold")).pack(
            fill="x", pady=(10, 2), padx=10
        )

        self.filter_buttons = {}
        for label in ["All", "Active", "Completed", "Overdue", "Trash"]:
            btn = ttk.Button(
                sidebar,
                text=label,
                style="Sidebar.TButton",
                command=lambda l=label: self._on_filter_changed(l),
            )
            btn.pack(fill="x", padx=5, pady=1)
            self.filter_buttons[label] = btn

        ttk.Label(sidebar, text="Priority", style="Stats.TLabel", font=("Helvetica", 10, "bold")).pack(
            fill="x", pady=(15, 2), padx=10
        )

        self.priority_filter_var = tk.StringVar(value="All")
        for label in ["All", "High", "Medium", "Low"]:
            btn = ttk.Button(
                sidebar,
                text=label,
                style="Sidebar.TButton",
                command=lambda l=label: self._on_priority_filter_changed(l),
            )
            btn.pack(fill="x", padx=5, pady=1)

        ttk.Label(sidebar, text="Category", style="Stats.TLabel", font=("Helvetica", 10, "bold")).pack(
            fill="x", pady=(15, 2), padx=10
        )

        self.category_var = tk.StringVar(value="All")
        self.category_combo = ttk.Combobox(
            sidebar, textvariable=self.category_var, state="readonly", values=["All"]
        )
        self.category_combo.pack(fill="x", padx=5, pady=2)
        self.category_combo.bind("<<ComboboxSelected>>", self._on_category_changed)

        ttk.Label(sidebar, text="Statistics", style="Stats.TLabel", font=("Helvetica", 10, "bold")).pack(
            fill="x", pady=(20, 2), padx=10
        )

        self.stats_labels = {}
        for key in ["Total", "Active", "Completed", "Overdue"]:
            lbl = ttk.Label(sidebar, text=f"{key}: 0", style="Stats.TLabel")
            lbl.pack(fill="x", pady=1, padx=10)
            self.stats_labels[key] = lbl

        ttk.Button(sidebar, text="Toggle Theme", style="Sidebar.TButton", command=self._toggle_theme).pack(
            fill="x", padx=5, pady=(20, 5)
        )

    def _create_main_area(self) -> None:
        main = ttk.Frame(self.root, padding=10)
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(2, weight=1)

        toolbar = ttk.Frame(main)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        toolbar.columnconfigure(0, weight=1)

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var)
        search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        search_entry.insert(0, "Search tasks...")
        search_entry.bind("<FocusIn>", lambda e: self._on_search_focus_in(search_entry))
        search_entry.bind("<FocusOut>", lambda e: self._on_search_focus_out(search_entry))

        self.sort_var = tk.StringVar(value="Created")
        sort_combo = ttk.Combobox(
            toolbar,
            textvariable=self.sort_var,
            state="readonly",
            values=["Created", "Due Date", "Priority", "Alphabetical"],
            width=15,
        )
        sort_combo.grid(row=0, column=1, padx=5)
        sort_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        ttk.Button(btn_frame, text="+ Add Task", command=self._on_add).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Edit", command=self._on_edit).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Toggle Complete", command=self._on_toggle_complete).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Save as Template", command=self._on_save_template).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Load Template", command=self._on_load_template).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Print View", command=self._on_print_view).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Duplicate", command=self._on_duplicate).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Delete", command=self._on_delete).pack(side="left", padx=2)

        sep = ttk.Separator(btn_frame, orient="vertical")
        sep.pack(side="left", fill="y", padx=5)

        ttk.Button(btn_frame, text="Mark All Done", command=self._on_mark_all_completed).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Clear Completed", command=self._on_clear_completed).pack(side="left", padx=2)

        sep2 = ttk.Separator(btn_frame, orient="vertical")
        sep2.pack(side="left", fill="y", padx=5)

        ttk.Button(btn_frame, text="Export CSV", command=self._on_export_csv).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Export JSON", command=self._on_export_json).pack(side="left", padx=2)

        tree_frame = ttk.Frame(main)
        tree_frame.grid(row=2, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        columns = ("id", "title", "category", "priority", "due_date", "status")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="ID", command=lambda: self._on_column_sort("id"))
        self.tree.heading("title", text="Title", command=lambda: self._on_column_sort("title"))
        self.tree.heading("category", text="Category", command=lambda: self._on_column_sort("category"))
        self.tree.heading("priority", text="Priority", command=lambda: self._on_column_sort("priority"))
        self.tree.heading("due_date", text="Due Date", command=lambda: self._on_column_sort("due_date"))
        self.tree.heading("status", text="Status", command=lambda: self._on_column_sort("status"))

        self.tree.column("id", width=40, anchor="center")
        self.tree.column("title", width=250)
        self.tree.column("category", width=100)
        self.tree.column("priority", width=80, anchor="center")
        self.tree.column("due_date", width=140)
        self.tree.column("status", width=80, anchor="center")

        self.tree.tag_configure("overdue", background="#ffcccc")
        self.tree.tag_configure("high_priority", background="#ffe6e6")
        self.tree.tag_configure("completed", foreground="#888888")
        self.tree.tag_configure("trashed", foreground="#aaaaaa")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<Double-1>", lambda e: self._on_edit())
        self.tree.bind("<Button-3>", self._on_right_click)

        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Edit", command=self._on_edit)
        self.context_menu.add_command(label="Duplicate", command=self._on_duplicate)
        self.context_menu.add_command(label="Toggle Complete", command=self._on_toggle_complete)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete", command=self._on_delete)

        self.search_var.trace_add("write", lambda *args: self._on_search_changed())

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-n>", lambda e: self._on_add())
        self.root.bind("<Delete>", lambda e: self._on_delete())
        self.root.bind("<Return>", lambda e: self._on_edit())
        self.root.bind("<space>", lambda e: self._on_toggle_complete())

    def _on_right_click(self, event) -> None:
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def _on_search_focus_in(self, entry: ttk.Entry) -> None:
        if entry.get() == "Search tasks...":
            entry.delete(0, "end")

    def _on_search_focus_out(self, entry: ttk.Entry) -> None:
        if not entry.get():
            entry.insert(0, "Search tasks...")

    def _on_search_changed(self) -> None:
        query = self.search_var.get()
        self.search_query = "" if query == "Search tasks..." else query
        self.refresh()

    def _on_filter_changed(self, filter_name: str) -> None:
        self.current_filter = filter_name
        self.refresh()

    def _on_priority_filter_changed(self, priority: str) -> None:
        self.current_priority_filter = priority
        self.refresh()

    def _on_category_changed(self, event=None) -> None:
        self.current_category_filter = self.category_var.get()
        self.refresh()

    def _on_column_sort(self, column: str) -> None:
        if self.column_sort == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.column_sort = column
            self.sort_reverse = False
        self.refresh()

    def _load_categories(self) -> None:
        categories = ["All"] + self.db.get_categories()
        self.category_combo["values"] = categories

    def _get_filtered_tasks(self) -> list:
        if self.current_filter == "Trash":
            tasks = self.db.get_trashed_tasks()
        else:
            tasks = self.db.get_all_tasks()

        if self.current_filter == "Active":
            tasks = [t for t in tasks if not t.completed]
        elif self.current_filter == "Completed":
            tasks = [t for t in tasks if t.completed]
        elif self.current_filter == "Overdue":
            tasks = [t for t in tasks if not t.completed and is_overdue(t.due_date)]

        if self.current_priority_filter != "All":
            tasks = [t for t in tasks if t.priority == self.current_priority_filter]

        if self.current_category_filter != "All":
            tasks = [t for t in tasks if t.category == self.current_category_filter]

        if self.search_query:
            q = self.search_query.lower()
            tasks = [
                t for t in tasks if q in t.title.lower() or q in t.description.lower()
            ]

        if self.column_sort:
            if self.column_sort == "title":
                tasks.sort(key=lambda t: t.title.lower(), reverse=self.sort_reverse)
            elif self.column_sort == "category":
                tasks.sort(key=lambda t: t.category.lower(), reverse=self.sort_reverse)
            elif self.column_sort == "priority":
                order = {"High": 0, "Medium": 1, "Low": 2}
                tasks.sort(key=lambda t: order.get(t.priority, 3), reverse=self.sort_reverse)
            elif self.column_sort == "due_date":
                tasks.sort(key=lambda t: t.due_date or "9999", reverse=self.sort_reverse)
            elif self.column_sort == "status":
                tasks.sort(key=lambda t: t.completed, reverse=self.sort_reverse)
            elif self.column_sort == "id":
                tasks.sort(key=lambda t: t.id or 0, reverse=self.sort_reverse)
        elif self.sort_by == "Due Date":
            tasks.sort(key=lambda t: t.due_date or "9999")
        elif self.sort_by == "Priority":
            order = {"High": 0, "Medium": 1, "Low": 2}
            tasks.sort(key=lambda t: order.get(t.priority, 3))
        elif self.sort_by == "Alphabetical":
            tasks.sort(key=lambda t: t.title.lower())
        else:
            tasks.sort(key=lambda t: t.created_at, reverse=True)

        return tasks

    def refresh(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        tasks = self._get_filtered_tasks()
        for task in tasks:
            tags = []
            if task.deleted:
                tags.append("trashed")
            elif task.completed:
                tags.append("completed")
            elif is_overdue(task.due_date):
                tags.append("overdue")
            if task.priority == "High" and not task.completed and not task.deleted:
                tags.append("high_priority")

            if task.deleted:
                status = "Trashed"
            elif task.completed:
                status = "Done"
            elif is_overdue(task.due_date):
                status = "Overdue"
            else:
                status = "Active"

            self.tree.insert(
                "",
                "end",
                values=(
                    task.id,
                    task.title,
                    task.category,
                    task.priority,
                    format_display_date(task.due_date),
                    status,
                ),
                tags=tags,
            )

        self._update_statistics()
        self._update_filter_badges()

    def _update_statistics(self) -> None:
        stats = self.db.get_statistics()
        for key, label in self.stats_labels.items():
            label.configure(text=f"{key}: {stats[key.lower()]}")

    def _update_filter_badges(self) -> None:
        stats = self.db.get_statistics()
        self.filter_buttons["All"].configure(text=f"All ({stats['total']})")
        self.filter_buttons["Active"].configure(text=f"Active ({stats['active']})")
        self.filter_buttons["Completed"].configure(text=f"Completed ({stats['completed']})")
        self.filter_buttons["Overdue"].configure(text=f"Overdue ({stats['overdue']})")
        self.filter_buttons["Trash"].configure(text=f"Trash ({stats['trashed']})")

    def _get_selected_task_id(self) -> Optional[int]:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a task first.")
            return None
        item = self.tree.item(selection[0])
        return item["values"][0]

    def _on_add(self) -> None:
        dialog = TaskDialog(self.root, "Add Task")
        self.root.wait_window(dialog)
        if dialog.result:
            try:
                self.db.add_task(dialog.result)
                self._load_categories()
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add task: {e}")

    def _on_edit(self) -> None:
        task_id = self._get_selected_task_id()
        if task_id is None:
            return
        task = self.db.get_task(task_id)
        if not task:
            messagebox.showerror("Error", "Task not found.")
            return

        dialog = TaskDialog(self.root, "Edit Task", task=task)
        self.root.wait_window(dialog)
        if dialog.result:
            try:
                self.db.update_task(dialog.result)
                self._load_categories()
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update task: {e}")

    def _on_duplicate(self) -> None:
        task_id = self._get_selected_task_id()
        if task_id is None:
            return
        task = self.db.get_task(task_id)
        if not task:
            return
        duplicated = Task(
            title=f"{task.title} (copy)",
            description=task.description,
            category=task.category,
            priority=task.priority,
            due_date=task.due_date,
        )
        try:
            self.db.add_task(duplicated)
            self._load_categories()
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to duplicate task: {e}")

    def _on_toggle_complete(self) -> None:
        task_id = self._get_selected_task_id()
        if task_id is None:
            return
        task = self.db.get_task(task_id)
        if not task:
            return
        task.completed = not task.completed
        try:
            self.db.update_task(task)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update task: {e}")

    def _on_delete(self) -> None:
        task_id = self._get_selected_task_id()
        if task_id is None:
            return
        task = self.db.get_task(task_id)
        if not task:
            return

        if task.deleted:
            if messagebox.askyesno("Confirm Permanent Delete", "Permanently delete this task? This cannot be undone."):
                try:
                    self.db.permanent_delete_task(task_id)
                    self.refresh()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete task: {e}")
        else:
            if messagebox.askyesno("Confirm Delete", "Move this task to trash?"):
                try:
                    self.db.soft_delete_task(task_id)
                    self.refresh()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete task: {e}")

    def _on_mark_all_completed(self) -> None:
        count = len([t for t in self.db.get_all_tasks() if not t.completed])
        if count == 0:
            messagebox.showinfo("Info", "No active tasks to complete.")
            return
        if messagebox.askyesno("Confirm", f"Mark all {count} active tasks as completed?"):
            try:
                self.db.mark_all_completed()
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update tasks: {e}")

    def _on_clear_completed(self) -> None:
        count = len([t for t in self.db.get_all_tasks() if t.completed])
        if count == 0:
            messagebox.showinfo("Info", "No completed tasks to clear.")
            return
        if messagebox.askyesno("Confirm", f"Move all {count} completed tasks to trash?"):
            try:
                self.db.delete_all_completed()
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear completed tasks: {e}")

    def _on_export_csv(self) -> None:
        tasks = self.db.get_all_tasks()
        if not tasks:
            messagebox.showinfo("Export", "No tasks to export.")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Export tasks as CSV",
        )
        if not filepath:
            return
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Title", "Description", "Category", "Priority", "Due Date", "Completed", "Created At"])
                for t in tasks:
                    writer.writerow([t.id, t.title, t.description, t.category, t.priority, t.due_date, t.completed, t.created_at])
            messagebox.showinfo("Export", f"Exported {len(tasks)} tasks to {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")

    def _on_export_json(self) -> None:
        tasks = self.db.get_all_tasks()
        if not tasks:
            messagebox.showinfo("Export", "No tasks to export.")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Export tasks as JSON",
        )
        if not filepath:
            return
        try:
            data = [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "category": t.category,
                    "priority": t.priority,
                    "due_date": t.due_date,
                    "completed": t.completed,
                    "created_at": t.created_at,
                }
                for t in tasks
            ]
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Export", f"Exported {len(tasks)} tasks to {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")

    def _on_save_template(self) -> None:
        task_id = self._get_selected_task_id()
        if task_id is None:
            return
        task = self.db.get_task(task_id)
        if not task:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Save as Template")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=15)
        frame.grid(row=0, column=0)

        ttk.Label(frame, text="Template Name:").grid(row=0, column=0, sticky="w", pady=5)
        name_entry = ttk.Entry(frame, width=30)
        name_entry.grid(row=0, column=1, pady=5)
        name_entry.focus_set()

        def do_save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Template name is required.", parent=dialog)
                return
            try:
                self.db.add_template(name, task.title, task.description, task.category, task.priority, task.recurrence)
                messagebox.showinfo("Success", f"Template '{name}' saved.")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save template: {e}")

        ttk.Button(frame, text="Save", command=do_save).grid(row=1, column=0, pady=10)
        ttk.Button(frame, text="Cancel", command=dialog.destroy).grid(row=1, column=1, pady=10)

    def _on_load_template(self) -> None:
        templates = self.db.get_templates()
        if not templates:
            messagebox.showinfo("Templates", "No templates found.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Load Template")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=15)
        frame.grid(row=0, column=0)

        ttk.Label(frame, text="Select Template:").grid(row=0, column=0, sticky="w", pady=5)

        template_names = [t["name"] for t in templates]
        template_var = tk.StringVar()
        template_combo = ttk.Combobox(frame, textvariable=template_var, values=template_names, state="readonly", width=30)
        template_combo.grid(row=0, column=1, pady=5)
        if template_names:
            template_combo.current(0)

        def do_load():
            selected_name = template_var.get()
            if not selected_name:
                return
            template = next((t for t in templates if t["name"] == selected_name), None)
            if not template:
                return
            new_task = Task(
                title=template["title"],
                description=template["description"],
                category=template["category"],
                priority=template["priority"],
                recurrence=template["recurrence"],
            )
            try:
                self.db.add_task(new_task)
                self._load_categories()
                self.refresh()
                messagebox.showinfo("Success", f"Task created from template '{selected_name}'.")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create task: {e}")

        def do_delete_template():
            selected_name = template_var.get()
            if not selected_name:
                return
            if messagebox.askyesno("Confirm", f"Delete template '{selected_name}'?"):
                template = next((t for t in templates if t["name"] == selected_name), None)
                if template:
                    try:
                        self.db.delete_template(template["id"])
                        messagebox.showinfo("Success", "Template deleted.")
                        dialog.destroy()
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to delete template: {e}")

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="Load", command=do_load).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete", command=do_delete_template).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="left", padx=5)

    def _on_print_view(self) -> None:
        tasks = self.db.get_all_tasks()
        if not tasks:
            messagebox.showinfo("Print", "No tasks to print.")
            return

        print_window = tk.Toplevel(self.root)
        print_window.title("Print View")
        print_window.geometry("600x500")

        text_widget = tk.Text(print_window, wrap="word", font=("Courier", 10))
        text_widget.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(print_window, command=text_widget.yview)
        scrollbar.pack(side="right", fill="y")
        text_widget.configure(yscrollcommand=scrollbar.set)

        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("TODO TASK REPORT")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report_lines.append("=" * 60)
        report_lines.append("")

        active_tasks = [t for t in tasks if not t.completed]
        completed_tasks = [t for t in tasks if t.completed]

        report_lines.append(f"ACTIVE TASKS ({len(active_tasks)})")
        report_lines.append("-" * 60)
        for t in active_tasks:
            status = "OVERDUE" if is_overdue(t.due_date) else "ACTIVE"
            report_lines.append(f"[{status}] {t.title}")
            if t.description:
                report_lines.append(f"  Description: {t.description}")
            report_lines.append(f"  Category: {t.category} | Priority: {t.priority}")
            report_lines.append(f"  Due: {format_display_date(t.due_date)}")
            report_lines.append("")

        report_lines.append("")
        report_lines.append(f"COMPLETED TASKS ({len(completed_tasks)})")
        report_lines.append("-" * 60)
        for t in completed_tasks:
            report_lines.append(f"[DONE] {t.title}")
            report_lines.append(f"  Category: {t.category} | Priority: {t.priority}")
            report_lines.append("")

        report_lines.append("=" * 60)
        report_lines.append(f"Total: {len(tasks)} | Active: {len(active_tasks)} | Completed: {len(completed_tasks)}")
        report_lines.append("=" * 60)

        text_widget.insert("1.0", "\n".join(report_lines))
        text_widget.configure(state="disabled")

        btn_frame = ttk.Frame(print_window)
        btn_frame.pack(fill="x", padx=10, pady=5)

        def save_report():
            filepath = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt")],
                title="Save Report",
            )
            if filepath:
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write("\n".join(report_lines))
                    messagebox.showinfo("Success", f"Report saved to {filepath}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save report: {e}")

        ttk.Button(btn_frame, text="Save as Text", command=save_report).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Close", command=print_window.destroy).pack(side="left", padx=5)

    def _check_reminders(self) -> None:
        try:
            due_soon = self.db.get_tasks_due_soon(minutes=60)
            if due_soon:
                task_list = "\n".join(f"  - {t.title} (due: {format_display_date(t.due_date)})" for t in due_soon)
                messagebox.showinfo("Reminders", f"Tasks due within the next hour:\n\n{task_list}")
        except Exception:
            pass
