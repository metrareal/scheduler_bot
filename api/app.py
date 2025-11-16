# api/app.py
from flask import Flask, request, jsonify
from storage import load_data, save_data, ensure_user, add_task, tasks_for_date, get_all_tasks, delete_task, archive_task, update_task_fields, get_user_obj, all_dates_with_tasks, get_archive, init_db
import datetime
import os

app = Flask(__name__)
init_db()

def parse_date_input(date_str):
    """
    Принимает даты в формате DD.MM.YYYY или YYYY-MM-DD — возвращает YYYY-MM-DD.
    """
    if not date_str:
        return None
    date_str = date_str.strip()
    # if already ISO
    try:
        d = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        return d.isoformat()
    except ValueError:
        pass
    # try DD.MM.YYYY
    try:
        d = datetime.datetime.strptime(date_str, "%d.%m.%Y").date()
        return d.isoformat()
    except ValueError:
        return None

@app.route("/tasks", methods=["GET"])
def get_tasks():
    data = load_data()
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    date_q = request.args.get("date", default=None)
    # allow date in DD.MM.YYYY or YYYY-MM-DD; server stores YYYY-MM-DD
    date_iso = None
    if date_q:
        date_iso = parse_date_input(date_q)
        if date_iso is None:
            return jsonify({"error": "invalid date format"}), 400

    user = get_user_obj(data, user_id)
    if not user:
        return jsonify({"tasks": []})

    if date_iso:
        tasks = tasks_for_date(user, date_iso)
    else:
        tasks = get_all_tasks(user)
    return jsonify({"tasks": tasks})

@app.route("/dates", methods=["GET"])
def get_dates():
    data = load_data()
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    user = get_user_obj(data, user_id)
    if not user:
        return jsonify({"dates": []})
    dates = all_dates_with_tasks(user)
    return jsonify({"dates": dates})

@app.route("/tasks", methods=["POST"])
def post_task():
    data = load_data()
    req = request.json or {}
    user_id = req.get("user_id")
    text = req.get("text")
    date_in = req.get("date")

    if not user_id or not text or not date_in:
        return jsonify({"error": "user_id, text and date are required"}), 400

    date_iso = parse_date_input(date_in)
    if not date_iso:
        return jsonify({"error": "invalid date format, use DD.MM.YYYY or YYYY-MM-DD"}), 400

    user = ensure_user(data, user_id)
    task = add_task(user, text, date_iso)
    save_data(data)
    return jsonify({"status": "ok", "task_id": task["id"]})

@app.route("/tasks/<int:task_id>", methods=["PUT"])
def put_task(task_id):
    data = load_data()
    req = request.json or {}
    user_id = req.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    user = get_user_obj(data, user_id)
    if not user:
        return jsonify({"error": "no user"}), 404

    # если в теле передан done=true => архивируем
    if "done" in req and req.get("done") in (True, "true", "True"):
        archived = archive_task(user, task_id)
        if not archived:
            return jsonify({"error": "task not found"}), 404
        save_data(data)
        return jsonify({"status": "archived", "task": archived})

    # иначе обновляем поля (text/date)
    fields = {}
    if "text" in req:
        fields["text"] = req["text"]
    if "date" in req:
        date_iso = parse_date_input(req["date"])
        if not date_iso:
            return jsonify({"error": "invalid date format"}), 400
        fields["date"] = date_iso

    updated = update_task_fields(user, task_id, fields)
    if not updated:
        return jsonify({"error": "task not found"}), 404
    save_data(data)
    return jsonify({"status": "updated", "task": updated})

@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def del_task(task_id):
    data = load_data()
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    user = get_user_obj(data, user_id)
    if not user:
        return jsonify({"error": "no user"}), 404
    ok = delete_task(user, task_id)
    if not ok:
        return jsonify({"error": "task not found"}), 404
    save_data(data)
    return jsonify({"status": "deleted"})

@app.route("/archive", methods=["GET"])
def get_user_archive():
    data = load_data()
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    user = get_user_obj(data, user_id)
    if not user:
        return jsonify({"archive": []})
    return jsonify({"archive": get_archive(user)})

# optional: 查看 весь файл (debug)
@app.route("/debug/json", methods=["GET"])
def debug_json():
    data = load_data()
    return jsonify(data)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
