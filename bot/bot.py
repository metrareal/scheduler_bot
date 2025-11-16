# bot/bot.py
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import datetime
from dotenv import load_dotenv
import os

from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
API_URL = "http://127.0.0.1:5000"
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

user_states = {}
# user_states[user_id] = {"expecting": None|"date_for_add"|"text_for_add",
#                         "add_date": None,
#                         "menu_message": {"chat_id":..., "message_id":...}
#                        }

# ---------- UI helpers ----------
def format_show_date(iso_date):
    # ISO YYYY-MM-DD -> DD.MM.YYYY for display
    try:
        d = datetime.datetime.strptime(iso_date, "%Y-%m-%d").date()
        return d.strftime("%d.%m.%Y")
    except:
        return iso_date

def main_menu():
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("➕ Добавить задачу", callback_data="add"))
    kb.row(InlineKeyboardButton("📅 Задачи на сегодня", callback_data="today"),
           InlineKeyboardButton("📆 Другие дни", callback_data="other_days"))
    # kb.row(InlineKeyboardButton("✔ Отметить выполненной", callback_data="done"), 
    #        InlineKeyboardButton("❌ Удалить задачу", callback_data="delete"))
    kb.row(InlineKeyboardButton("📁 Архив", callback_data="archive"),
           InlineKeyboardButton("❔ Помощь", callback_data="help"))
    return kb

def add_menu_kb():
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("Сегодня", callback_data="add_today"))
    kb.row(InlineKeyboardButton("На другую дату", callback_data="add_other"))
    kb.row(InlineKeyboardButton("⬅ Назад", callback_data="back"))
    return kb

def back_kb():
    return InlineKeyboardMarkup().add(InlineKeyboardButton("⬅ Назад", callback_data="back"))

def tasks_list_kb(tasks):
    kb = InlineKeyboardMarkup()
    for t in tasks:
        status = "✔" if t.get("done") else " "
        display = f"{t['id']}. {format_show_date(t['date'])} — {t['text'][:30]} {status}"
        kb.add(InlineKeyboardButton(display, callback_data=f"task:{t['id']}"))
    kb.add(InlineKeyboardButton("⬅ Назад", callback_data="back"))
    return kb

def task_action_kb(task_id):
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("✔ Выполнить", callback_data=f"do:{task_id}"),
           InlineKeyboardButton("❌ Удалить", callback_data=f"del:{task_id}"))
    kb.row(InlineKeyboardButton("⬅ Назад", callback_data="back"))
    return kb

def dates_kb(dates):
    kb = InlineKeyboardMarkup()
    for iso in dates:
        kb.add(InlineKeyboardButton(format_show_date(iso), callback_data=f"date:{iso}"))
    kb.add(InlineKeyboardButton("⬅ Назад", callback_data="back"))
    return kb

# ---------- API helpers ----------
def api_get_tasks(user_id, date=None):
    try:
        params = {"user_id": user_id}
        if date:
            params["date"] = date  # date can be ISO or DD.MM.YYYY; API handles both
        r = requests.get(f"{API_URL}/tasks", params=params, timeout=5)
        return r.json().get("tasks", [])
    except:
        return None

def api_get_dates(user_id):
    try:
        r = requests.get(f"{API_URL}/dates", params={"user_id": user_id}, timeout=5)
        return r.json().get("dates", [])
    except:
        return None

def api_add_task(user_id, text, date):
    try:
        payload = {"user_id": user_id, "text": text, "date": date}  # date can be DD.MM.YYYY or ISO
        r = requests.post(f"{API_URL}/tasks", json=payload, timeout=5)
        return r.json()
    except:
        return None

def api_update_task(user_id, task_id, fields):
    try:
        payload = {"user_id": user_id}
        payload.update(fields)
        r = requests.put(f"{API_URL}/tasks/{task_id}", json=payload, timeout=5)
        return r.json()
    except:
        return None

def api_delete_task(user_id, task_id):
    try:
        r = requests.delete(f"{API_URL}/tasks/{task_id}", params={"user_id": user_id}, timeout=5)
        return r.json()
    except:
        return None

