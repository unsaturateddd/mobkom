# MobKom Robot v2.0 — Telegram Bot

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from datetime import datetime, timedelta
import database as db
import config
import uuid
import io
from logger import log_bot, log_admin, log_signal, log_purchase


def generate_qr_image(data):
    import qrcode
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


def is_admin(uid):
    return db.get_role(uid) == "admin"


def is_moder(uid):
    return db.get_role(uid) in ("admin", "moderator")


def can_panel(uid):
    return db.get_role(uid) in ("admin", "moderator", "trader")


def get_role(uid):
    return db.get_role(uid)


def time_in_bot(uid):
    user = db.get_user(uid)
    if not user or not user.get("joined_at"):
        return "—"
    try:
        joined = datetime.strptime(user["joined_at"], "%Y-%m-%d %H:%M:%S")
        delta = datetime.now() - joined
        days = delta.days
        hours = delta.seconds // 3600
        if days > 0:
            return f"{days} дн. {hours} ч."
        return f"{hours} ч."
    except:
        return "—"


# ═══════════════════════════════════════
# МЕНЮ
# ═══════════════════════════════════════

def main_menu(uid):
    buttons = [
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("📢 Наш канал", url="https://t.me/focustradeps")],
        [InlineKeyboardButton("🔑 Получение доступа", callback_data="access")],
        [InlineKeyboardButton("❓ Поддержка, FAQ", callback_data="faq")],
    ]
    role = get_role(uid)
    if role in ("admin", "moderator", "trader"):
        buttons.append([InlineKeyboardButton("🔧 Панель", callback_data="panel")])
    if role in ("admin", "moderator"):
        buttons.append([InlineKeyboardButton("🛡 Админ-панель", callback_data="admin_panel")])
        buttons.append([InlineKeyboardButton("🎖 Выдача ролей", callback_data="give_role")])
    return InlineKeyboardMarkup(buttons)


def panel_menu(uid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Авто-Откуп", callback_data="auto_buy")],
        [InlineKeyboardButton("📡 Сигналы", callback_data="distribute_signals")],
        [InlineKeyboardButton("⚙️ Настройка SMS", callback_data="sms_config")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_main")],
    ])


def admin_panel_menu(uid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("🏥 Healthcheck", callback_data="admin_health")],
        [InlineKeyboardButton("📋 Логи", callback_data="admin_logs")],
        [InlineKeyboardButton("👥 Все пользователи", callback_data="admin_users")],
        [InlineKeyboardButton("🔍 Инфо о юзере", callback_data="admin_user_info")],
        [InlineKeyboardButton("🔑 Роли", callback_data="admin_roles")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_main")],
    ])


# ═══════════════════════════════════════
# /start
# ═══════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = update.effective_user.username or ""
    name = update.effective_user.first_name or ""

    user = db.get_user(uid)
    if not user:
        db.add_user(uid, username=username, name=name)
        db.log(uid, "start", f"First visit: @{username}")
        log_bot("start", f"New user: @{username}", user_id=uid)
    else:
        log_bot("start", f"Returning user: @{username}", user_id=uid)

    role = get_role(uid)
    role_name = {"admin": "👑 Админ", "moderator": "🛡 Модератор", "trader": "📈 Трейдер"}.get(role, "Нет роли")

    welcome = f"👋 Добро пожаловать в MobKom Robot!\n\n"
    welcome += f"Ваша роль: {role_name}\n\n"
    welcome += f"⚠️ ТЕХ. РАБОТЫ!\n"
    welcome += f"Оповещу о начале работ."

    await update.message.reply_text(welcome, reply_markup=main_menu(uid))


