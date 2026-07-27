import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            role TEXT DEFAULT 'trader',
            username TEXT DEFAULT '',
            name TEXT DEFAULT '',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS phones (
            phone_id TEXT PRIMARY KEY,
            imei TEXT UNIQUE NOT NULL,
            model TEXT DEFAULT '',
            trader_id INTEGER DEFAULT NULL,
            status TEXT DEFAULT 'offline',
            battery INTEGER DEFAULT 0,
            last_seen TIMESTAMP DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS trader_settings (
            trader_id INTEGER PRIMARY KEY,
            receive_signals INTEGER DEFAULT 0,
            distribute_signals INTEGER DEFAULT 0,
            auto_buy_enabled INTEGER DEFAULT 0,
            card TEXT DEFAULT '',
            amount INTEGER DEFAULT 0,
            cooldown INTEGER DEFAULT 30,
            sending INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trader_id INTEGER,
            card TEXT,
            amount INTEGER,
            dirty_card TEXT DEFAULT '',
            retries INTEGER DEFAULT 1,
            enabled INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (trader_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS qr_tokens (
            token TEXT PRIMARY KEY,
            trader_id INTEGER,
            used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (trader_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_id TEXT,
            body TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trader_id INTEGER,
            purchase_id INTEGER,
            phone_id TEXT,
            card TEXT,
            amount INTEGER,
            status TEXT DEFAULT 'pending',
            response TEXT DEFAULT '',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT NULL,
            action TEXT,
            details TEXT DEFAULT '',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Add missing columns for existing databases
    try:
        conn.execute("SELECT card FROM trader_settings LIMIT 1")
    except:
        conn.execute("ALTER TABLE trader_settings ADD COLUMN card TEXT DEFAULT ''")
    try:
        conn.execute("SELECT amount FROM trader_settings LIMIT 1")
    except:
        conn.execute("ALTER TABLE trader_settings ADD COLUMN amount INTEGER DEFAULT 0")
    try:
        conn.execute("SELECT cooldown FROM trader_settings LIMIT 1")
    except:
        conn.execute("ALTER TABLE trader_settings ADD COLUMN cooldown INTEGER DEFAULT 30")
    try:
        conn.execute("SELECT sending FROM trader_settings LIMIT 1")
    except:
        conn.execute("ALTER TABLE trader_settings ADD COLUMN sending INTEGER DEFAULT 0")
    
    conn.commit()
    conn.close()


# ── Users ──

def add_user(user_id, role="trader", username="", name=""):
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO users (user_id, role, username, name) VALUES (?, ?, ?, ?)",
                 (user_id, role, username, name))
    conn.commit()
    conn.close()


def get_user(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_role(user_id):
    user = get_user(user_id)
    return user["role"] if user else "trader"


def set_role(user_id, role):
    conn = get_db()
    conn.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, user_id))
    conn.commit()
    conn.close()


def get_all_users(role=None):
    conn = get_db()
    if role:
        rows = conn.execute("SELECT * FROM users WHERE role = ?", (role,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_users_with_signal():
    conn = get_db()
    rows = conn.execute("""
        SELECT u.* FROM users u
        JOIN trader_settings ts ON u.user_id = ts.trader_id
        WHERE ts.receive_signals = 1
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Phones ──

def register_phone(imei, model=""):
    conn = get_db()
    phone_id = f"ph_{imei[-6:]}"
    conn.execute("INSERT OR REPLACE INTO phones (phone_id, imei, model, status) VALUES (?, ?, ?, 'online')",
                 (phone_id, imei, model))
    conn.commit()
    conn.close()
    log(None, "phone_registered", f"{model} ({imei})")
    return phone_id


def get_phones(trader_id=None):
    conn = get_db()
    if trader_id:
        rows = conn.execute("SELECT * FROM phones WHERE trader_id = ?", (trader_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM phones").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_phone(phone_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM phones WHERE phone_id = ?", (phone_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_phone(phone_id):
    conn = get_db()
    conn.execute("DELETE FROM phones WHERE phone_id = ?", (phone_id,))
    conn.commit()
    conn.close()


def assign_phone(phone_id, trader_id=None):
    conn = get_db()
    conn.execute("UPDATE phones SET trader_id = ? WHERE phone_id = ?", (trader_id, phone_id))
    conn.commit()
    conn.close()


def update_phone_status(phone_id, status, battery=0):
    conn = get_db()
    conn.execute("UPDATE phones SET status = ?, battery = ?, last_seen = CURRENT_TIMESTAMP WHERE phone_id = ?",
                 (status, battery, phone_id))
    conn.commit()
    conn.close()


# ── Trader Settings ──

def get_trader_settings(trader_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM trader_settings WHERE trader_id = ?", (trader_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_trader_settings(trader_id, **kwargs):
    conn = get_db()
    existing = get_trader_settings(trader_id)
    if not existing:
        conn.execute("INSERT INTO trader_settings (trader_id) VALUES (?)", (trader_id,))
    for key, val in kwargs.items():
        conn.execute(f"UPDATE trader_settings SET {key} = ? WHERE trader_id = ?", (val, trader_id))
    conn.commit()
    conn.close()


# ── Purchases ──

def add_purchase(trader_id, card, amount, dirty_card="", retries=1):
    conn = get_db()
    conn.execute("INSERT INTO purchases (trader_id, card, amount, dirty_card, retries) VALUES (?, ?, ?, ?, ?)",
                 (trader_id, card, amount, dirty_card, retries))
    conn.commit()
    conn.close()


def get_purchases(trader_id):
    conn = get_db()
    rows = conn.execute("SELECT * FROM purchases WHERE trader_id = ? ORDER BY id DESC", (trader_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_purchase(purchase_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM purchases WHERE id = ?", (purchase_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def toggle_purchase(purchase_id, enabled):
    conn = get_db()
    conn.execute("UPDATE purchases SET enabled = ? WHERE id = ?", (1 if enabled else 0, purchase_id))
    conn.commit()
    conn.close()


def delete_purchase(purchase_id):
    conn = get_db()
    conn.execute("DELETE FROM purchases WHERE id = ?", (purchase_id,))
    conn.commit()
    conn.close()


# ── Logs ──

def log(user_id=None, action="", details=""):
    conn = get_db()
    conn.execute("INSERT INTO logs (user_id, action, details) VALUES (?, ?, ?)",
                 (user_id, action, details))
    conn.commit()
    conn.close()


def get_logs(limit=50):
    conn = get_db()
    rows = conn.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── QR Tokens ──

def save_qr_token(token, trader_id):
    conn = get_db()
    conn.execute("INSERT INTO qr_tokens (token, trader_id) VALUES (?, ?)", (token, trader_id))
    conn.commit()
    conn.close()


def validate_qr_token(token):
    conn = get_db()
    row = conn.execute("SELECT * FROM qr_tokens WHERE token = ? AND used = 0", (token,)).fetchone()
    if row:
        # Проверка таймаута 5 минут
        created = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
        if (datetime.now() - created).total_seconds() > 300:
            conn.close()
            return None  # Токен истёк
        conn.execute("UPDATE qr_tokens SET used = 1 WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return dict(row)
    conn.close()
    return None


def cleanup_expired_tokens():
    """Удаление истёкших токенов"""
    conn = get_db()
    conn.execute("DELETE FROM qr_tokens WHERE used = 1 OR created_at < datetime('now', '-5 minutes')")
    conn.commit()
    conn.close()