def api_get_archive(user_id):
    try:
        r = requests.get(f"{API_URL}/archive", params={"user_id": user_id}, timeout=5)
        return r.json().get("archive", [])
    except:
        return None

# ---------- Handlers ----------
@bot.message_handler(commands=["start"])
def start_cmd(message):
    user_id = message.from_user.id
    user_states.setdefault(user_id, {"expecting": None, "add_date": None, "menu_message": None})
    sent = bot.send_message(message.chat.id, "👋 <b>Планировщик дня</b>\nВыберите действие:", reply_markup=main_menu())
    user_states[user_id]["menu_message"] = {"chat_id": sent.chat.id, "message_id": sent.message_id}

@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    user_id = call.from_user.id
    st = user_states.setdefault(user_id, {"expecting": None, "add_date": None, "menu_message": None})
    bot.answer_callback_query(call.id)
    data = call.data
    mm = st.get("menu_message") or {"chat_id": call.message.chat.id, "message_id": call.message.message_id}

    if data == "back":
        bot.edit_message_text("👋 <b>Планировщик дня</b>\nВыберите действие:", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=main_menu())
        st["expecting"] = None
        st["add_date"] = None
        return

    if data == "help":
        bot.edit_message_text("Кнопки: добавлять, смотреть на сегодня, другие дни, архив, пометить выполненной, удалить.\nВвод даты/текста — через обычное сообщение, когда бот попросит.", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=back_kb())
        return

    if data == "add":
        bot.edit_message_text("<b>Добавление задачи</b>\nВыберите дату:", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=add_menu_kb())
        return

    if data == "add_today":
        today_iso = datetime.date.today().isoformat()
        st["expecting"] = "text_for_add"
        st["add_date"] = today_iso
        bot.edit_message_text(f"<b>Добавление задачи на {format_show_date(today_iso)}</b>\n\nОтправьте текст задачи (обычное сообщение):", chat_id=mm["chat_id"], message_id=mm["message_id"])
        return

    if data == "add_other":
        st["expecting"] = "date_for_add"
        bot.edit_message_text("<b>Добавление задачи</b>\n\nОтправьте дату в формате DD.MM.YYYY:", chat_id=mm["chat_id"], message_id=mm["message_id"])
        return

    if data == "today":
        today_iso = datetime.date.today().isoformat()
        tasks = api_get_tasks(user_id, date=today_iso)
        if tasks is None:
            bot.edit_message_text("Ошибка при обращении к API.", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=back_kb())
            return
        if not tasks:
            bot.edit_message_text(f"📅 <b>Задачи на {format_show_date(today_iso)}</b>\n\nСписок пуст.", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=back_kb())
            return
        bot.edit_message_text(f"📅 <b>Задачи на {format_show_date(today_iso)}</b>\n\nВыберите задачу:", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=tasks_list_kb(tasks))
        return

    if data == "other_days":
        dates = api_get_dates(user_id)
        if dates is None:
            bot.edit_message_text("Ошибка при обращении к API.", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=back_kb())
            return
        # убираем сегодняшнюю дату из списка, если есть
        today_iso = datetime.date.today().isoformat()
        dates = [d for d in dates if d != today_iso]
        if not dates:
            bot.edit_message_text("📆 <b>Другие дни</b>\n\nНет задач на другие дни.", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=back_kb())
            return
        bot.edit_message_text("📆 <b>Другие дни</b>\n\nВыберите дату:", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=dates_kb(dates))
        return

    if data.startswith("date:"):
        iso = data.split(":",1)[1]
        tasks = api_get_tasks(user_id, date=iso)
        if tasks is None:
            bot.edit_message_text("Ошибка при обращении к API.", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=back_kb())
            return
        bot.edit_message_text(f"📆 <b>Задачи на {format_show_date(iso)}</b>\n\nВыберите задачу:", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=tasks_list_kb(tasks))
        return

    if data == "archive":
        arch = api_get_archive(user_id)
        if arch is None:
            bot.edit_message_text("Ошибка при обращении к API.", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=back_kb())
            return
        if not arch:
            bot.edit_message_text("📁 <b>Архив</b>\n\nАрхив пуст.", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=back_kb())
            return
        # покажем архив кратко (список)
        text = "📁 <b>Архив (выполненные задачи)</b>:\n\n"
        for t in arch:
            text += f"{t['id']}. {format_show_date(t['date'])} — {t['text'][:40]} (выполнено {format_show_date(t.get('completed_at',''))})\n"
        bot.edit_message_text(text, chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=back_kb())
        return

    if data.startswith("task:"):
        try:
            tid = int(data.split(":",1)[1])
        except:
            return
        bot.edit_message_text(f"<b>Задача #{tid}</b>\nВыберите действие:", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=task_action_kb(tid))
        return

    if data.startswith("do:"):
        try:
            tid = int(data.split(":",1)[1])
        except:
            return
        res = api_update_task(user_id, tid, {"done": True})
        if res is None or ("status" not in res and "archived" not in res):
            bot.edit_message_text("Ошибка при обращении к API.", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=back_kb())
            return
        # после архивации вернёмся к списку всех задач (обновлённому)
        tasks = api_get_tasks(user_id)
        if tasks is None:
            bot.edit_message_text("✔ Задача помечена выполненной, но не удалось получить список.", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=back_kb())
            return
        if not tasks:
            bot.edit_message_text("✔ Задача помечена выполненной.\n\nСписок текущих задач пуст.", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=back_kb())
            return
        bot.edit_message_text("✔ Задача помечена выполненной.\n\n📋 <b>Текущие задачи</b>\n\nВыберите задачу:", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=tasks_list_kb(tasks))
        return

    if data.startswith("del:"):
        try:
            tid = int(data.split(":",1)[1])
        except:
            return
        res = api_delete_task(user_id, tid)
        if res is None or res.get("status") is None:
            bot.edit_message_text("Ошибка при обращении к API.", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=back_kb())
            return
        tasks = api_get_tasks(user_id)
        if tasks is None:
            bot.edit_message_text("Удалено, но не удалось получить список.", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=back_kb())
            return
        if not tasks:
            bot.edit_message_text("❌ Задача удалена.\n\nСписок теперь пуст.", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=back_kb())
            return
        bot.edit_message_text("❌ Задача удалена.\n\n📋 <b>Текущие задачи</b>\n\nВыберите задачу:", chat_id=mm["chat_id"], message_id=mm["message_id"], reply_markup=tasks_list_kb(tasks))
        return

