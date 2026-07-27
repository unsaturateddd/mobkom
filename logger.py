# logger.py — Система логирования в файл

import os
import json
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def get_log_file(name="main"):
    date = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(LOG_DIR, f"{name}_{date}.log")


def log_event(category, action, details="", user_id=None, phone_id=None):
    """
    Запись события в лог файл

    Категории: bot, ws, signal, purchase, admin, error
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file = get_log_file(category)

    entry = {
        "time": timestamp,
        "category": category,
        "action": action,
        "details": details,
        "user_id": user_id,
        "phone_id": phone_id
    }

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Также в консоль с эмодзи
    emoji = {
        "bot": "🤖",
        "ws": "🔌",
        "signal": "📡",
        "purchase": "🎯",
        "admin": "🛡",
        "error": "❌",
        "info": "ℹ️"
    }.get(category, "📝")

    print(f"  {emoji} [{timestamp}] {action}: {details[:80]}")


def log_bot(action, details="", user_id=None):
    log_event("bot", action, details, user_id=user_id)


def log_ws(action, details="", phone_id=None):
    log_event("ws", action, details, phone_id=phone_id)


def log_signal(action, details=""):
    log_event("signal", action, details)


def log_purchase(action, details="", user_id=None):
    log_event("purchase", action, details, user_id=user_id)


def log_admin(action, details="", user_id=None):
    log_event("admin", action, details, user_id=user_id)


def log_error(action, details=""):
    log_event("error", action, details)


def get_logs(category=None, limit=50):
    """Чтение логов"""
    logs = []
    date = datetime.now().strftime("%Y-%m-%d")

    if category:
        files = [get_log_file(category)]
    else:
        files = [get_log_file(f) for f in ["bot", "ws", "signal", "purchase", "admin", "error"]]

    for log_file in files:
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        logs.append(entry)
                    except:
                        pass

    # Сортировка по времени
    logs.sort(key=lambda x: x.get("time", ""), reverse=True)
    return logs[:limit]


def get_log_stats():
    """Статистика логов"""
    stats = {}
    date = datetime.now().strftime("%Y-%m-%d")

    for category in ["bot", "ws", "signal", "purchase", "admin", "error"]:
        log_file = get_log_file(category)
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                stats[category] = sum(1 for _ in f)
        else:
            stats[category] = 0

    return stats