# ═══════════════════════════════════════
# CALLBACK HANDLER
# ═══════════════════════════════════════

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    data = q.data

    try:
        await q.answer()
    except:
        pass

    async def edit(text, **kw):
        try:
            await q.edit_message_text(text, **kw)
        except:
            # Если не удалось отредактировать (фото и т.д.) — отправляем новое
            try:
                await q.message.reply_text(text, **kw)
            except:
                pass

    role = get_role(uid)

    # ── Навигация ──

    if data == "back_main":
        context.user_data.clear()
        await edit("MobKom Robot", reply_markup=main_menu(uid))

    # ── Профиль ──

    elif data == "profile":
        user = db.get_user(uid)
        uname = user["username"] if user else "—"
        rname = {"admin": "👑 Админ", "moderator": "🛡 Модератор", "trader": "📈 Трейдер"}.get(role, "Нет роли")
        joined = user["joined_at"][:10] if user and user.get("joined_at") else "—"
        duration = time_in_bot(uid)

        subs = []
        if role in ("admin", "moderator", "trader"):
            s = db.get_trader_settings(uid) or {}
            subs.append(f"📡 Сигналы: {'✅' if s.get('receive_signals') else '❌'}")
            subs.append(f"📤 Раздача: {'✅' if s.get('distribute_signals') else '❌'}")
            subs.append(f"🎯 Авто-откуп: {'✅' if s.get('auto_buy_enabled') else '❌'}")

        text = f"👤 Мой профиль\n\n"
        text += f"ID: {uid}\n"
        text += f"Username: @{uname}\n"
        text += f"Роль: {rname}\n\n"
        text += f"В боте с: {joined}\n"
        text += f"В боте уже: {duration}\n"
        if subs:
            text += f"\nПодписки:\n" + "\n".join(subs)

        await edit(text, reply_markup=main_menu(uid))

    # ── Получение доступа ──

    elif data == "access":
        await edit(
            "🔑 Получение доступа\n\n"
            "📩 Для получения доступа:\nНапишите: @Focustradep\n\n"
            "📤 Для выдачи доступа:\nНапишите: @Focustradep или @wget1337",
            reply_markup=main_menu(uid)
        )

    # ── FAQ ──

    elif data == "faq":
        await edit(
            "❓ Поддержка, FAQ\n\n"
            "Как пользоваться ботом?\n"
            "1. Получите роль у админа\n"
            "2. Настройте авто-откуп\n"
            "3. Включите получение сигналов\n\n"
            "По вопросам: @Focustradep",
            reply_markup=main_menu(uid)
        )

    # ── Панель трейдера ──

    elif data == "panel" and can_panel(uid):
        await edit("🔧 Панель управления", reply_markup=panel_menu(uid))

    elif data == "auto_buy" and can_panel(uid):
        purchases = db.get_purchases(uid)
        phones = db.get_phones(trader_id=uid)
        if purchases:
            lines = [f"[{i+1}] {p['card'][:8]}... {p['amount']}₽" for i, p in enumerate(purchases)]
            text = "🎯 Авто-Откуп\n\n" + "\n".join(lines)
        else:
            text = "🎯 Авто-Откуп\n\nОткупов нет"
        if phones:
            phone_lines = [f"{'🟢' if p['status']=='online' else '🔴'} {p['model']}" for p in phones]
            text += "\n\n📱 Телефоны:\n" + "\n".join(phone_lines)
        await edit(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Добавить откуп", callback_data="add_purchase")],
            [InlineKeyboardButton("📋 Мои откупы", callback_data="list_purchases")],
            [InlineKeyboardButton("📱 Добавить телефон", callback_data="auto_add_phone")],
            [InlineKeyboardButton("◀️ Назад", callback_data="panel")],
        ]))

    elif data == "add_purchase" and can_panel(uid):
        context.user_data["action"] = "add_card"
        await edit(
            "➕ Новый откуп\n\nКарта: не задана\nСумма: не задана\nГрязный рек: не задан\nПопыток: 1",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ Карта", callback_data="set_card"),
                 InlineKeyboardButton("💰 Сумма", callback_data="set_amount")],
                [InlineKeyboardButton("🔄 Грязный рек", callback_data="set_dirty_card")],
                [InlineKeyboardButton("🔢 Попытки", callback_data="set_retries")],
                [InlineKeyboardButton("✅ Создать", callback_data="create_purchase")],
                [InlineKeyboardButton("◀️ Назад", callback_data="auto_buy")],
            ])
        )

    elif data == "set_card":
        context.user_data["action"] = "set_card"
        await edit("✏️ Отправьте номер карты:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="add_purchase")]]))

    elif data == "set_amount":
        context.user_data["action"] = "set_amount"
        await edit("💰 Отправьте сумму:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="add_purchase")]]))

    elif data == "set_dirty_card":
        context.user_data["action"] = "set_dirty_card"
        await edit("🔄 Отправьте грязный реквизит:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="add_purchase")]]))

    elif data == "set_retries":
        context.user_data["action"] = "set_retries"
        await edit("🔢 Отправьте кол-во попыток (по умолчанию 1):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="add_purchase")]]))

    elif data == "create_purchase" and can_panel(uid):
        p = context.user_data.get("purchase", {})
        if p.get("card") and p.get("amount"):
            db.add_purchase(uid, p["card"], p["amount"], p.get("dirty_card", ""), p.get("retries", 1))
            context.user_data.pop("purchase", None)
            context.user_data.pop("action", None)
            await edit("✅ Откуп создан!", reply_markup=panel_menu(uid))
        else:
            await edit("❌ Заполните карту и сумму", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="add_purchase")]]))

    elif data == "list_purchases" and can_panel(uid):
        purchases = db.get_purchases(uid)
        if purchases:
            buttons = [[InlineKeyboardButton(f"[{i+1}] {p['card'][:8]}... {p['amount']}₽", callback_data=f"purchase_{p['id']}")] for i, p in enumerate(purchases)]
            buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="auto_buy")])
            await edit("📋 Мои откупы:", reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await edit("📋 Откупов нет", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="auto_buy")]]))

    elif data.startswith("purchase_") and can_panel(uid):
        pid = int(data.split("_")[1])
        p = db.get_purchase(pid)
        if p:
            status = "✅ Активен" if p["enabled"] else "⏸ Пауза"
            await edit(
                f"⚙️ Откуп #{pid}\n\n"
                f"Карта: {p['card']}\n"
                f"Сумма: {p['amount']}\n"
                f"Грязный рек: {p['dirty_card'] or '—'}\n"
                f"Попыток: {p['retries']}\n"
                f"Статус: {status}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("▶️ Включить" if not p["enabled"] else "⏹ Выключить", callback_data=f"toggle_purchase_{pid}")],
                    [InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_purchase_{pid}")],
                    [InlineKeyboardButton("◀️ Назад", callback_data="list_purchases")],
                ])
            )

    elif data.startswith("toggle_purchase_") and can_panel(uid):
        pid = int(data.split("_")[2])
        p = db.get_purchase(pid)
        if p:
            db.toggle_purchase(pid, not p["enabled"])
            await edit(f"✅ Откуп #{pid} {'включён' if not p['enabled'] else 'остановлен'}", reply_markup=panel_menu(uid))

    elif data.startswith("delete_purchase_") and can_panel(uid):
        pid = int(data.split("_")[2])
        db.delete_purchase(pid)
        await edit(f"🗑 Откуп #{pid} удалён", reply_markup=panel_menu(uid))

    # ── Получение сигналов ──

    elif data == "receive_signals" and can_panel(uid):
        s = db.get_trader_settings(uid) or {}
        active = s.get("receive_signals", 0)
        status = "✅ Активно" if active else "❌ Неактивно"
        await edit(
            f"📡 Получение сигналов\n\nСтатус: {status}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Включить" if not active else "⏹ Выключить", callback_data="toggle_receive")],
                [InlineKeyboardButton("◀️ Назад", callback_data="panel")],
            ])
        )

    elif data == "toggle_receive" and can_panel(uid):
        s = db.get_trader_settings(uid) or {}
        new = 0 if s.get("receive_signals") else 1
        db.update_trader_settings(uid, receive_signals=new)
        status = "включено" if new else "выключено"
        await edit(f"📡 Получение сигналов: {status}", reply_markup=panel_menu(uid))

    # ── Сигналы ──

    elif data == "distribute_signals" and can_panel(uid):
        phones = db.get_phones(trader_id=uid)
        online = len([p for p in phones if p['status'] == 'online'])
        await edit(
            f"📡 Сигналы\n\n"
            f"📱 Устройств: {len(phones)} (онлайн: {online})",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Список устройств", callback_data="device_list")],
                [InlineKeyboardButton("➕ Подключить устройство", callback_data="add_phone")],
                [InlineKeyboardButton("◀️ Назад", callback_data="panel")],
            ])
        )

    elif data == "device_list" and can_panel(uid):
        phones = db.get_phones(trader_id=uid)
        if phones:
            buttons = []
            for p in phones:
                status_icon = "🟢" if p['status'] == 'online' else "🔴"
                buttons.append([InlineKeyboardButton(
                    f"{status_icon} {p['model']} ({p['imei'][-6:]})",
                    callback_data=f"device_{p['phone_id']}"
                )])
            buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="distribute_signals")])
            await edit("📋 Ваши устройства:", reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await edit(
                "📋 Устройств нет\n\nПодключите первое устройство",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Подключить", callback_data="add_phone")],
                    [InlineKeyboardButton("◀️ Назад", callback_data="distribute_signals")],
                ])
            )

    elif data.startswith("device_") and can_panel(uid):
        phone_id = data.split("_", 1)[1]
        phone = db.get_phone(phone_id)
        if phone:
            status = "🟢 Онлайн" if phone['status'] == 'online' else "🔴 Оффлайн"
            battery = f"{phone['battery']}%" if phone['battery'] else "—"
            last_seen = phone['last_seen'][:16] if phone['last_seen'] else "—"
            await edit(
                f"📱 {phone['model']}\n\n"
                f"IMEI: {phone['imei']}\n"
                f"Статус: {status}\n"
                f"Батарея: {battery}\n"
                f"Последний раз: {last_seen}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Обновить", callback_data=f"device_{phone_id}")],
                    [InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_device_{phone_id}")],
                    [InlineKeyboardButton("◀️ Назад", callback_data="device_list")],
                ])
            )

    elif data.startswith("delete_device_") and can_panel(uid):
        phone_id = data.split("_", 2)[2]
        db.delete_phone(phone_id)
        await edit(f"🗑 Устройство удалено", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ К списку", callback_data="device_list")],
        ]))

    elif data == "add_phone" and can_panel(uid):
        token = str(uuid.uuid4())[:12]
        db.save_qr_token(token, uid)
        qr_img = generate_qr_image(token)
        await q.message.reply_photo(
            photo=qr_img,
            caption=f"📱 Сканируйте QR код в приложении\n\n"
                    f"Токен: {token}\n"
                    f"Действителен: 5 минут",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="distribute_signals")]])
        )

    elif data == "auto_add_phone" and can_panel(uid):
        token = str(uuid.uuid4())[:12]
        db.save_qr_token(token, uid)
        qr_img = generate_qr_image(token)
        await q.message.reply_photo(
            photo=qr_img,
            caption=f"📱 Подключите телефон для авто-откупа\n\n"
                    f"1. Скачайте APK\n"
                    f"2. Отсканируйте QR код\n\n"
                    f"Токен: {token}\n"
                    f"Действителен: 5 минут",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="auto_buy")]])
        )

    # ── Настройка SMS ──

    elif data == "sms_config" and can_panel(uid):
        s = db.get_trader_settings(uid) or {}
        card = s.get("card", "—")
        amount = s.get("amount", "—")
        cooldown = s.get("cooldown", 30)
        text = f"⚙️ Настройка SMS на 7878\n\n"
        text += f"💳 Карта: {card}\n"
        text += f"💰 Сумма: {amount}\n"
        text += f"⏱ КД: {cooldown}с\n"
        await edit(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Карта", callback_data="sms_set_card"),
             InlineKeyboardButton("💰 Сумма", callback_data="sms_set_amount")],
            [InlineKeyboardButton("⏱ КД", callback_data="sms_set_cooldown")],
            [InlineKeyboardButton("◀️ Назад", callback_data="panel")],
        ]))

    elif data == "sms_set_card":
        context.user_data["action"] = "sms_set_card"
        await edit("💳 Отправьте номер карты:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="sms_config")]]))

    elif data == "sms_set_amount":
        context.user_data["action"] = "sms_set_amount"
        await edit("💰 Отправьте сумму:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="sms_config")]]))

    elif data == "sms_set_cooldown":
        context.user_data["action"] = "sms_set_cooldown"
        await edit("⏱ Отправьте КД в секундах (по умолчанию 30):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="sms_config")]]))

    # ── Админ-панель ──

    elif data == "admin_panel" and is_moder(uid):
        await edit("🛡 Админ-панель", reply_markup=admin_panel_menu(uid))

    elif data == "admin_stats" and is_moder(uid):
        users = db.get_all_users()
        phones = db.get_phones()
        online = len([p for p in phones if p["status"] == "online"])
        traders = len([u for u in users if u["role"] == "trader"])
        mods = len([u for u in users if u["role"] == "moderator"])
        admins = len([u for u in users if u["role"] == "admin"])
        await edit(
            f"📊 Статистика\n\n"
            f"Пользователей: {len(users)}\n"
            f"Трейдеров: {traders}\n"
            f"Модераторов: {mods}\n"
            f"Админов: {admins}\n\n"
            f"Телефонов: {len(phones)} (онлайн: {online})",
            reply_markup=admin_panel_menu(uid)
        )

    elif data == "admin_health" and is_moder(uid):
        from websocket_server import get_health_status
        health = get_health_status()
        await edit(
            f"🏥 Healthcheck\n\n"
            f"Статус: {health['status']}\n"
            f"Аптайм: {health['uptime']}\n"
            f"Телефонов онлайн: {health['phones_online']}\n"
            f"Всего подключений: {health['total_connections']}\n"
            f"Всего сообщений: {health['total_messages']}\n"
            f"Всего SMS: {health['total_sms_sent']}\n"
            f"Всего сигналов: {health['total_signals']}",
            reply_markup=admin_panel_menu(uid)
        )

    elif data == "admin_logs" and is_moder(uid):
        from logger import get_logs, get_log_stats
        stats = get_log_stats()
        logs = get_logs(limit=10)
        text = f"📋 Статистика логов:\n\n"
        text += f"🤖 Бот: {stats.get('bot', 0)}\n"
        text += f"🔌 WebSocket: {stats.get('ws', 0)}\n"
        text += f"📡 Сигналы: {stats.get('signal', 0)}\n"
        text += f"🎯 Откупы: {stats.get('purchase', 0)}\n"
        text += f"🛡 Админ: {stats.get('admin', 0)}\n"
        text += f"❌ Ошибки: {stats.get('error', 0)}\n\n"
        text += "Последние события:\n"
        for l in logs[:5]:
            text += f"[{l['time'][-8:]}] {l['action']}: {l['details'][:40]}\n"
        await edit(text, reply_markup=admin_panel_menu(uid))

    elif data == "admin_users" and is_moder(uid):
        users = db.get_all_users()
        text = f"👥 Все пользователи ({len(users)}):\n\n"
        for u in users[:20]:
            r = {"admin": "👑", "moderator": "🛡", "trader": "📈"}.get(u["role"], "❌")
            text += f"{r} {u['user_id']} @{u['username']} [{u['role']}]\n"
        await edit(text, reply_markup=admin_panel_menu(uid))

    elif data == "admin_user_info" and is_moder(uid):
        context.user_data["action"] = "admin_look_user"
        await edit("🔍 Отправьте user_id для просмотра:", reply_markup=admin_panel_menu(uid))

    elif data == "admin_roles" and is_moder(uid):
        context.user_data["action"] = "admin_setrole"
        await edit("🔑 Отправьте: user_id role\n\nРоли: admin, moderator, trader", reply_markup=admin_panel_menu(uid))

    # ── Выдача ролей ──

    elif data == "give_role" and is_moder(uid):
        context.user_data["action"] = "give_role"
        await edit(
            "🎖 Выдача ролей\n\n"
            "Отправьте: user_id role\n\n"
            "Роли:\n"
            "📈 Трейдер\n"
            "🛡 Модератор\n"
            "👑 Админ\n"
            "❌ Нет роли (trader)",
            reply_markup=main_menu(uid)
        )


# ═══════════════════════════════════════
# ТЕКСТОВЫЕ СООБЩЕНИЯ
# ═══════════════════════════════════════

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    action = context.user_data.get("action")
    role = get_role(uid)

    if action == "set_card":
        context.user_data.setdefault("purchase", {})["card"] = text
        context.user_data.pop("action", None)
        p = context.user_data.get("purchase", {})
        await update.message.reply_text(
            f"✅ Карта: {text}\n\n"
            f"Текущие данные:\n"
            f"Карта: {p.get('card', '—')}\n"
            f"Сумма: {p.get('amount', '—')}\n"
            f"Грязный рек: {p.get('dirty_card', '—')}\n"
            f"Попытки: {p.get('retries', 1)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ Карта", callback_data="set_card"),
                 InlineKeyboardButton("💰 Сумма", callback_data="set_amount")],
                [InlineKeyboardButton("🔄 Грязный рек", callback_data="set_dirty_card")],
                [InlineKeyboardButton("🔢 Попытки", callback_data="set_retries")],
                [InlineKeyboardButton("✅ Создать", callback_data="create_purchase")],
                [InlineKeyboardButton("◀️ Назад", callback_data="auto_buy")],
            ])
        )

    elif action == "set_amount":
        try:
            context.user_data.setdefault("purchase", {})["amount"] = int(text)
            context.user_data.pop("action", None)
            p = context.user_data.get("purchase", {})
            await update.message.reply_text(
                f"✅ Сумма: {text}\n\n"
                f"Текущие данные:\n"
                f"Карта: {p.get('card', '—')}\n"
                f"Сумма: {p.get('amount', '—')}\n"
                f"Грязный рек: {p.get('dirty_card', '—')}\n"
                f"Попытки: {p.get('retries', 1)}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✏️ Карта", callback_data="set_card"),
                     InlineKeyboardButton("💰 Сумма", callback_data="set_amount")],
                    [InlineKeyboardButton("🔄 Грязный рек", callback_data="set_dirty_card")],
                    [InlineKeyboardButton("🔢 Попытки", callback_data="set_retries")],
                    [InlineKeyboardButton("✅ Создать", callback_data="create_purchase")],
                    [InlineKeyboardButton("◀️ Назад", callback_data="auto_buy")],
                ])
            )
        except ValueError:
            await update.message.reply_text("❌ Введите число")

    elif action == "set_dirty_card":
        context.user_data.setdefault("purchase", {})["dirty_card"] = text
        context.user_data.pop("action", None)
        p = context.user_data.get("purchase", {})
        await update.message.reply_text(
            f"✅ Грязный рек: {text}\n\n"
            f"Текущие данные:\n"
            f"Карта: {p.get('card', '—')}\n"
            f"Сумма: {p.get('amount', '—')}\n"
            f"Грязный рек: {p.get('dirty_card', '—')}\n"
            f"Попытки: {p.get('retries', 1)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ Карта", callback_data="set_card"),
                 InlineKeyboardButton("💰 Сумма", callback_data="set_amount")],
                [InlineKeyboardButton("🔄 Грязный рек", callback_data="set_dirty_card")],
                [InlineKeyboardButton("🔢 Попытки", callback_data="set_retries")],
                [InlineKeyboardButton("✅ Создать", callback_data="create_purchase")],
                [InlineKeyboardButton("◀️ Назад", callback_data="auto_buy")],
            ])
        )

    elif action == "set_retries":
        try:
            context.user_data.setdefault("purchase", {})["retries"] = int(text)
            context.user_data.pop("action", None)
            p = context.user_data.get("purchase", {})
            await update.message.reply_text(
                f"✅ Попыток: {text}\n\n"
                f"Текущие данные:\n"
                f"Карта: {p.get('card', '—')}\n"
                f"Сумма: {p.get('amount', '—')}\n"
                f"Грязный рек: {p.get('dirty_card', '—')}\n"
                f"Попытки: {p.get('retries', 1)}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✏️ Карта", callback_data="set_card"),
                     InlineKeyboardButton("💰 Сумма", callback_data="set_amount")],
                    [InlineKeyboardButton("🔄 Грязный рек", callback_data="set_dirty_card")],
                    [InlineKeyboardButton("🔢 Попытки", callback_data="set_retries")],
                    [InlineKeyboardButton("✅ Создать", callback_data="create_purchase")],
                    [InlineKeyboardButton("◀️ Назад", callback_data="auto_buy")],
                ])
            )
        except ValueError:
            await update.message.reply_text("❌ Введите число")

    elif action == "add_phone_imei" and can_panel(uid):
        db.register_phone(text, "Unknown")
        db.assign_phone(f"ph_{text[-6:]}", trader_id=uid)
        context.user_data.pop("action", None)
        log_admin("phone_added", f"Phone: {text}", user_id=uid)
        await update.message.reply_text(f"✅ Телефон {text} подключён", reply_markup=panel_menu(uid))

    elif action == "sms_set_card" and can_panel(uid):
        db.update_trader_settings(uid, card=text)
        context.user_data.pop("action", None)
        s = db.get_trader_settings(uid) or {}
        await update.message.reply_text(
            f"✅ Карта: {text}\n\n"
            f"💳 Карта: {s.get('card', '—')}\n"
            f"💰 Сумма: {s.get('amount', '—')}\n"
            f"⏱ КД: {s.get('cooldown', 30)}с",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Карта", callback_data="sms_set_card"),
                 InlineKeyboardButton("💰 Сумма", callback_data="sms_set_amount")],
                [InlineKeyboardButton("⏱ КД", callback_data="sms_set_cooldown")],
                [InlineKeyboardButton("◀️ Назад", callback_data="panel")],
            ])
        )

    elif action == "sms_set_amount" and can_panel(uid):
        try:
            db.update_trader_settings(uid, amount=int(text))
            context.user_data.pop("action", None)
            s = db.get_trader_settings(uid) or {}
            await update.message.reply_text(
                f"✅ Сумма: {text}\n\n"
                f"💳 Карта: {s.get('card', '—')}\n"
                f"💰 Сумма: {s.get('amount', '—')}\n"
                f"⏱ КД: {s.get('cooldown', 30)}с",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Карта", callback_data="sms_set_card"),
                     InlineKeyboardButton("💰 Сумма", callback_data="sms_set_amount")],
                    [InlineKeyboardButton("⏱ КД", callback_data="sms_set_cooldown")],
                    [InlineKeyboardButton("◀️ Назад", callback_data="panel")],
                ])
            )
        except ValueError:
            await update.message.reply_text("❌ Введите число")

    elif action == "sms_set_cooldown" and can_panel(uid):
        try:
            db.update_trader_settings(uid, cooldown=int(text))
            context.user_data.pop("action", None)
            s = db.get_trader_settings(uid) or {}
            await update.message.reply_text(
                f"✅ КД: {text}с\n\n"
                f"💳 Карта: {s.get('card', '—')}\n"
                f"💰 Сумма: {s.get('amount', '—')}\n"
                f"⏱ КД: {s.get('cooldown', 30)}с",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Карта", callback_data="sms_set_card"),
                     InlineKeyboardButton("💰 Сумма", callback_data="sms_set_amount")],
                    [InlineKeyboardButton("⏱ КД", callback_data="sms_set_cooldown")],
                    [InlineKeyboardButton("◀️ Назад", callback_data="panel")],
                ])
            )
        except ValueError:
            await update.message.reply_text("❌ Введите число в секундах")

    elif action == "give_role" and is_moder(uid):
        parts = text.split()
        if len(parts) == 2:
            try:
                target_uid = int(parts[0])
                new_role = parts[1]
                if new_role in ("admin", "moderator", "trader"):
                    db.set_role(target_uid, new_role)
                    db.log(uid, "role_change", f"{target_uid} -> {new_role}")
                    log_admin("role_change", f"{uid} -> {target_uid} -> {new_role}", user_id=uid)
                    context.user_data.pop("action", None)
                    await update.message.reply_text(f"✅ {target_uid} → {new_role}", reply_markup=main_menu(uid))
                else:
                    await update.message.reply_text("❌ Роль: admin, moderator, trader")
            except ValueError:
                await update.message.reply_text("❌ user_id должен быть числом")
        else:
            await update.message.reply_text("Формат: user_id role")

    elif action == "admin_setrole" and is_moder(uid):
        parts = text.split()
        if len(parts) == 2:
            try:
                target_uid = int(parts[0])
                new_role = parts[1]
                if new_role in ("admin", "moderator", "trader"):
                    db.set_role(target_uid, new_role)
                    db.log(uid, "role_change", f"{target_uid} -> {new_role}")
                    context.user_data.pop("action", None)
                    await update.message.reply_text(f"✅ {target_uid} → {new_role}", reply_markup=admin_panel_menu(uid))
                else:
                    await update.message.reply_text("❌ Роль: admin, moderator, trader")
            except ValueError:
                await update.message.reply_text("❌ user_id должен быть числом")
        else:
            await update.message.reply_text("Формат: user_id role")

    elif action == "admin_look_user" and is_moder(uid):
        try:
            target_uid = int(text)
            user = db.get_user(target_uid)
            if user:
                r = {"admin": "👑 Админ", "moderator": "🛡 Модератор", "trader": "📈 Трейдер"}.get(user["role"], "Нет роли")
                phones = db.get_phones(trader_id=target_uid)
                purchases = db.get_purchases(target_uid)
                s = db.get_trader_settings(target_uid) or {}

                info = f"🔍 Инфо: @{user['username']} ({user['user_id']})\n\n"
                info += f"Роль: {r}\n"
                info += f"В боте с: {user['joined_at'][:10]}\n\n"
                info += f"📱 Телефоны: {len(phones)}\n"
                info += f"🎯 Откупов: {len(purchases)}\n"
                info += f"📡 Сигналы: {'✅' if s.get('receive_signals') else '❌'}\n"
                info += f"📤 Раздача: {'✅' if s.get('distribute_signals') else '❌'}"
                await update.message.reply_text(info, reply_markup=admin_panel_menu(uid))
            else:
                await update.message.reply_text("❌ Пользователь не найден")
        except ValueError:
            await update.message.reply_text("❌ Введите user_id")
        context.user_data.pop("action", None)


# ═══════════════════════════════════════
# BROADCAST
# ═══════════════════════════════════════

async def broadcast_signal():
    from telegram import Bot
    bot = Bot(token=config.BOT_TOKEN)
    users = db.get_all_users_with_signal()
    sent = 0
    for u in users:
        try:
            await bot.send_message(chat_id=u["user_id"], text=config.SIGNAL_TEXT)
            sent += 1
        except:
            pass
    return sent


def setup_bot():
    app = Application.builder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app