@bot.message_handler(func=lambda m: True)
def plain_text_handler(message):
    user_id = message.from_user.id
    st = user_states.setdefault(user_id, {"expecting": None, "add_date": None, "menu_message": None})

    if st["expecting"] == "date_for_add":
        text = message.text.strip()
        # ожидаем DD.MM.YYYY
        try:
            d = datetime.datetime.strptime(text, "%d.%m.%Y").date()
            st["add_date"] = d.isoformat()
            st["expecting"] = "text_for_add"
            bot.send_message(message.chat.id, f"Дата принята: {format_show_date(st['add_date'])}\nТеперь отправьте текст задачи:")
        except ValueError:
            bot.reply_to(message, "Некорректный формат даты. Используйте DD.MM.YYYY. Попробуйте ещё раз.")
        return

    if st["expecting"] == "text_for_add":
        text = message.text.strip()
        date_iso = st.get("add_date") or datetime.date.today().isoformat()
        res = api_add_task(user_id, text, date_iso)
        if res is None:
            bot.send_message(message.chat.id, "Ошибка при отправке запроса к API.")
        elif res.get("status") == "ok":
            tid = res.get("task_id")
            bot.send_message(message.chat.id, f"✅ Задача добавлена (id={tid}) на {format_show_date(date_iso)}.")
        else:
            bot.send_message(message.chat.id, f"Не удалось добавить задачу: {res}")
        st["expecting"] = None
        st["add_date"] = None
        sent = bot.send_message(message.chat.id, "👋 <b>Планировщик дня</b>\nВыберите действие:", reply_markup=main_menu())
        st["menu_message"] = {"chat_id": sent.chat.id, "message_id": sent.message_id}
        return

    # если не ожидали ничего — покажем меню
    start_cmd(message)

if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
