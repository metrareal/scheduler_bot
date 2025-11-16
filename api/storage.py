# api/storage.py
import json
import os
import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data.json")

def init_db():
    if not os.path.exists(DB_PATH):
        data = {"users": []}
        save_data(data)

def load_data():
    init_db()
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user_obj(data, user_id):
    for u in data["users"]:
        if u.get("user_id") == user_id:
            return u
    return None

def ensure_user(data, user_id):
    user = get_user_obj(data, user_id)
    if user is None:
        user = {"user_id": user_id, "tasks": [], "archive": []}
        data["users"].append(user)
    # ensure keys exist
    if "tasks" not in user:
        user["tasks"] = []
    if "archive" not in user:
        user["archive"] = []
    return user

def next_task_id(user):
    if not user["tasks"] and not user["archive"]:
        return 1
    max_id = 0
    for t in user.get("tasks", []) + user.get("archive", []):
        if t.get("id", 0) > max_id:
            max_id = t["id"]
    return max_id + 1

def add_task(user, text, date_iso):
    tid = next_task_id(user)
    task = {
        "id": tid,
        "text": text,
        "date": date_iso,   # YYYY-MM-DD
        "done": False,
        "created_at": datetime.date.today().isoformat()
    }
    user["tasks"].append(task)
    return task

def find_task(user, task_id):
    for t in user.get("tasks", []):
        if t.get("id") == task_id:
            return t
    return None

def delete_task(user, task_id):
    t = find_task(user, task_id)
    if t:
        user["tasks"].remove(t)
        return True
    return False

def archive_task(user, task_id):
    """
    Помечаем задачу выполненной и перемещаем в archive со штампом completed_at.
    """
    t = find_task(user, task_id)
    if not t:
        return None
    t["done"] = True
    t["completed_at"] = datetime.date.today().isoformat()  # YYYY-MM-DD
    # переносим в archive
    user["tasks"].remove(t)
    user["archive"].append(t)
    return t

def update_task_fields(user, task_id, fields: dict):
    t = find_task(user, task_id)
    if not t:
        return None
    # обновляем только разрешённые поля
    for k in ("text", "date", "done"):
        if k in fields:
            t[k] = fields[k]
    return t

def tasks_for_date(user, date_iso):
    return [t for t in user.get("tasks", []) if t.get("date") == date_iso]

def all_dates_with_tasks(user):
    # возвращаем уникальные даты задач, отсортированные (YYYY-MM-DD)
    dates = sorted({t.get("date") for t in user.get("tasks", [])})
    return dates

def get_all_tasks(user):
    return user.get("tasks", [])

def get_archive(user):
    return user.get("archive", [])